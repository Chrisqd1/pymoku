
# Pull in Python 3 string object on Python 2.
from builtins import str

import select, socket, struct, sys
import os, os.path
import logging, time, threading, math
import zmq

from collections import deque
from queue import Queue, Empty

from pymoku import Moku, FrameTimeout, NoDataException, StreamException, UncommittedSettings, dataparser, _stream_handler
from _stream_instrument import _STREAM_STATE_NONE, _STREAM_STATE_RUNNING, _STREAM_STATE_WAITING, _STREAM_STATE_INVAL, _STREAM_STATE_FSFULL, _STREAM_STATE_OVERFLOW, _STREAM_STATE_BUSY, _STREAM_STATE_STOPPED

from . import _instrument
from _instrument import dont_commit

log = logging.getLogger(__name__)

class FrameQueue(Queue):
	def put(self, item, block=True, timeout=None):
		# Behaves the same way as default except that instead of raising Full, it
		# just pushes the item on to the deque anyway, throwing away old frames.
		self.not_full.acquire()
		try:
			if self.maxsize > 0 and block:
				if timeout is None:
					while self._qsize() == self.maxsize:
						self.not_full.wait()
				elif timeout < 0:
					raise ValueError("'timeout' must be a non-negative number")
				else:
					endtime = _time() + timeout
					while self._qsize() == self.maxsize:
						remaining = endtime - _time()
						if remaining <= 0.0:
							break
						self.not_full.wait(remaining)
			self._put(item)
			self.unfinished_tasks += 1
			self.not_empty.notify()
		finally:
			self.not_full.release()

	def get(self, block=True, timeout=None):
		item = None
		while True:
			try:
				item = Queue.get(self, block=block, timeout=timeout or 1)
			except Empty:
				if timeout is None:
					continue
				else:
					raise
			else:
				return item

	# The default _init for a Queue doesn't actually bound the deque, relying on the
	# put function to bound.
	def _init(self, maxsize):
		self.queue = deque(maxlen=maxsize)

class DataBuffer(object):
	"""
	Holds data from the internal buffer (prior to rendering)
	"""

	def __init__(self, ch1, ch2, xs, stateid, scales):
		self.ch1 = ch1
		self.ch2 = ch2
		self.xs = xs
		self.stateid = stateid
		self.scales = scales


class DataFrame(object):
	"""
	Superclass representing a full frame of some kind of data. This class is never used directly,
	but rather it is subclassed depending on the type of data contained and the instrument from
	which it originated. For example, the :any:`Oscilloscope` instrument will generate :any:`VoltsFrame`
	objects, where :any:`VoltsFrame` is a subclass of :any:`DataFrame`.
	"""
	def __init__(self):
		self.complete = False
		self.chs_valid = [False, False]

		#: Channel 1 raw data array. Present whether or not the channel is enabled, but the contents
		#: are undefined in the latter case.
		self.raw1 = []

		#: Channel 2 raw data array.
		self.raw2 = []

		self.stateid = None
		self.trigstate = None

		#: Frame number. Increments monotonically but wraps at 16-bits.
		self.frameid = 0

		#: Incremented once per trigger event. Wraps at 32-bits.
		self.waveformid = 0

		self.flags = None

	def add_packet(self, packet):
		hdr_len = 15
		if len(packet) <= hdr_len:
			# Should be a higher priority but actually seems unexpectedly common. Revisit.
			log.debug("Corrupt frame recevied, len %d", len(packet))
			return

		data = struct.unpack('<BHBBBBBIBH', packet[:hdr_len])
		frameid = data[1]
		instrid = data[2]
		chan = (data[3] >> 4) & 0x0F

		self.stateid = data[4]
		self.trigstate = data[5]
		self.flags = data[6]
		self.waveformid = data[7]
		self.source_serial = data[8]

		if self.frameid != frameid:
			self.frameid = frameid
			self.chs_valid = [False, False]

		log.debug("AP ch %d, f %d, w %d", chan, frameid, self.waveformid)

		# For historical reasons the data length is 1026 while there are only 1024
		# valid samples. Trim the fat.
		if chan == 0:
			self.chs_valid[0] = True
			self.raw1 = packet[hdr_len:-8]
		else:
			self.chs_valid[1] = True
			self.raw2 = packet[hdr_len:-8]

		self.complete = all(self.chs_valid)

		if self.complete:
			if not self.process_complete():
				self.complete = False
				self.chs_valid = [False, False]

	def process_complete(self):
		# Designed to be overridden by subclasses needing to transform the raw data in to Volts etc.
		return True


