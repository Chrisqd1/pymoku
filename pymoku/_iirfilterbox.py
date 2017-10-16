
import math
import logging

from pymoku._oscilloscope import _CoreOscilloscope, VoltsData

from ._instrument import *
from . import _frame_instrument
from . import _siggen
from . import _utils


log = logging.getLogger(__name__)
REG_ENABLE				= 96
REG_MONSELECT			= 111
REG_INPUTOFFSET_CH0		= 112
REG_INPUTOFFSET_CH1		= 113
REG_OUTPUTOFFSET_CH0	= 114
REG_OUTPUTOFFSET_CH1	= 115
REG_CH0_CH0GAIN			= 116
REG_CH0_CH1GAIN			= 117
REG_CH1_CH0GAIN			= 118
REG_CH1_CH1GAIN			= 119
REG_INPUTSCALE_CH0		= 120
REG_INPUTSCALE_CH1		= 121
REG_OUTPUTSCALE_CH0		= 122
REG_OUTPUTSCALE_CH1		= 123
REG_SAMPLINGFREQ		= 124

#REG_FILT_RESET 		= 127
REG_FILT_RESET 		= 62

_IIR_MON_IN_CH1 		= 0
_IIR_MON_IN_CH1OFF		= 1
_IIR_MON_OUT_CH1		= 2
_IIR_MON_IN_CH2 		= 3
_IIR_MON_IN_CH2OFF 		= 4
_IIR_MON_OUT_CH2 		= 5

# REG_OSC_OUTSEL constants
OSC_SOURCE_ADC		= 0
OSC_SOURCE_DAC		= 1

# REG_OSC_TRIGMODE constants
OSC_TRIG_AUTO		= 0
OSC_TRIG_NORMAL		= 1
OSC_TRIG_SINGLE		= 2

# REG_OSC_TRIGLVL constants
OSC_TRIG_CH1		= 0
OSC_TRIG_CH2		= 1
OSC_TRIG_DA1		= 2
OSC_TRIG_DA2		= 3

OSC_EDGE_RISING		= 0
OSC_EDGE_FALLING	= 1
OSC_EDGE_BOTH		= 2

# Re-export the top level attributes so they'll be picked up by pymoku.instruments, we
# do actually want to give people access to these constants directly for Oscilloscope
OSC_ROLL			= ROLL
OSC_SWEEP			= SWEEP
OSC_FULL_FRAME		= FULL_FRAME

_OSC_LB_ROUND		= 0
_OSC_LB_CLIP		= 1

_OSC_AIN_DDS		= 0
_OSC_AIN_DECI		= 1

_OSC_ADC_SMPS		= ADC_SMP_RATE
_OSC_BUFLEN			= CHN_BUFLEN
_OSC_SCREEN_WIDTH	= 1024
_OSC_FPS			= 10


_IIR_COEFFWIDTH = 48

NumStages = 8


class IIRFilterFrame(_frame_instrument.FrameBasedInstrument):
	"""
	Object representing a frame of data in units of Volts. This is the native output format of
	the :any:`Oscilloscope` instrument and similar.

	This object should not be instantiated directly, but will be returned by a supporting *get_frame*
	implementation.

	.. autoinstanceattribute:: pymoku._frame_instrument.VoltsFrame.ch1
		:annotation: = [CH1_DATA]

	.. autoinstanceattribute:: pymoku._frame_instrument.VoltsFrame.ch2
		:annotation: = [CH2_DATA]

	.. autoinstanceattribute:: pymoku._frame_instrument.VoltsFrame.frameid
		:annotation: = n

	.. autoinstanceattribute:: pymoku._frame_instrument.VoltsFrame.waveformid
		:annotation: = n
	"""
	def __init__(self, scales):
		super(IIRFilterFrame, self).__init__()

		#: Channel 1 data array in units of Volts. Present whether or not the channel is enabled, but the
		#: contents are undefined in the latter case.
		self.ch1 = []

		#: Channel 2 data array in units of Volts.
		self.ch2 = []

		self.scales = scales

	def __json__(self):
		return { 'ch1': self.ch1, 'ch2' : self.ch2 }

	def process_complete(self):
		if self.stateid not in self.scales:
			log.error("Can't render voltage frame, haven't saved calibration data for state %d", self.stateid)
			return

		scale1, scale2 = self.scales[self.stateid]

		try:
			smpls = int(len(self.raw1) / 4)
			dat = struct.unpack('<' + 'i' * smpls, self.raw1)
			dat = [ x if x != -0x80000000 else None for x in dat ]

			self.ch1_bits = [ float(x) if x is not None else None for x in dat[:1024] ]
			self.ch1 = [ x * scale1 if x is not None else None for x in self.ch1_bits]

			smpls = int(len(self.raw2) / 4)
			dat = struct.unpack('<' + 'i' * smpls, self.raw2)
			dat = [ x if x != -0x80000000 else None for x in dat ]

			self.ch2_bits = [ float(x) if x is not None else None for x in dat[:1024] ]
			self.ch2 = [ x * scale2 if x is not None else None for x in self.ch2_bits]
		except (IndexError, TypeError, struct.error):
			# If the data is bollocksed, force a reinitialisation on next packet
			log.exception("Oscilloscope packet")
			self.frameid = None
			self.complete = False

		return True

