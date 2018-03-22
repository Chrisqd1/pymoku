
import math, time
import logging
from copy import deepcopy
from pymoku._oscilloscope import _CoreOscilloscope
from ._instrument import *
from . import _utils
from ._dec_filter import DecFilter


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

_IIR_MON_NONE		= 0
_IIR_MON_IN1 		= 1
_IIR_MON_INCH1		= 2
_IIR_MON_OUT1		= 3
_IIR_MON_IN2 		= 4
_IIR_MON_INCH2 		= 5
_IIR_MON_OUT2 		= 6
_IIR_COEFFWIDTH = 48

_IIR_INPUT_SMPS = ADC_SMP_RATE/4
_IIR_CHN_BUFLEN = 2**13

class IIRFilterBox(_CoreOscilloscope):
	r"""

	The IIR Filter Box implements infinite impulse response (IIR) filters using 4 cascaded Direct Form 1 second-order stages
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
		gain set using :any:`set_gains_offsets`.

	.. warning::
		Some coefficients may result in overflow or underflow, which degrade filter performance. Filter responses should be checked prior to use.

	"""
	def __init__(self):
		"""Create a new IIR FilterBox instrument, ready to be attached to a Moku."""
		super(IIRFilterBox, self).__init__()
		self._register_accessors(_iir_reg_handlers)

		self.id = 6
		self.type = "iirfilterbox"

		# Monitor samplerate
		self._input_samplerate = _IIR_INPUT_SMPS
		self._chn_buffer_len = _IIR_CHN_BUFLEN

		# Remembers monitor source choice
		self.monitor_a = None
		self.monitor_b = None

		self._decfilter1 = DecFilter(self, 103)
		self._decfilter2 = DecFilter(self, 107)

	@needs_commit
	def set_defaults(self):
		""" Reset the IIR to sane defaults. """
		super(IIRFilterBox, self).set_defaults()

		# Default values
		self.input_en1 = True
		self.output_en1 = False
		self.input_en2 = True
		self.output_en2 = False

		self.set_control_matrix(1, 1.0, 0.0)
		self.set_control_matrix(2, 0.0, 1.0)

		self.ch1_sampling_freq = 0
		self.ch2_sampling_freq = 0

		self.filter_reset = 0

		self.input_scale1 = 0
		self.input_scale2 = 0
		self.output_scale1 = 0
		self.output_scale2 = 0

		self.input_offset1 = 0
		self.input_offset2 = 0
		self.output_offset1 = 0
		self.output_offset2 = 0

		# initialize filter coefficient arrays as all pass filters
		b = [1.0,1.0,0.0,0.0,0.0,0.0]
		self.filter_ch1 = [b,b,b,b]
		self.filter_ch2 = [b,b,b,b]

		# do we want to set here?
		self.set_frontend(1,fiftyr=True, atten=False, ac=False)
		self.set_frontend(2,fiftyr=True, atten=False, ac=False)

		# Default unity gain, zero offset, identity mixing matrix.
		self.set_gains_offsets(1)
		self.set_gains_offsets(2)

	@needs_commit
	def set_control_matrix(self, ch, scale_in1, scale_in2):
		"""
		Configure the input control matrix specifying the input signal mixing for the specified filter channel.

		Input mixing allows a filter channel to act on a linear combination of the two input signals.

		:type ch: int, {1,2}
		:param ch: target filter channel

		:type scale_in1: float, [-20,20]
		:param scale_in1: linear scale factor of input 1 signal added to target filter channel input.
			To avoid quantization, use at most one decimal place.

		:type scale_in2: float, [-20,20] 
		:param scale_in2: linear scale factor of input 2 signal added to target filter channel input.
			To avoid quantization, use at most one decimal place.
		"""
		_utils.check_parameter_valid('set', ch, [1, 2], 'filter channel')
		_utils.check_parameter_valid('range', scale_in1, [-20, 20], 'control matrix scale (ch1)', 'linear scalar')
		_utils.check_parameter_valid('range', scale_in2, [-20, 20], 'control matrix scale (ch2)', 'linear scalar')
		if (scale_in1/0.1)%1 or (scale_in2/0.1)%1:
			log.warning("Control matrix scalars should contain one decimal place to avoid quantization effects.")

		# Get calibration coefficients
		a1, a2 = self._adc_gains()
		d1, d2 = self._dac_gains()

		front_end = self._get_frontend(channel = 1) if ch == 1 else self._get_frontend(channel = 2)
		atten = 10.0 if front_end[1] else 1.0

		adc_calibration = a1 if ch == 1 else a2
		dac_calibration = d1 if ch == 1 else d2

		control_matrix_ch1 = int(round(scale_in1 * 3750.0 * adc_calibration * 2**10 / atten))
		control_matrix_ch2 = int(round(scale_in2 * 3750.0 * adc_calibration * 2**10 / atten))

		if ch == 1:
			self.matrixscale_ch1_ch1 = control_matrix_ch1
			self.matrixscale_ch1_ch2 = control_matrix_ch2
		else:
			self.matrixscale_ch2_ch1 = control_matrix_ch1
			self.matrixscale_ch2_ch2 = control_matrix_ch2

	# NOTE: This function avoids @needs_commit because it calls _set_mmap_access which requires an immediate commit
	def set_filter(self, ch, sample_rate, filter_coefficients):
		"""
		Set SOS filter sample rate and filter coefficients. This also enables the input and outputs of the specified Moku:Lab channel.

		:type ch: int; {1,2}
		:param ch: target channel

		:type sample_rate: string; {'high','low'}
		:param sample_rate: filter sample rate where 'high' ~ 15.625 MHz and 'low' ~ 122.070 kHz.

		:type filter_coefficients: array;
		:param filter_coefficients: array containing SOS filter coefficients. Format is described in class documentation above.
		"""
		_utils.check_parameter_valid('set', ch, [1, 2], 'filter channel')
		_utils.check_parameter_valid('set', sample_rate, ['high', 'low'], 'filter sample rate')

		# Set the filter input samplerate
		factor = (8 if sample_rate == 'high' else 1024)
		if ch == 1:
			self._decfilter1.set_samplerate(factor)
		else:
			self._decfilter2.set_samplerate(factor)

		# Conversion of input array (typically generated by Scipy/Matlab) to HDL memory map format
		if filter_coefficients != None:

			# Deep copy to avoid modifying user's original input array 
			intermediate_filter = deepcopy(filter_coefficients)

			# Array dimension check
			if len(filter_coefficients) != 5:
				_utils.check_parameter_valid('set', len(filter_coefficients), [5],'number of coefficient array rows')
			for m in range(4):
				if m == 0:
					if len(filter_coefficients[0]) != 1:
						_utils.check_parameter_valid('set', len(filter_coefficients[0]), [1],'number of columns in coefficient array row 0')
				else:
					if len(filter_coefficients[m]) != 6:
						_utils.check_parameter_valid('set', len(filter_coefficients[m]), [6],("number of columns in coefficient array row %s"%(m)))

			# Array values check
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

		# Enable the output and input of the set channel
		if ch==1:
			self.output_en1 = True
			self.input_en1 = True
		else:
			self.output_en2 = True
			self.input_en2 = True

		# Manually commit the above register settings as @needs_commit is not used in this function
		self.commit()

	@needs_commit
	def disable_output(self, ch):
		"""
		Disables the output of the specified IIR filter channel.

		:type ch: int; {1,2}
		:param ch: target channel
		"""
		if ch == 1:
			self.output_en1 = False
		else:
			self.output_en2 = False

	@needs_commit
	def set_gains_offsets(self, ch, input_gain=1.0, output_gain=1.0, input_offset=0, output_offset=0):
		"""
		Configure pre- and post-filter scales and offsets for a given filter channel.

		.. note::
			The overall output gain of the instrument is the product of the gain of the filter, set by the filter coefficients,
			and the input/output stage gain set here.

		:type ch: int, {1,2}
		:param ch: target filter channel

		:type input_gain, output_gain: float, [-100,100] scalar
		:param input_gain, output_gain: channel scalars before and after the FIR filter

		:type input_offset: float, [-1.0,1.0] Volts
		:param input_offset: channel offset before the FIR filter

		:type output_offset: float, [-2.0,2.0] Volts
		:param output_offset: channel offset after the FIR filter
		"""
		_utils.check_parameter_valid('set', ch, [1,2],'filter channel')
		_utils.check_parameter_valid('range', input_gain, [-100,100],'input scale','linear scalar')
		_utils.check_parameter_valid('range', output_gain, [-100,100],'output scale','linear scalar')
		_utils.check_parameter_valid('range', input_offset, [-1.0,1.0],'input offset','Volts')
		_utils.check_parameter_valid('range', output_offset, [-2.0,2.0],'output offset','Volts')

		# Get calibration coefficients
		a1, a2 = self._adc_gains()
		d1, d2 = self._dac_gains()

		front_end = self._get_frontend(channel = 1) if ch == 1 else self._get_frontend(channel = 2)
		atten = 10.0 if front_end[1] else 1.0

		adc_calibration = a1 if ch == 1 else a2
		dac_calibration = d1 if ch == 1 else d2

		# Calculate input/output scale values
		output_gain_factor = 1 / 3750.0 / 8 / dac_calibration
		input_scale_bits = int(round(input_gain*2**9))
		output_scale_bits = int(round(output_gain*2**9*output_gain_factor))

		# Calculate input/output offset values
		input_offset_bits = int(round(atten / adc_calibration * input_offset / 0.5))
		output_offset_bits = int(round(1 / dac_calibration / 2 * output_offset / 0.5))

		if ch == 1:
			self.input_scale1 = input_scale_bits
			self.output_scale1 = output_scale_bits
			self.input_offset1 = input_offset_bits
			self.output_offset1 = output_offset_bits
		else:
			self.input_scale2 = input_scale_bits
			self.output_scale2 = output_scale_bits
			self.input_offset2 = input_offset_bits
			self.output_offset2 = output_offset_bits

	@needs_commit
	def set_monitor(self, ch, source):
		"""
		Select the point inside the filterbox to monitor.

		There are two monitoring channels available, 'a' and 'b'; you can mux any of the internal
		monitoring points to either of these channels.

		The source is one of:
			- **adc1**	: CH 1 ADC input
			- **in1**	: Filter CH 1 after input offset and mixing
			- **out1**	: Filter CH 1 output
			- **adc2**	: CH 2 ADC input
			- **in2**	: Filter CH 2 after input offset and
			- **out2**	: Filter CH 2 Output

		:param ch: Monitor channel
		:type ch: str ['a', 'b']

		:param source: Signal to connect to this monitor channel
		:type source: str
		"""
		_utils.check_parameter_valid('string', ch, desc="monitor channel")
		_utils.check_parameter_valid('string', source, desc="monitor signal")

		_utils.check_parameter_valid('set', ch, allowed=['a','b'], desc="monitor channel")
		_utils.check_parameter_valid('set', source, allowed=['adc1', 'in1', 'out1', 'adc2', 'in2', 'out2'], desc="monitor source")

		sources = {
			'none': _IIR_MON_NONE,
			'adc1': _IIR_MON_IN1,
			'in1':	_IIR_MON_INCH1,
			'out1': _IIR_MON_OUT1,
			'adc2': _IIR_MON_IN2,
			'in2':	_IIR_MON_INCH2,
			'out2':	_IIR_MON_OUT2,
		}

		ch = ch.lower()
		source = source.lower()

		if ch == 'a':
			self.monitor_a = source
			self.mon1_source = sources[source]
		else:
			self.monitor_b = source
			self.mon2_source = sources[source]

	@needs_commit
	def set_trigger(self, source, edge, level, hysteresis=False, hf_reject=False, mode='auto'):
		"""
			Set the trigger for the monitor signals. This can be either of the input channel signals
			or monitor channel signals.

			:type source: string; {'in1','in2','A','B','ext'}
			:param source: Trigger channel

			:type edge: string, {'rising','falling','both'}
			:param edge: Which edge to trigger on.

			:type level: float, [-10.0, 10.0] volts
			:param level: Trigger level

			:type hysteresis: bool
			:param hysteresis: Enable Hysteresis around trigger point.

			:type hf_reject: bool
			:param hf_reject: Enable high-frequency noise rejection

			:type mode: string, {'auto', 'normal'}
			:param mode: Trigger mode.
		"""
		_utils.check_parameter_valid('string', source, desc="trigger source")
		source = source.lower()
		_utils.check_parameter_valid('set', source, allowed=['in1','in2','a','b','ext'], desc="trigger source")

		# Translate the IIR trigger sources to Oscilloscope sources
		_str_to_osc_trig_source = {
			'a' : 'in1',
			'b' : 'in2',
			'in1' : 'out1',
			'in2' : 'out2',
			'ext' : 'ext'
		}

		source = _utils.str_to_val(_str_to_osc_trig_source, source, 'trigger source')

		super(IIRFilterBox, self).set_trigger(source=source, edge=edge, level=level, hysteresis=hysteresis, hf_reject=hf_reject, mode=mode)

	def _calculate_scales(self):
		# This calculates scaling factors for the internal Oscilloscope frames
		scales = super(IIRFilterBox, self)._calculate_scales()

		# Change the scales we care about
		#deci_gain = self._deci_gain()
		atten1 = self.get_frontend(1)
		atten2 = self.get_frontend(2)

		monitor_source_gains = {
			'none'	: 1.0,
			'adc1'	: scales['gain_adc1']*(10.0 if atten1[1] else 1.0),
			'in1'	: scales['gain_adc1']*(10.0 if atten1[1] else 1.0),
			'out1'	: (scales['gain_dac1']*(2**4)), # 12bit ADC - 16bit DAC
			'adc2'	: scales['gain_adc2']*(10.0 if atten2[1] else 1.0),
			'in2'	: scales['gain_adc2']*(10.0 if atten2[1] else 1.0),
			'out2'	: (scales['gain_dac2']*(2**4))
		}

		# Replace scaling factors depending on the monitor signal source
		scales['scale_ch1'] = 1.0 if not self.monitor_a else monitor_source_gains[self.monitor_a]
		scales['scale_ch2'] = 1.0 if not self.monitor_b else monitor_source_gains[self.monitor_b]

		return scales