# Revisit: Should this be a Mixin? Are there more instrument classifications of this type, recording ability, for example?
class FrameBasedInstrument(_stream_handler.StreamHandler, _instrument.MokuInstrument):
	def __init__(self):
		super(FrameBasedInstrument, self).__init__()
		self._buflen = 1
		self._queue = FrameQueue(maxsize=self._buflen)
		self._hb_forced = False

	def _set_frame_class(self, frame_class, **frame_kwargs):
		self.frame_class = frame_class
		self.frame_kwargs = frame_kwargs

	def _flush(self):
		""" Clear the Frame Buffer.
		This is normally not required as one can simply wait for the correctly-generated frames to propagate through
		using the appropriate arguments to :any:`get_data`.
		"""
		with self._queue.mutex:
			self._queue.queue.clear()

	def _set_buffer_length(self, buflen):
		""" Set the internal frame buffer length."""
		self._buflen = buflen
		self._queue = FrameQueue(maxsize=buflen)

	def _get_buffer_length(self):
		""" Return the current length of the internal frame buffer
		"""
		return self._buflen

	@dont_commit
	def get_data(self, timeout=None):
		""" Get a :any:`DataFrame` from the internal data channel buffer.
		This will commit any outstanding device settings and pause acquisition.
		"""
		from datetime import datetime
		if self._moku is None: raise NotDeployedException()
		fname = datetime.now().strftime(self.logname + "_%Y%m%d_%H%M%S")

		if self.check_uncommitted_state():
			raise UncommittedSettings("Detected uncommitted instrument settings.")

		# Get a frame to see what the acquisition state was for the current buffer
		# TODO: Need a way of getting buffer state information without frames
		try:
			frame = self.get_realtime_data(timeout=timeout, wait=False)
		except FrameTimeout:
			raise BufferTimeout('Timed out waiting on valid data.')

		# Check if it is already paused
		was_paused = self.get_pause()

		# Force a pause even if it already has happened
		if not was_paused: 
			self.set_pause(True)
			self.commit()
				
		# Get buffer data using a network stream
		self._stream_start(start=0, duration=0, use_sd=False, ch1=True, ch2=True, filetype='net')

		while True:
			try:
				self._stream_receive_samples(timeout)
			except NoDataException:
				log.debug("No more data to receive.")
				break

		if not was_paused:
			self.set_pause(False)
			self.commit()

		res = self._stream_get_processed_samples()
		self._stream_clear_processed_samples()

		return res
		
	def _process_buffer(self, buff):
		# Expected to be overwritten by child class in the case of 
		# post-processing a buffer object
		return buff

	def get_realtime_data(self, timeout=None, wait=True):
		""" Get a :any:`DataFrame` from the internal frame buffer
		"""
		try:
			# Dodgy hack, infinite timeout gets translated in to just an exceedingly long one
			endtime = time.time() + (timeout or sys.maxsize)
			while self._running:
				frame = self._queue.get(block=True, timeout=timeout)
				# Should really just wait for the new stateid to propagte through, but
				# at the moment we don't support stateid and stateid_alt being different;
				# i.e. we can't rerender already aquired data. Until we fix this, wait
				# for a trigger to propagate through so we don't at least render garbage
				if not wait or frame.trigstate == self._stateid:
					return frame
				elif time.time() > endtime:
					raise FrameTimeout()
				else:
					log.debug("Incorrect state received: %d/%d", frame.trigstate, self._stateid)
		except Empty:
			raise FrameTimeout()

	def _set_running(self, state):
		prev_state = self._running
		super(FrameBasedInstrument, self)._set_running(state)
		if state and not prev_state:
			self._fr_worker = threading.Thread(target=self._frame_worker)
			self._fr_worker.start()
		elif not state and prev_state:
			self._fr_worker.join()


	def _frame_worker(self):
		if(getattr(self, 'frame_class', None)):
			ctx = zmq.Context.instance()
			skt = ctx.socket(zmq.SUB)
			skt.connect("tcp://%s:27185" % self._moku._ip)
			skt.setsockopt_string(zmq.SUBSCRIBE, u'')
			skt.setsockopt(zmq.RCVHWM, 8)
			skt.setsockopt(zmq.LINGER, 5000)

			fr = self.frame_class(**self.frame_kwargs)

			try:
				while self._running:
					if skt in zmq.select([skt], [], [], 1.0)[0]:
						d = skt.recv()
						fr.add_packet(d)

						if fr.complete:
							self._queue.put_nowait(fr)
							fr = self.frame_class(**self.frame_kwargs)
			finally:
				skt.close()