class IIRFilterBox(_CoreOscilloscope):
	""" Oscilloscope instrument object. This should be instantiated and attached to a :any:`Moku` instance.

	.. automethod:: pymoku.instruments.Oscilloscope.__init__

	.. attribute:: hwver

		Hardware Version

	.. attribute:: hwserial

		Hardware Serial Number

	.. attribute:: framerate
		:annotation: = 10

		Frame Rate, range 1 - 30.

	.. attribute:: type
		:annotation: = "oscilloscope"

		Name of this instrument.

	"""


	def __init__(self):
		"""Create a new Oscilloscope instrument, ready to be attached to a Moku."""
		super(IIRFilterBox, self).__init__()
		self._register_accessors(_iir_reg_handlers)

		self.id = 6
		self.type = "iirfilterbox"
		self.calibration = None

		#self.logname = "MokuDataloggerData"
		#self.binstr = "<s32"
		#self.procstr = ["*C","*C"]
		#self.timestep = 1

		#self.decimation_rate = 1

		self.scales = {}

		#self.set_frame_class(IIRFilterFrame, scales=self.scales)

	def set_defaults(self):
		""" Reset the Oscilloscope to sane defaults. """
		super(IIRFilterBox, self).set_defaults()

		# #Default values
		self.ch1_input = 0
		self.ch1_output = 0
		self.ch2_input = 0
		self.ch2_output = 0

		self.ch0_ch0gain = 1.0
		self.ch0_ch1gain = 0.0
		self.ch1_ch0gain = 0.0
		self.ch1_ch1gain = 1.0

		self.ch1_sampling_freq = 0
		self.ch2_sampling_freq = 0

		self.filter_reset = 0

		self.inputscale_ch1 = 2**9
		self.inputscale_ch2 = 2**9
		self.outputscale_ch1 = 2**6
		self.outputscale_ch2 = 2**6

		self.inputoffset_ch1 = 0
		self.inputoffset_ch2 = 0
		self.outputoffset_ch1 = 0
		self.outputoffset_ch2 = 0

		self.fiftyr_ch1 = True
		self.atten_ch1 = False
		self.ac_ch1 = False

		self.fiftyr_ch2 = True
		self.atten_ch2 = False
		self.ac_ch2 = False

		# initiliase filter coefficient arrays as all pass filters
		b = [1.0,1.0,0.0,0.0,0.0,0.0]
		self.filter_ch1 = [b,b,b,b]
		self.filter_ch2 = [b,b,b,b]

		self.set_frontend(1,fiftyr=True, atten=False, ac=False)
		self.set_frontend(2,fiftyr=True, atten=False, ac=False)


	@needs_commit
	def set_filter_io(self, ch = 1, input_switch = 'off', output_switch = 'off', impedance = 'low', attenuation = 'off', coupling = 'dc'):
		"""
		Configure filter channel I/O and front-end settings

		:type ch : int; {1,2}
		:param ch : target channel

		:type input_switch : string; {'off', 'on'}
		:param input_switch : toggle input on/off

		:type output_switch : string; {'off', 'on'}
		:param output_switch : toggle output on/off	

		:type impedance : string; {'low', 'high'}
		:param impedance : toggle front-end input impedance, low = 50 Z, high = 1M Z

		:type attenuation : string; {'off', 'on'}
		:param attenuation : toggle front-end input attenuation, off = no attenuation, on = 20 dB attenuation

		:type coupling : string; {'ac', 'dc'}
		:param coupling : toggle front-end coupling, ac = AC coupling, dc = DC coupling					
		"""
		_utils.check_parameter_valid('set', ch, [1,2],'filter channel')
		_utils.check_parameter_valid('set', input_switch, ['off','on'],'input switch')
		_utils.check_parameter_valid('set', output_switch, ['off','on'],'output switch')
		_utils.check_parameter_valid('set', impedance, ['low','high'],'input impedance')
		_utils.check_parameter_valid('set', attenuation, ['off','on'],'input attenuation')
		_utils.check_parameter_valid('set', coupling, ['ac','dc'],'input coupling')

		fiftyr = True if impedance == 'low' else False
		atten = True if attenuation == 'on' else False
		ac = True if coupling == 'ac' else False

		if ch == 1:
			self.ch1_input = 1 if input_switch == 'on' else 0
			self.ch1_output = 1 if output_switch == 'on' else 0
			self.fiftyr_ch1 = fiftyr
			self.atten_ch1 = atten
			self.ac_ch1 = ac
			self._set_frontend(channel = 1, fiftyr = fiftyr, atten = atten, ac = ac)
		else:
			self.ch2_input = 1 if input_switch == 'on' else 0
			self.ch2_output = 1 if output_switch == 'on' else 0
			self.fiftyr_ch2 = fiftyr
			self.atten_ch2 = atten
			self.ac_ch2 = ac
			self._set_frontend(channel = 2, fiftyr = fiftyr, atten = atten, ac = ac)			

	@needs_commit
	def set_filter_settings(self, ch = 1, sample_rate = 'high', filter_array = None):
		"""
		Set SOS filter sample rate and send filter coefficients to the device via the memory map

		:type ch : int; {1,2}
		:param ch : target channel

		:type sample_rate : string; {'off','on'}
		:param sample_rate : set sos sample rate

		:type filter_array : array; 
		:param filter_array : array containing SOS filter coefficients
		"""

		_utils.check_parameter_valid('set', ch, [1,2],'filter channel')
		_utils.check_parameter_valid('set', sample_rate, ['high','low'],'input switch')

		# check filter array dimensions
		if len(filter_array) != 5:
			raise ValueOutOfRangeException("Filter array dimensions are incorrect")
		for m in range(4):
			if m == 0:
				if len(filter_array[0]) != 1:
					raise ValueOutOfRangeException("Filter array dimensions are incorrect")
			else:
				if len(filter_array[m]) != 6:
					raise ValueOutOfRangeException("Filter array dimensions are incorrect")

		#check if filter array values are within required bounds:
		if filter_array[0][0] >= 8e6 or filter_array[0][0] < -8e6:
			raise ValueOutOfRangeException("Filter array gain factor is out of bounds")

		for m in range(4):
			for n in range(6):
				if filter_array[m+1][n] >= 4.0 or filter_array[m+1][n] < -4.0:
					raise ValueOutOfRangeException("Filter array entry m = %d, n = %d is out of bounds"%(m+1,n))

		if ch == 1:
			self.ch1_sampling_freq = 0 if sample_rate == 'high' else 1
		else:
			self.ch2_sampling_freq = 0 if sample_rate == 'high' else 1

		intermediate_filter = filter_array #self.filter_ch1 if ch == 1 else self.filter_ch2

		# multiply S coefficients into B coefficients and replace all S coefficients with 1.0
		for n in range(4):
			intermediate_filter[n+1][1] *= intermediate_filter[n+1][0]
			intermediate_filter[n+1][2] *= intermediate_filter[n+1][0]
			intermediate_filter[n+1][3] *= intermediate_filter[n+1][0]
			intermediate_filter[n+1][0] = 1.0

		# place gain factor G into S coefficient position 4 to comply with HDL requirements:
		intermediate_filter[4][0] = intermediate_filter[0][0]
		intermediate_filter = intermediate_filter[1:5]

		if ch == 1:
			self.filter_ch1 = intermediate_filter
		else:
			self.filter_ch2 = intermediate_filter

		# combine both filter arrays to the format required for memory map access:
		filter_coeffs = [[0.0]*6]*4
		coeff_list = [ [ [0 for k in range(2)] for x in range(6)] for y in range(8) ]
		for n in range(4):
		 	filter_coeffs[n] = self.filter_ch1[n] + self.filter_ch2[n]

		for k in range(2):
			for x in range(4):
					for y in range(6):
						if y == 0:
							coeff_list[x][y][k] = int(round( 2**(_IIR_COEFFWIDTH - 24) * filter_coeffs[x][y + k*6]))
						else:
							coeff_list[x][y][k] = int(round( 2**(_IIR_COEFFWIDTH - 3) * filter_coeffs[x][y + k*6]))

		with open('data.dat', 'wb') as f:
			for k in range(2):
				for y in range(6):
					for x in range(4):
						f.write(struct.pack('<Q', coeff_list[x][y][k] & 0xFFFFFFFFFFFFFFFF))

		self._set_mmap_access(True)
		self._moku._send_file('j', 'data.dat')
		self._set_mmap_access(False)


	@needs_commit
	def set_instrument_gains(self, ch = 1, input_scale = 0, output_scale = 0, input_offset = 0, output_offset = 0, matrix_scalar_ch1 = 1, matrix_scalar_ch2 = 1):
		"""
		Configure non-SOS filterbox settings for specified channel

		:type ch : int
		:param ch : target channel

		:type input_scale, output_scale : int, dB
		:param input_scale, output_scale : channel scalars before and after the IIR filter

		:type input_offset, output_offset : int, mW
		:param input_offset, output_offset : channel offsets before and after the IIR filter

		:type matrix_scalar_ch1 : int, linear scalar
		:param matrix_scalar_ch1 : scalar controlling proportion of signal coming from channel 1 that is added to the current filter channel

		:type matrix_scalar_ch2 : int, linear scalar
		:param matrix_scalar_ch2 : scalar controlling proportion of signal coming from channel 2 that is added to the current filter channel
		"""
		_utils.check_parameter_valid('set', ch, [1,2],'filter channel')
		_utils.check_parameter_valid('range', input_scale, [-40,40],'input scale','dB')
		_utils.check_parameter_valid('range', output_scale, [-40,40],'output scale','dB')
		_utils.check_parameter_valid('range', input_offset, [-500,500],'input offset','mW')
		_utils.check_parameter_valid('range', output_offset, [-500,500],'output offset','mW')
		_utils.check_parameter_valid('range', matrix_scalar_ch1, [0,20],'matrix ch1 scalar','linear scalar')
		_utils.check_parameter_valid('range', matrix_scalar_ch2, [0,20],'matrix ch2 scalar','linear scalar')

		## Get calibration coefficients
		a1, a2 = self._adc_gains()
		d1, d2 = self._dac_gains()		

		adc_calibration = a1 if ch == 1 else a2
		dac_calibration = d1 if ch == 1 else d2

		## Calculate control matrix scale values
		atten1 = 10 if self.atten_ch1 == True else 1.0
		atten2 = 10 if self.atten_ch2 == True else 1.0

		c1 = 375.0 * adc_calibration / atten1
		c2 = 375.0 * adc_calibration / atten2

		control_matrix_ch1 = int(round(matrix_scalar_ch1 * c1 * 2**10)) 
		control_matrix_ch2 = int(round(matrix_scalar_ch2 * c2 * 2**10)) 

		## Calculate input/output scale values
		output_gain_factor = 1 / 375.0 / 8 / dac_calibration
		self.input_scale = int(round(10**(round(input_scale)/20)*2**9))
		self.output_scale = int(round(10**(round(output_scale)/20)*2**6 * output_gain_factor))

		## Calculate input/output offset values
		self.input_offset = int(round(375.0 * round(input_offset) / 500.0))
		self.output_offset = int(round(1 / dac_calibration / 2 * output_offset / 500.0))

		if ch == 1:
			self.inputscale_ch1 = self.input_scale
			self.outputscale_ch1 = self.output_scale
			self.inputoffset_ch1 = self.input_offset
			self.outputoffset_ch1 = self.output_offset
			self.ch0_ch0gain = control_matrix_ch1
			self.ch0_ch1gain = control_matrix_ch2
		else:
			self.inputscale_ch2 = self.input_scale
			self.outputscale_ch2 = self.output_scale
			self.inputoffset_ch2 = self.input_offset
			self.outputoffset_ch2 = self.output_offset
			self.ch1_ch0gain = control_matrix_ch1
			self.ch1_ch1gain = control_matrix_ch2

	@needs_commit
	def _set_mmap_access(self, access):
		self.mmap_access = access

	@needs_commit
	def set_monitor(self, ch, source = 'in ch1'):
		"""
		Select the point inside the filterbox to monitor.

		There are two monitoring channels available, '1' and '2'; you can mux any of the internal
		monitoring points to either of these channels.

		The source is one of:
			- **in ch1**		: CH 1 ADC Input
			- **in ch1 offset**	: Filter CH 1 After Input Offset
			- **out ch1**		: Filter CH 1 Output
			- **in ch2**		: CH 2 ADC Input
			- **in ch2 offset**	: Filter CH 2 After Input Offset
			- **out ch2**		: Filter CH 2 Output
		"""
		sources = {
			'in ch1' 		: _IIR_MON_IN_CH1,
			'in ch1 offset' : _IIR_MON_IN_CH1OFF,
			'out ch1'		: _IIR_MON_OUT_CH1,
			'in ch2' 		: _IIR_MON_IN_CH2,
			'in ch2 offset' : _IIR_MON_IN_CH2OFF,
			'out ch2'		: _IIR_MON_OUT_CH2,
		}

		source = source.lower()

		if ch == 1:
			self.monitor_select0 = sources[source]
		elif ch == 2:
			self.monitor_select1 = sources[source]
		else:
			raise ValueOutOfRangeException("Invalid channel %d", ch)