_iir_reg_handlers = {
	'mon1_source':	(REG_MONSELECT,		to_reg_unsigned(0,3), from_reg_unsigned(0,3)),
	'mon2_source':	(REG_MONSELECT,		to_reg_unsigned(3,3), from_reg_unsigned(3,3)),

	'input_en1':		(REG_ENABLE,			to_reg_unsigned(0,1), from_reg_unsigned(0,1)),
	'input_en2':		(REG_ENABLE,			to_reg_unsigned(1,1), from_reg_unsigned(1,1)),
	'output_en1':		(REG_ENABLE,			to_reg_unsigned(2,1), from_reg_unsigned(2,1)),
	'output_en2':		(REG_ENABLE,			to_reg_unsigned(3,1), from_reg_unsigned(3,1)),

	'matrixscale_ch1_ch1':		(REG_CH0_CH0GAIN, 	to_reg_signed(0,16), from_reg_signed(0,16)),
	'matrixscale_ch1_ch2':		(REG_CH0_CH1GAIN,	to_reg_signed(0,16), from_reg_signed(0,16)),
	'matrixscale_ch2_ch1':		(REG_CH1_CH0GAIN,	to_reg_signed(0,16), from_reg_signed(0,16)),
	'matrixscale_ch2_ch2':		(REG_CH1_CH1GAIN,	to_reg_signed(0,16), from_reg_signed(0,16)),

	'ch1_sampling_freq':	(REG_SAMPLINGFREQ,		to_reg_unsigned(0, 1), from_reg_unsigned(0, 1)),
	'ch2_sampling_freq':	(REG_SAMPLINGFREQ,		to_reg_unsigned(1, 1), from_reg_unsigned(1, 1)),

	'filter_reset':		(REG_FILT_RESET, 		to_reg_bool(0), from_reg_bool(0)),

	'input_scale1':	(REG_INPUTSCALE_CH0,	to_reg_unsigned(0, 18), from_reg_unsigned(0, 18)),
	'input_scale2':	(REG_INPUTSCALE_CH1,	to_reg_unsigned(0, 18), from_reg_unsigned(0, 18)),

	'output_scale1':	(REG_OUTPUTSCALE_CH0,	to_reg_unsigned(0, 18), from_reg_unsigned(0, 18)),
	'output_scale2':	(REG_OUTPUTSCALE_CH1,	to_reg_unsigned(0, 18), from_reg_unsigned(0, 18)),

	'input_offset1':	(REG_INPUTOFFSET_CH0,	to_reg_signed(0, 14), from_reg_signed(0, 14)),
	'input_offset2':	(REG_INPUTOFFSET_CH1,	to_reg_signed(0, 14), from_reg_signed(0, 14)),

	'output_offset1':	(REG_OUTPUTOFFSET_CH0,	to_reg_signed(0, 17), from_reg_signed(0, 17)),
	'output_offset2':	(REG_OUTPUTOFFSET_CH1,	to_reg_signed(0, 17), from_reg_signed(0, 17))
}