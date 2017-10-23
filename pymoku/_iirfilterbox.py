
import math
import logging
from copy import deepcopy
from pymoku._oscilloscope import _CoreOscilloscope
from ._instrument import *
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
	r"""

	The IIR Filter Box implements infinite impulse resposne (IIR) filters using 4 cascaded Direct Form 1 second-order stages
	with a final output gain stage. The total transfer function can be written:

	.. math::
		H(z) = G * \prod_{k=1}^4 s_k * \frac{b_0k + b_1k * z^-1 + b_2k * z^-2}{1 + a_1k * z^-1 + a_2k * z^-2}

	To specify a filter, you must supply an array containing the filter coefficients. The array should contain five rows and six columns.
	The first row has one column entry, corresponding to the overall gain factor G. The following four rows have six entries each, corresponding
	to the s, b0, b1, b2, a1 and a2 coefficients of the four cascaded SOS filters.

	Example array dimensions:

	+----------+------+------+------+------+-------+
	| G        |      |      |      |      |       |
	+==========+======+======+======+======+=======+
	| s1       | b0.1 | b1.1 | b2.1 | a1.1 |  a2.1 |
	+----------+------+------+------+------+-------+
	| s2       | b0.2 | b1.2 | b2.2 | a1.2 |  a2.2 |
	+----------+------+------+------+------+-------+
	| s3       | b0.3 | b1.3 | b2.3 | a1.3 |  a2.3 |
	+----------+------+------+------+------+-------+
	| s4       | b0.4 | b1.4 | b2.4 | a1.4 |  a2.4 |
	+----------+------+------+------+------+-------+

	Each coefficient must be in the range [-4.0, +4.0). Internally, these are represented as signed 48-bit fixed-point numbers, with 45 fractional bits.
	The output scaling can be up to 8,000,000. Filter coefficients can be computed using signal processing toolboxes in e.g. MATLAB or SciPy.

	.. note::
		The overall output gain of the instrument is the product of the gain of the filter, set in the coefficient matrix, and the output stage
		gain set using :any:`set_offset_gain`.

	.. warning::
		Some coefficients may result in overflow or underflow, which degrade filter performance. Filter responses should be checked prior to use.

	"""


	def __init__(self):
		"""Create a new IIR FilterBox instrument, ready to be attached to a Moku."""
		super(IIRFilterBox, self).__init__()
		self._register_accessors(_iir_reg_handlers)

		self.id = 6
		self.type = "iirfilterbox"

	def set_defaults(self):
		""" Reset the Oscilloscope to sane defaults. """
		super(IIRFilterBox, self).set_defaults()

		# #Default values
		self.ch1_input = True
		self.ch1_output = False
		self.ch2_input = True
		self.ch2_output = False

		self.ch0_ch0gain = 0.0
		self.ch0_ch1gain = 0.0
		self.ch1_ch0gain = 0.0
		self.ch1_ch1gain = 0.0

		self.ch1_sampling_freq = 0
		self.ch2_sampling_freq = 0

		self.filter_reset = 0

		self.inputscale_ch1 = 0
		self.inputscale_ch2 = 0
		self.outputscale_ch1 = 0
		self.outputscale_ch2 = 0

		self.inputoffset_ch1 = 0
		self.inputoffset_ch2 = 0
		self.outputoffset_ch1 = 0
		self.outputoffset_ch2 = 0

		# initialize filter coefficient arrays as all pass filters
		b = [1.0,1.0,0.0,0.0,0.0,0.0]
		self.filter_ch1 = [b,b,b,b]
		self.filter_ch2 = [b,b,b,b]

		# do we want to set here?
		self.set_frontend(1,fiftyr=True, atten=False, ac=False)
		self.set_frontend(2,fiftyr=True, atten=False, ac=False)

		# Default unity gain, zero offset, identiy mixing matrix.
		self.set_offset_gain(1)
		self.set_offset_gain(2)


	@needs_commit
	def set_filter(self, ch, sample_rate, filter_coefficients):
		"""
		Set SOS filter sample rate and filter coefficients.

		:type ch : int; {1,2}
		:param ch : target channel

		:type sample_rate : string; {'high','low'}
		:param sample_rate : filter sample rate. High = 15.625 MHz, low = 122.070 KHz

		:type filter_coefficients : array;
		:param filter_coefficients : array containing SOS filter coefficients. The array format can be seen in the class documentation above
		"""

		_utils.check_parameter_valid('set', ch, [1,2],'filter channel')
		_utils.check_parameter_valid('set', sample_rate, ['high','low'],'sample rate')
		_utils.check_parameter_valid('bool', output_off, desc = 'disable output')

		if ch == 1:
			self.ch1_output = True
			self.ch1_sampling_freq = 0 if sample_rate == 'high' else 1
		else:
			self.ch2_output = True
			self.ch2_sampling_freq = 0 if sample_rate == 'high' else 1


		## The following converts the input filter coefficient array into a format required by the memory map to correctly configure the HDL.
		## We don't use this modified format for the input array to reduce the amount of coefficient manipulation a user must perform after generating them in Matlab/Scipy, etc.

		if filter_coefficients != None:

			# deep copy the filter coefficient array as it is modified below and potentially used by further set_filter_settings function calls
			intermediate_filter = deepcopy(filter_coefficients)

			# check filter array dimensions
			if len(filter_coefficients) != 5:
				_utils.check_parameter_valid('set', len(filter_coefficients), [5],'number of coefficient array rows')
			for m in range(4):
				if m == 0:
					if len(filter_coefficients[0]) != 1:
						_utils.check_parameter_valid('set', len(filter_coefficients[0]), [1],'number of columns in coefficient array row 0')
				else:
					if len(filter_coefficients[m]) != 6:
						_utils.check_parameter_valid('set', len(filter_coefficients[m]), [6],("number of columns in coefficient array row %s"%(m)))

			# check if filter array values are within required bounds:
			_utils.check_parameter_valid('range', filter_coefficients[0][0], [-8e6,8e6 - 2**(-24)],("coefficient array entry m = %s, n = %s"%(0,0)))
			for m in range(1, 5):
				for n in range(6):
					_utils.check_parameter_valid('range', filter_coefficients[m][n], [-4.0,4.0 - 2**(-45)],("coefficient array entry m = %s, n = %s"%(0,0)))


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

		# combine both filter arrays:
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

		with open('.data.dat', 'wb') as f:
			for k in range(2):
				for y in range(6):
					for x in range(4):
						f.write(struct.pack('<q', coeff_list[x][y][k]))

		self._set_mmap_access(True)
		self._moku._send_file('j', '.data.dat')
		self._set_mmap_access(False)
		os.remove('.data.dat')


	@needs_commit
	def set_offset_gain(self, ch, input_scale=1, output_scale=1, input_offset=0, output_offset=0, matrix_scalar_ch1=None, matrix_scalar_ch2=None):
		"""
		Configure pre- and post-filter scales, offsets and input mixing for a channel.

		Input mixing allows one filter to act on a linear combination of the two input signals. If *matrix_scalar_ch[12]* are left blank,
		the input matrix is set to the identitiy; that is, filter channel 1 comes only from input channel 1 etc.

		.. note::
			The overall output gain of the instrument is the product of the gain of the filter, set by the filter coefficients,
			and the output stage gain set here.

		:type ch : int, {1,2}
		:param ch : target channel

		:type input_scale, output_scale : int, linear scalar, [0,100]
		:param input_scale, output_scale : channel scalars before and after the IIR filter

		:type input_offset, output_offset : int, mV, [-500,500]
		:param input_offset, output_offset : channel offsets before and after the IIR filter

		:type matrix_scalar_ch1 : int, linear scalar, [0,20]
		:param matrix_scalar_ch1 : scalar controlling proportion of signal coming from channel 1 that is added to the current filter channel

		:type matrix_scalar_ch2 : int, linear scalar, [0,20]
		:param matrix_scalar_ch2 : scalar controlling proportion of signal coming from channel 2 that is added to the current filter channel
		"""
		_utils.check_parameter_valid('set', ch, [1,2],'filter channel')
		_utils.check_parameter_valid('range', input_scale, [0,100],'input scale','linear scalar')
		_utils.check_parameter_valid('range', output_scale, [0,100],'output scale','linear scalar')
		_utils.check_parameter_valid('range', input_offset, [-500,500],'input offset','mV')
		_utils.check_parameter_valid('range', output_offset, [-500,500],'output offset','mV')
		_utils.check_parameter_valid('range', matrix_scalar_ch1, [0,20],'matrix ch1 scalar','linear scalar')
		_utils.check_parameter_valid('range', matrix_scalar_ch2, [0,20],'matrix ch2 scalar','linear scalar')

		## Get calibration coefficients
		a1, a2 = self._adc_gains()
		d1, d2 = self._dac_gains()

		front_end = self._get_frontend(channel = 1) if ch == 1 else self._get_frontend(channel = 2)
		atten = 10.0 if front_end[1] else 1.0

		adc_calibration = a1 if ch == 1 else a2
		dac_calibration = d1 if ch == 1 else d2

		if matrix_scalar_ch1 is None:
			matrix_scalar_ch1 = 1 if ch == 1 else 0

		if matrix_scalar_ch2 is None:
			matrix_scalar_ch2 = 1 if ch == 2 else 0

		control_matrix_ch1 = int(round(matrix_scalar_ch1 * 375.0 * adc_calibration * 2**10 / atten))
		control_matrix_ch2 = int(round(matrix_scalar_ch2 * 375.0 * adc_calibration * 2**10 / atten))

		## Calculate input/output scale values
		output_gain_factor = 1 / 375.0 / 8 / dac_calibration
		input_scale_bits = int(round(input_scale*2**9))
		output_scale_bits = int(round(output_scale*2**6*output_gain_factor))

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
	def set_monitor(self, ch, source):
		"""
		Select the point inside the filterbox to monitor.

		There are two monitoring channels available, '1' and '2'; you can mux any of the internal
		monitoring points to either of these channels.

		The source is one of:
			- **adc1**	: CH 1 ADC Input
			- **in1**	: Filter CH 1 After Input Offset
			- **out1**	: Filter CH 1 Output
			- **adc2**	: CH 2 ADC Input
			- **in2**	: Filter CH 2 After Input Offset
			- **out2**	: Filter CH 2 Output
		"""
		_utils.check_parameter_valid('set', ch, [1,2],'filter channel')

		sources = {
			'adc1': _IIR_MON_IN_CH1,
			'in1':	_IIR_MON_IN_CH1OFF,
			'out1': _IIR_MON_OUT_CH1,
			'adc2': _IIR_MON_IN_CH2,
			'in2':	_IIR_MON_IN_CH2OFF,
			'out2':	_IIR_MON_OUT_CH2,
		}

		source = source.lower()

		if ch == 1:
			self.monitor_select0 = sources[source]
		else:
			self.monitor_select1 = sources[source]


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