_iir_reg_handlers = {
	'monitor_select0':	(REG_MONSELECT,		to_reg_unsigned(0,3), from_reg_unsigned(0,3)),
	'monitor_select1':	(REG_MONSELECT,		to_reg_unsigned(3,3), from_reg_unsigned(3,3)),

	'ch1_input':		(REG_ENABLE,			to_reg_unsigned(0,1), from_reg_unsigned(0,1)),
	'ch2_input':		(REG_ENABLE,			to_reg_unsigned(1,1), from_reg_unsigned(1,1)),
	'ch1_output':		(REG_ENABLE,			to_reg_unsigned(2,1), from_reg_unsigned(2,1)),
	'ch2_output':		(REG_ENABLE,			to_reg_unsigned(3,1), from_reg_unsigned(3,1)),

	'ch0_ch0gain':		(REG_CH0_CH0GAIN, 	to_reg_signed(0,16), from_reg_signed(0,16)),
	'ch0_ch1gain':		(REG_CH0_CH1GAIN,	to_reg_signed(0,16), from_reg_signed(0,16)),
	'ch1_ch0gain':		(REG_CH1_CH0GAIN,	to_reg_signed(0,16), from_reg_signed(0,16)),
	'ch1_ch1gain':		(REG_CH1_CH1GAIN,	to_reg_signed(0,16), from_reg_signed(0,16)),

	'ch1_sampling_freq':	(REG_SAMPLINGFREQ,		to_reg_unsigned(0, 1), from_reg_unsigned(0, 1)),
	'ch2_sampling_freq':	(REG_SAMPLINGFREQ,		to_reg_unsigned(1, 1), from_reg_unsigned(1, 1)),

	'filter_reset':		(REG_FILT_RESET, 		to_reg_bool(0), from_reg_bool(0)),

	'inputscale_ch1':	(REG_INPUTSCALE_CH0,	to_reg_unsigned(0, 18), from_reg_unsigned(0, 18)),	
	'inputscale_ch2':	(REG_INPUTSCALE_CH1,	to_reg_unsigned(0, 18), from_reg_unsigned(0, 18)),

	'outputscale_ch1':	(REG_OUTPUTSCALE_CH0,	to_reg_unsigned(0, 18), from_reg_unsigned(0, 18)),
	'outputscale_ch2':	(REG_OUTPUTSCALE_CH1,	to_reg_unsigned(0, 18), from_reg_unsigned(0, 18)),

	'inputoffset_ch1':	(REG_INPUTOFFSET_CH0,	to_reg_signed(0, 13), from_reg_signed(0, 13)),	
	'inputoffset_ch2':	(REG_INPUTOFFSET_CH1,	to_reg_signed(0, 13), from_reg_signed(0, 13)),	

	'outputoffset_ch1':	(REG_OUTPUTOFFSET_CH0,	to_reg_signed(0, 16), from_reg_signed(0, 16)),	
	'outputoffset_ch2':	(REG_OUTPUTOFFSET_CH1,	to_reg_signed(0, 16), from_reg_signed(0, 16))
}