
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

REG_FILT_RESET 		= 62

_IIR_MON_IN_CH1 		= 0
_IIR_MON_IN_CH1OFF		= 1
_IIR_MON_OUT_CH1		= 2
_IIR_MON_IN_CH2 		= 3
_IIR_MON_IN_CH2OFF 		= 4
_IIR_MON_OUT_CH2 		= 5
_IIR_COEFFWIDTH = 48

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

		self.scales = {}

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

		# initialize filter coefficient arrays as all pass filters
		b = [1.0,1.0,0.0,0.0,0.0,0.0]
		self.filter_ch1 = [b,b,b,b]
		self.filter_ch2 = [b,b,b,b]

		# do we want to set here? 
		self.set_frontend(1,fiftyr=True, atten=False, ac=False)
		self.set_frontend(2,fiftyr=True, atten=False, ac=False)


	@needs_commit
	def set_filter_io(self, ch = 1, input_switch = False, output_switch = False):
		"""
		Configure filter channel I/O and front-end settings

		:type ch : int; {1,2}
		:param ch : target channel

		:type input_switch : bool;
		:param input_switch : toggle input on(true)/off(false)

		:type output_switch : bool; 
		:param output_switch : toggle output on(true)/off(false)			
		"""
		_utils.check_parameter_valid('set', ch, [1,2],'filter channel')
		_utils.check_parameter_valid('bool', input_switch, desc = 'input switch')
		_utils.check_parameter_valid('bool', output_switch, desc = 'output switch')

		if ch == 1:
			self.ch1_input = input_switch
			self.ch1_output = output_switch

		else:
			self.ch2_input = input_switch
			self.ch2_output = output_switch
			

	@needs_commit
	def set_filter_settings(self, ch = 1, sample_rate = 'high', filter_array = None):
		"""
		Set SOS filter sample rate and send filter coefficients to the device via the memory map.

		Moku:DigitalFilterBox implements infinite impulse resposne (IIR) filters using 4 cascaded Direct Form 1 second-order stages
		with a final output gain stage. The total transfer function can be written:

		H(Z) = G * prod(1 <= k <= 4) : sk * [b0,k + b1,k * z^-1 + b2,k * z^-2] / [1 + a1,k * z^-1 + a2,k * z^-2]

		To specify a filter, you must supply an array containing the filter coefficients. The array should contain five rows and six columns. 
		The first row has one column entry, corresponding to the overall gain factor G. The following four rows have six entries each, corresponding
		to the s, b0, b1, b2, a1 and a2 coefficients of the four cascaded SOS filters. 

		Each coefficient must be in the range [-4.0, +4.0). Internally, these are represented as signed 48-bit fixed-point numbers, with 45 fractional bits.

		Example array dimensions:

	 	[[G],
		[s1, b0.1, b1.1, b2.1, a1.1, a2.1],
		[s2, b0.2, b1.2, b2.2, a1.2, a2.2],
		[s3, b0.3, b1.3, b2.3, a1.3, a2.3],
		[s4, b0.4, b1.4, b2.4, a1.4, a2.4]]

		:type ch : int; {1,2}
		:param ch : target channel

		:type sample_rate : string; {'high','low'}
		:param sample_rate : set sos sample rate

		:type filter_array : array; 
		:param filter_array : array containing SOS filter coefficients
		"""

		print(filter_array)

		_utils.check_parameter_valid('set', ch, [1,2],'filter channel')
		_utils.check_parameter_valid('set', sample_rate, ['high','low'],'sample rate')

		# check filter array dimensions
		if len(filter_array) != 5:
			#raise ValueOutOfRangeException("Filter array dimensions are incorrect")
			_utils.check_parameter_valid('set', len(filter_array), [5],'number of coefficient array rows')
		for m in range(4):
			if m == 0:
				if len(filter_array[0]) != 1:
					#raise ValueOutOfRangeException("Filter array dimensions are incorrect")
					_utils.check_parameter_valid('set', len(filter_array[0]), [1],'number of columns in coefficient array row 0')
			else:
				if len(filter_array[m]) != 6:
					#raise ValueOutOfRangeException("Filter array dimensions are incorrect")
					#exception_string = "number of columns in coefficient array row "
					_utils.check_parameter_valid('set', len(filter_array[m]), [6],("number of columns in coefficient array row %s"%(m)))

		#check if filter array values are within required bounds:
		#if filter_array[0][0] >= 8e6 or filter_array[0][0] < -8e6:
			#raise ValueOutOfRangeException("Filter array gain factor is out of bounds")
			#raise ValueOutOfRangeException("Invalid parameter Filter array gain factor is out of bounds")

		_utils.check_parameter_valid('range', filter_array[0][0], [-8e6,8e6 - 2**(-24)],("coefficient array entry m = %s, n = %s"%(0,0)))

		for m in range(1, 5):
			for n in range(6):
				_utils.check_parameter_valid('range', filter_array[m][n], [-4.0,4.0 - 2**(-45)],("coefficient array entry m = %s, n = %s"%(0,0)))
				#if filter_array[m][n] >= 4.0 or filter_array[m][n] < -4.0:
				#	raise ValueOutOfRangeException("Filter array entry m = %d, n = %d is out of bounds"%(m,n))


		if ch == 1:
			self.ch1_sampling_freq = 0 if sample_rate == 'high' else 1
		else:
			self.ch2_sampling_freq = 0 if sample_rate == 'high' else 1

		intermediate_filter = filter_array 

		# multiply S coefficients into B coefficients and replace all S coefficients with 1.0
		for n in range(1,5):
			intermediate_filter[n][1] *= intermediate_filter[n][0]
			intermediate_filter[n][2] *= intermediate_filter[n][0]
			intermediate_filter[n][3] *= intermediate_filter[n][0]
			intermediate_filter[n][0] = 1.0

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

		:type ch : int, {1,2}
		:param ch : target channel

		:type input_scale, output_scale : int, dB, [-40,40]
		:param input_scale, output_scale : channel scalars before and after the IIR filter

		:type input_offset, output_offset : int, mW, [-500,500]
		:param input_offset, output_offset : channel offsets before and after the IIR filter

		:type matrix_scalar_ch1 : int, linear scalar, [0,20]
		:param matrix_scalar_ch1 : scalar controlling proportion of signal coming from channel 1 that is added to the current filter channel

		:type matrix_scalar_ch2 : int, linear scalar, [0,20]
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

		front_end = self._get_frontend(channel = 1) if ch == 1 else self._get_frontend(channel = 2)
		atten = 10.0 if front_end[1] else 1.0

		adc_calibration = a1 if ch == 1 else a2
		dac_calibration = d1 if ch == 1 else d2

		control_matrix_ch1 = int(round(matrix_scalar_ch1 * 375.0 * adc_calibration * 2**10 / atten)) 
		control_matrix_ch2 = int(round(matrix_scalar_ch2 * 375.0 * adc_calibration * 2**10 / atten)) 

		## Calculate input/output scale values
		output_gain_factor = 1 / 375.0 / 8 / dac_calibration
		input_scale_bits = int(round(10**(round(input_scale)/20)*2**9))
		output_scale_bits = int(round(10**(round(output_scale)/20)*2**6 * output_gain_factor))

		## Calculate input/output offset values
		input_offset_bits = int(round(375.0 * round(input_offset) / 500.0))
		output_offset_bits = int(round(1 / dac_calibration / 2 * output_offset / 500.0))

		if ch == 1:
			self.inputscale_ch1 = input_scale_bits
			self.outputscale_ch1 = output_scale_bits
			self.inputoffset_ch1 = input_offset_bits
			self.outputoffset_ch1 = output_offset_bits
			self.ch0_ch0gain = control_matrix_ch1
			self.ch0_ch1gain = control_matrix_ch2
		else:
			self.inputscale_ch2 = input_scale_bits
			self.outputscale_ch2 = output_scale_bits
			self.inputoffset_ch2 = input_offset_bits
			self.outputoffset_ch2 = output_offset_bits
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