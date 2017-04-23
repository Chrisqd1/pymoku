import zmq
import dataparser
import math

from . import _instrument
from _instrument import *
from pymoku import Moku, UncommittedSettings, InvalidConfigurationException, FrameTimeout, BufferTimeout, NotDeployedException, InvalidOperationException, NoDataException, StreamException, InsufficientSpace, MPNotMounted, MPReadOnly, dataparser

_STREAM_STATE_NONE		= 0
_STREAM_STATE_RUNNING 	= 1
_STREAM_STATE_WAITING 	= 2
_STREAM_STATE_INVAL		= 3
_STREAM_STATE_FSFULL	= 4
_STREAM_STATE_OVERFLOW	= 5
_STREAM_STATE_BUSY		= 6
_STREAM_STATE_STOPPED	= 7

class StreamHandler(_instrument.MokuInstrument):
	"""
		Helper class - should not be instantiated directly.
		This class is intended to handle streams: checking status, receiving/parsing raw data, 
		translating error messages and setting up new streaming sessions.
	"""

	def __init__(self):
		super(StreamHandler, self).__init__()
		# Stream socket connection
		self._dlskt = None
		# Data parser for current session
		self._strparser = None
		# Stream identifier number
		self._dlserial = 0
		# Current stream file type
		self._dlftype = None

		# Enabled channels for streaming session
		self.ch1 = False
		self.ch2 = False
		self.nch = 0

		self.procstr = ''
		self.binstr = ''
		self.hdrstr = ''
		self.fmtstr = ''


	@staticmethod
	def _max_stream_rates(instr, nch, use_sd):
		"""
		Returns the maximum rate at which the instrument can be streamed for the given
		streaming configuration

		Currently only specified for the Oscilloscope instrument
		"""

		# These are checked on the client side too but we sanity-check here as an invalid
		# rate can hard-hang the Moku. These rates are approximate and experimentally
		# derived, should be updated as we test and optimize things.
		# Logging rates depend on which storage medium, and the filetype as well
		maxrates = None
		if nch == 2:
			if(use_sd):
				maxrates = { 'bin' : 150e3, 'csv' : 1e3, 'net' : 20e3, 'plot' : 10}
			else:
				maxrates = { 'bin' : 1e6, 'csv' : 1e3, 'net' : 20e3, 'plot' : 10}
		else:
			if(use_sd):
				maxrates = { 'bin' : 250e3, 'csv' : 3e3, 'net' : 40e3, 'plot' : 10}
			else:
				maxrates = { 'bin' : 1e6, 'csv' : 3e3, 'net' : 40e3, 'plot' : 10}

		return maxrates
		
	@staticmethod
	def _estimate_logsize(ch1, ch2, duration, timestep, filetype):
		"""
		Returns a rough estimate of log size for disk space checking. 
		Currently assumes instrument is the Oscilloscope.

		:type ch1: bool
		:param ch1: Is Channel 1 enabled?
		:type ch2: bool
		:param ch2: Is Channel 2 enabled?
		:type duration: float
		:param duration: Duration of logging session in seconds.
		:type timestep: float
		:param timestep: Timestep of each sample (1/samplerate)
		:type filetype: string {'csv','bin'}
		:param filetype: File type of the log to estimate size of
		"""
		if filetype is 'bin':
			sample_size_bytes = 4 * (ch1 + ch2)
			return (duration / timestep) * sample_size_bytes
		elif filetype is 'csv':
			# one byte per character: time, data (assume negative half the time), newline
			characters_per_line = 16 + ( 2 + 16.5 )*(ch1 + ch2) + 2
			return (duration / timestep) *  characters_per_line

	def _stream_start(self, start, duration, use_sd, ch1, ch2, filetype):
		""" Start an instrument streaming session.

		If the duration is non-zero, the device must be in ROLL mode (via a call to :any:`set_xmode`). 
		Also, the sample rate must be appropriate to the instrument and file type (as calculated by 
		:any:`_max_stream_rates`)

		:raises InvalidOperationException: if the sample rate is too high for the selected filetype or if the
			device *x_mode* isn't set to *ROLL* when running non-'net' type streams.

		.. warning:: Start parameter not currently implemented, must be set to zero

		:type start: float
		:param start: Start time in seconds from the time of function call
		:type duration: float
		:param duration: Log duration in seconds
		:type use_sd: bool
		:param use_sd: Log to SD card (default is internal volatile storage). Ignored if 'net' file type.
		:type ch1: bool
		:param ch1: Log from Channel 1
		:type ch2: bool
		:param ch2: Log from Channel 2
		:param filetype: Type of log to start. One of the types below.

		*File Types*

		- **csv** -- CSV file
		- **bin** -- LI Binary file
		- **net** -- Log to network, retrieve data with :any:`_stream_receive_samples`
		"""
		if (not ch1) and (not ch2):
			raise InvalidOperationException("No channels were selected for logging")
		if duration < 0:
			raise InvalidOperationException("Invalid duration %d", duration)
		
		from datetime import datetime
		if self._moku is None: raise NotDeployedException()

		self._dlserial += 1
		self.tag = "%04d" % self._dlserial

		self.ch1 = bool(ch1)
		self.ch2 = bool(ch2)		
		self.nch = bool(self.ch1) + bool(self.ch2)
		# Update all child instrument local datalogging variables
		self._update_datalogger_params()
		
		fname = datetime.now().strftime(self.logname + "_%Y%m%d_%H%M%S")

		# Currently the data stream genesis is from the x_mode commit below, meaning that delayed start
		# doesn't work properly. Once this is fixed in the FPGA/daemon, remove this check and the note
		# in the documentation above.
		if start:
			raise InvalidOperationException("Logging start time parameter currently not supported")

		# Logging rates depend on which storage medium, and the filetype as well
		if duration > 0:
			maxrates = StreamHandler._max_stream_rates(None, self.nch, use_sd)
			if math.floor(1.0 / self.timestep) > maxrates[filetype]:
				raise InvalidOperationException("Sample Rate %d too high for file type %s. Maximum rate: %d" % (1.0 / self.timestep, filetype, maxrates[filetype]))

			if self.x_mode != _instrument.ROLL:
				raise InvalidOperationException("Instrument must be in roll mode to perform data logging")

		if not all([ len(s) for s in [self.binstr, self.procstr, self.fmtstr, self.hdrstr]]):
			raise InvalidOperationException("Instrument currently doesn't support data logging")

		# If not a network stream, we must check the mount point is available
		if filetype is not 'net':
			mp = 'e' if use_sd else 'i'
			try:
				t , f = self._moku._fs_free(mp)
				logsize = self._estimate_logsize(ch1, ch2, duration, self.timestep, filetype)
				if f < logsize:
					raise InsufficientSpace("Insufficient disk space for requested log file (require %d kB, available %d kB)" % (logsize/(2**10), f/(2**10)))
			except MPReadOnly as e:
				if use_sd:
					raise MPReadOnly("SD Card is read only.")
				raise e
			except MPNotMounted as e:
				if use_sd:
					raise MPNotMounted("SD Card is unmounted.")
				raise e

		# We have to be in this mode anyway because of the above check, but rewriting this register and committing
		# is necessary in order to reset the channel buffers on the device and flush them of old data.
		if duration > 0:
			self.x_mode = _instrument.ROLL
			self.commit()

		try:
			self._moku._stream_prep(ch1=self.ch1, ch2=self.ch2, start=start, end=start + duration, offset=0, timestep=self.timestep,
			binstr=self.binstr, procstr=self.procstr, fmtstr=self.fmtstr, hdrstr=self.hdrstr,
			fname=fname, ftype=filetype, tag=self.tag, use_sd=use_sd)
		except StreamException as e:
			self._stream_error(status=e.err)
		
		if filetype == 'net':
			self._streamsub_init(self.tag)

		log.info("Starting new data streaming session.")
		self._moku._stream_start()

		# This may not actually exist as a file (e.g. if a 'net' session was run)
		self.logfile = str(self._stream_status()[4]).strip()

		# Store the requested filetype in the case of a "wait" call
		self._dlftype = filetype

	def _stream_stop(self):
		""" Stop a recording session previously started with :py:func:`datalogger_start`

		This function signals that the user no longer needs to know the status of the previous
		log, discarding that state. It must be called before a second log is started or else
		that start attempt will fail with a "busy" error.

		:rtype: int
		:return: final status code (see :py:func:`_stream_status`
		"""
		if self._moku is None: raise NotDeployedException()

		log.info("Stopping data streaming session.")
		stat = self._moku._stream_stop()
		self._streamsub_destroy()

		return stat

	def _stream_status(self):
		""" Return the status of the most recent recording session to be started.
		This is still valid after the stream has stopped, in which case the status will reflect that it's safe
		to start a new session.

		Returns a tuple of state variables:

		- **status** -- Current datalogger state
		- **logged** -- Number of samples recorded so far. If more than one channel is active, this is the sum of all points across all channels.
		- **to start** -- Number of seconds until/since start. Time until start is positive, a negative number indicates that the record has started already.
		- **to end** -- Number of seconds until/since end.
		- **filename** -- Base filename of current log session (without filetype)

		Status is one of:

		- **_STREAM_STATE_NONE** -- No session
		- **_STREAM_STATE_RUNNING** -- Session currently running
		- **_STREAM_STATE_WAITING** -- Session waiting to run (delayed start)
		- **_STREAM_STATE_INVAL** -- An attempt was made to start a session with invalid parameters
		- **_STREAM_STATE_FSFULL** -- A session has terminated early due to the storage filling up
		- **_STREAM_STATE_OVERFLOW** -- A session has terminated early due to the sample rate being too high for the storage speed
		- **_STREAM_STATE_BUSY** -- An attempt was made to start a session when one was already running
		- **_STREAM_STATE_STOPPED** -- A session has successfully completed.

		:rtype: int, int, int, int
		:return: status, logged, to start, to end, filename.
		"""
		if self._moku is None: raise NotDeployedException()
		return self._moku._stream_status()

	def _stream_data_remaining(self):
		""" Returns number of seconds from session start and end.

		- **to start** -- Number of seconds until/since start. Time until start is positive, a negative number indicates that the record has started already.
		- **to end** -- Number of seconds until/since end.

		:rtype: int, int
		:return: to start, to end
		"""
		d1, d2, start, end, fname = self._stream_status()
		return start, end

	def _stream_data_captured(self):
		""" Returns number of samples captures in this datalogging session.

		:rtype: int
		:returns: sample count
		"""
		return self._stream_status()[1]

	def _stream_completed(self, status):
		""" Returns whether or not the datalogger is expecting to log any more data.

		If the log is completed then the results files are ready to be uploaded or simply
		read off the SD card. At most one subsequent :any:`datalogger_get_samples` call
		will return without timeout.

		If the datalogger has entered an error state, a StreamException is raised.

		:rtype: bool
		:returns: Whether the current session has finished running. 

		:raises StreamException: if the session has entered an error state
		"""
		if not status:
			status = self._stream_status()[0]
		self._stream_error(status=status)
		return status not in [_STREAM_STATE_RUNNING, _STREAM_STATE_WAITING]

	def _stream_error(self, status=None):
		""" Checks the current datalogger session for errors. Alternatively, the status
		parameter returned by :any:`_stream_status` call can be translated to the 
		associated exception (if any).

		:raises StreamException: if the session is in error.
		:raises InvalidArgument:
		"""
		if not status:
			status = self._stream_status()[0]
		msg = None

		if status in [_STREAM_STATE_NONE, _STREAM_STATE_RUNNING, _STREAM_STATE_WAITING, _STREAM_STATE_STOPPED]:
			msg = None
		elif status == _STREAM_STATE_INVAL:
			msg = "Invalid Parameters for Datalogger Operation"
		elif status == _STREAM_STATE_FSFULL:
			msg = "Target Filesystem Full"
		elif status == _STREAM_STATE_OVERFLOW:
			msg ="Session overflowed, sample rate too fast."
		elif status == _STREAM_STATE_BUSY:
			msg = "Tried to start a logging session while one was already running."
		else:
			raise ValueError('Invalid status argument')

		if msg:
			raise StreamException(msg, status)

	def _stream_net_is_running(self):
		return self._dlskt is not None

	def _stream_receive_samples(self,timeout):
		"""
			Gets raw samples off the network and parses them.

			:raises NoDataException: if there is no more data to receive for the session.
		"""
		if not self._stream_net_is_running():
			raise StreamException("No network stream is currently running.")

		ch, start, coeff, raw = self._stream_get_samples_raw(timeout)

		self._strparser.set_coeff(ch, coeff)
		self._strparser.parse(raw, ch)

	def _stream_get_processed_samples(self):
		"""
			Gets any already parsed samples for the current session.

			:rtype: array
			:returns: Array where each entry is an array corresponding to 
			processed channel samples [[Ch1 Samples],[Ch2 Samples]].
		"""
		processed_smps = self._strparser.processed
		if self.nch == 1:
			if self.ch1:
				return [processed_smps[0],[]]
			if self.ch2:
				return [[],processed_smps[0]]
		return processed_smps

	def _stream_clear_processed_samples(self, _len=None):
		"""
			Clears out already processed samples

			:type _len: int
			:param _len: Number of processed samples to clear.
		"""
		if not _len:
			self._strparser.clear_processed()
		else:
			self._strparser.clear_processed(_len)

	def _stream_get_samples_raw(self, timeout):
		"""
			Receives raw instrument samples off the network

			:type timeout: int
			:param timeout: Timeout in seconds

			:raises NoDataException: if the network times out waiting for samples.

		"""
		if self._dlskt in zmq.select([self._dlskt], [], [], timeout)[0]:
			hdr, data = self._dlskt.recv_multipart()

			hdr = hdr.decode('ascii')
			tag, ch, start, coeff = hdr.split('|')
			ch = int(ch)
			start = int(start)
			coeff = float(coeff)

			# Special value to indicate the stream has finished
			if ch == -1:
				raise NoDataException("Data log terminated")

			return ch, start, coeff, data
		else:
			raise FrameTimeout("Data log timed out after %d seconds", timeout)

	def _streamsub_init(self, tag):
		"""
			Initialises a ZMQ stream subscriber and data parser for current session.
		"""
		ctx = zmq.Context.instance()
		self._dlskt = ctx.socket(zmq.SUB)
		self._dlskt.connect("tcp://%s:27186" % self._moku._ip)
		self._dlskt.setsockopt_string(zmq.SUBSCRIBE, unicode(tag))

		self._strparser = dataparser.LIDataParser(self.ch1, self.ch2,
			self.binstr, self.procstr, self.fmtstr, self.hdrstr,
			self.timestep, int(time.time()), [0] * self.nch,
			0) # Zero offset from start time to first sample, valid for streams but not so much for single frame transfers

	def _streamsub_destroy(self):
		if self._dlskt is not None:
			self._dlskt.close()
			self._dlskt = None

	def _update_datalogger_params(self):
		# To be overwritten by child instruments to update local datalogger parameters
		# prior to starting any stream session
		
		return
