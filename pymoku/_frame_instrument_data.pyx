import struct

class InstrumentData(object):
	"""
	Superclass representing a full frame of some kind of data. This class is never used directly,
	but rather it is subclassed depending on the type of data contained and the instrument from
	which it originated. For example, the :any:`Oscilloscope` instrument will generate :any:`VoltsData`
	objects, where :any:`VoltsData` is a subclass of :any:`InstrumentData`.
	"""
	def __init__(self, instrument):
		#: A reference to the parent instrument that generates this data object
		self._instrument = instrument

		self._complete = False
		self._chs_valid = [False, False]

		#: Channel 1 raw data array. Present whether or not the channel is enabled, but the contents
		#: are undefined in the latter case.
		self._raw1 = []

		#: Channel 2 raw data array.
		self._raw2 = []

		self._stateid = None
		self._trigstate = None

		#: Frame number. Increments monotonically but wraps at 16-bits.
		self._frameid = 0

		#: Incremented once per trigger event. Wraps at 32-bits.
		self.waveformid = 0

		#: True if at least one trigger event has occured, synchronising the data across all channels.
		self.synchronised = False

		self._flags = None

	def add_packet(self, packet):
		hdr_len = 15
		if len(packet) <= hdr_len:
			# Should be a higher priority but actually seems unexpectedly common. Revisit.
			return

		data = struct.unpack('<BHBBBBBIBH', packet[:hdr_len])
		frameid = data[1]
		instrid = data[2]
		chan = (data[3] >> 4) & 0x0F

		self._stateid = data[4]
		self._trigstate = data[5]
		self._flags = data[6]
		self.waveformid = data[7]
		self._source_serial = data[8]

		if self._frameid != frameid:
			self._frameid = frameid
			self._chs_valid = [False, False]

		# For historical reasons the data length is 1026 while there are only 1024
		# valid samples. Trim the fat.
		if chan == 0:
			self._chs_valid[0] = True
			self._raw1 = packet[hdr_len:-8]
		else:
			self._chs_valid[1] = True
			self._raw2 = packet[hdr_len:-8]

		self._complete = all(self._chs_valid)

		if self._complete:
			if not self.process_complete():
				self._complete = False
				self._chs_valid = [False, False]

	def process_complete(self):
		# Update the waveform ID latch of the parent instrument as soon as waveform ID increments
		self._instrument._data_syncd |= self.waveformid > 0

		# We can't be sure the channels have synchronised in the channel buffers until the first
		# triggered waveform is received.
		if not self._instrument._data_syncd:
			self._raw1 = struct.pack('<i',-0x80000000)*int(len(self._raw1)/4)
			self._raw2 = struct.pack('<i',-0x80000000)*int(len(self._raw2)/4)
		else:
			self.synchronised = True

		return True

	def process_buffer(self):
		# Designed to be overridden by subclasses needing to add x-axis to buffer data etc.
		return True
