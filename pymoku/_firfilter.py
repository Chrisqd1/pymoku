import math
import logging
import os

from ._instrument import *
CHN_BUFLEN = 2**13
from . import _frame_instrument
from pymoku._oscilloscope import _CoreOscilloscope
from . import _utils

log = logging.getLogger(__name__)

REG_FIR_CONTROL = 96

REG_FIR_IN_SCALE1 = 105
REG_FIR_IN_OFFSET1 = 106
REG_FIR_OUT_SCALE1 = 107
REG_FIR_OUT_OFFSET1 = 108
REG_FIR_MATRIXGAIN_CH1 = 109

REG_FIR_IN_SCALE2 = 110
REG_FIR_IN_OFFSET2 = 111
REG_FIR_OUT_SCALE2 = 112
REG_FIR_OUT_OFFSET2 = 113
REG_FIR_MATRIXGAIN_CH2 = 114

_FIR_NUM_BLOCKS = 29
_FIR_BLOCK_SIZE = 511

_ADC_DEFAULT_CALIBRATION = 3750.0								# Bits/V (No attenuation)
_DAC_DEFAULT_CALIBRATION = _ADC_DEFAULT_CALIBRATION * 2.0**3	# Bits/V

class _DecFilter(object):
	REG_DECIMATION = 0
	REG_INTERP_WDFRATES = 1
	REG_INTERP_CICRATES = 2
	REG_INTERP_CTRL = 3

	def __init__(self, instr, regbase):
		self._instr = instr
		self.regbase = regbase

	def set_samplerate(self, factor):
		d_wdfmuxsel = 0
		d_outmuxsel = 0
		d_cic1_dec = 0
		d_cic1_bitshift = 0
		d_cic2_dec = 0
		d_cic2_bitshift = 0
		i_muxsel = 0
		i_ratechange_cic2 = 0
		i_interprate_cic2 = 0
		i_bitshift_cic2 = 0
		i_ratechange_cic1 = 0
		i_bitshift_cic1 = 0
		i_interprate_cic1 = 0
		i_highrate_wdf1 = 0
		i_highrate_wdf2 = 0
		if factor == 1:
			d_outmuxsel = 0
			i_muxsel = 0
		elif factor == 2:
			d_wdfmuxsel = 0
			d_outmuxsel = 1
			i_muxsel = 1
			i_highrate_wdf1 = 0
		elif factor == 4:
			d_wdfmuxsel = 0
			d_outmuxsel = 2
			i_muxsel = 2
			i_highrate_wdf1 = factor/2 - 1
			i_highrate_wdf2 = 0
		elif 8 <= factor <= 64:
			d_wdfmuxsel = 1
			d_outmuxsel = 2
			d_cic1_dec = factor/4
			d_cic1_bitshift = 12 - math.log(d_cic1_dec**3,2)
			i_muxsel = 3
			i_ratechange_cic1 = factor/4
			i_interprate_cic1 = 0
			i_bitshift_cic1 = math.log(i_ratechange_cic1**2,2)
			i_highrate_wdf1 = factor/2 - 1
			i_highrate_wdf2 = factor/4 - 1
		else: # 128 <= factor <= 1024
			d_wdfmuxsel = 2
			d_outmuxsel = 2
			d_cic1_dec = 16
			d_cic1_bitshift = 0
			d_cic2_dec = factor/64
			d_cic2_bitshift = math.log(d_cic2_dec**3,2)
			i_muxsel = 4
			i_ratechange_cic2 = factor/64
			i_interprate_cic2 = 0
			i_bitshift_cic2 = math.log(i_ratechange_cic2**2,2)
			i_ratechange_cic1 = 16
			i_bitshift_cic1 = 8
			i_interprate_cic1 = i_ratechange_cic2 - 1
			i_highrate_wdf1 = factor/2 - 1
			i_highrate_wdf2 = factor/4 - 1

		self._instr._accessor_set(self.regbase + self.REG_DECIMATION, to_reg_unsigned(0, 2), d_wdfmuxsel)
		self._instr._accessor_set(self.regbase + self.REG_DECIMATION, to_reg_unsigned(2, 2), d_outmuxsel)
		self._instr._accessor_set(self.regbase + self.REG_DECIMATION, to_reg_unsigned(4, 4), d_cic1_bitshift)
		self._instr._accessor_set(self.regbase + self.REG_DECIMATION, to_reg_unsigned(8, 4), d_cic2_bitshift)
		self._instr._accessor_set(self.regbase + self.REG_DECIMATION, to_reg_unsigned(12, 5), d_cic1_dec)
		self._instr._accessor_set(self.regbase + self.REG_DECIMATION, to_reg_unsigned(17, 5), d_cic2_dec)

		self._instr._accessor_set(self.regbase + self.REG_INTERP_CTRL, to_reg_unsigned(0, 3), i_muxsel)
		self._instr._accessor_set(self.regbase + self.REG_INTERP_WDFRATES, to_reg_unsigned(0, 16), i_highrate_wdf1)
		self._instr._accessor_set(self.regbase + self.REG_INTERP_WDFRATES, to_reg_unsigned(16, 16), i_highrate_wdf2)
		self._instr._accessor_set(self.regbase + self.REG_INTERP_CTRL, to_reg_unsigned(3, 5), i_ratechange_cic1)
		self._instr._accessor_set(self.regbase + self.REG_INTERP_CTRL, to_reg_unsigned(8, 5), i_ratechange_cic2)
		self._instr._accessor_set(self.regbase + self.REG_INTERP_CICRATES, to_reg_unsigned(0, 16), i_interprate_cic1)
		self._instr._accessor_set(self.regbase + self.REG_INTERP_CICRATES, to_reg_unsigned(16, 16), i_interprate_cic2)
		self._instr._accessor_set(self.regbase + self.REG_INTERP_CTRL, to_reg_unsigned(13, 4), i_bitshift_cic1)
		self._instr._accessor_set(self.regbase + self.REG_INTERP_CTRL, to_reg_unsigned(17, 4), i_bitshift_cic2)

class FIRFilter(_CoreOscilloscope):
	""" Finite Impulse Response (FIR) Filter instrument object.

	To run a new FIRFilter instrument, this should be instantiated and deployed via a connected
	:any:`Moku` object using :any:`deploy_instrument`. Alternatively, a pre-configured instrument object
	can be obtained by discovering an already running FIRFilter instrument on a Moku:Lab device via
	:any:`deploy_or_connect`.

	.. automethod:: pymoku.instruments.FIRFilter.__init__

	.. attribute:: type
		:annotation: = "firfilter"

		Name of this instrument.
	"""
	def __init__(self):
		super(FIRFilter, self).__init__()
		self._register_accessors(_fir_reg_handlers)
		self.id = 10
		self.type = "firfilter"

		self._decfilter1 = _DecFilter(self, 97)
		self._decfilter2 = _DecFilter(self, 101)

	@needs_commit
	def set_defaults(self):
		super(FIRFilter, self).set_defaults()
		self.set_gains_offsets(1)
		self.set_gains_offsets(2)

		# TODO: Set these registers in a monitor function instead
		self.mon1_source = 1
		self.mon2_source = 4

	@needs_commit
	def set_control_matrix(self, ch, scale_in1, scale_in2):
		"""
		Configure the input control matrix specifying the input signal mixing for the specified filter channel.

		Input mixing allows a filter channel to act on a linear combination of the two input signals.

		:type ch: int, {1,2}
		:param ch: target filter channel

		:type scale_in1: float, [-20,20]
		:param scale_in1: linear scale factor of input 1 signal added to target filter channel input

		:type scale_in2: float, [-20,20] 
		:param scale_in2: linear scale factor of input 2 signal added to target filter channel input
		"""
		_utils.check_parameter_valid('set', ch, [1, 2], 'filter channel')
		_utils.check_parameter_valid('range', scale_in1, [-20, 20], 'control matrix scale (ch1)', 'linear scalar')
		_utils.check_parameter_valid('range', scale_in2, [-20, 20], 'control matrix scale (ch2)', 'linear scalar')

		if ch == 1:
			self.matrixscale_ch1_ch1 = scale_in1
			self.matrixscale_ch1_ch2 = scale_in2
		else:
			self.matrixscale_ch2_ch1 = scale_in1
			self.matrixscale_ch2_ch2 = scale_in2

	@needs_commit
	def set_gains_offsets(self, ch, input_gain=1.0, output_gain=1.0, input_offset=0, output_offset=0):
		"""
		Configure pre- and post-filter scales and offsets for a given filter channel.

		.. note::
			The overall output gain of the instrument is the product of the gain of the filter, set by the filter coefficients,
			and the input/output stage gain set here.

		:type ch: int, {1,2}
		:param ch: target filter channel

		:type input_gain, output_gain: float, linear scalar, [-100,100]
		:param input_gain, output_gain: channel scalars before and after the FIR filter

		:type input_offset: float, volts, [-0.5,0.5]
		:param input_offset: channel offset before the FIR filter

		:type output_offset: float, volts, [-1.0,1.0]
		:param output_offset: channel offset after the FIR filter
		"""
		_utils.check_parameter_valid('set', ch, [1, 2], 'filter channel')
		_utils.check_parameter_valid('range', input_gain, [-100, 100], 'input gain', 'linear scalar')
		_utils.check_parameter_valid('range', output_gain, [-100, 100], 'output gain', 'linear scalar')
		_utils.check_parameter_valid('range', input_offset, [-0.5, 0.5], 'input offset', 'Volts')
		_utils.check_parameter_valid('range', output_offset, [-1.0, 1.0], 'output offset', 'Volts')

		if ch == 1:
			self.input_scale1 = input_gain
			self.output_scale1 = output_gain
			self.input_offset1 = input_offset
			self.output_offset1 = output_offset
		else:
			self.input_scale2 = input_gain
			self.output_scale2 = output_gain
			self.input_offset2 = input_offset
			self.output_offset2 = output_offset

		# Reset the channel's filtering loop for new settings to take effect immediately
		self._channel_reset(ch)

	@needs_commit
	def set_filter(self, ch, decimation_factor, filter_coefficients):
		"""
		Set FIR filter sample rate and kernel coefficients. This will enable the specified channel output.
 
		:type ch : int; {1,2}
		:param ch : target channel.

		:type decimation_factor : int; [0,10]
		:param decimation_factor : the binary exponent *n* specifying the sample rate: Fs = 125 MHz / 2^n.

		:type filter_coefficients : float array;
		:param filter_coefficients : array of max 2^n * 29 FIR filter coefficients. The array format can be seen in the class documentation above.
		"""
		# TODO: Document the quantization of array coefficients incurred
		# TODO: The array format is NOT in the class documentation above...?



		_utils.check_parameter_valid('set', ch, [1, 2],'filter channel')
		_utils.check_parameter_valid('set', enable, [True, False],'channel output enable')
		_utils.check_parameter_valid('set', link, [True, False],'channel link')
		_utils.check_parameter_valid('set', decimation_factor, range(11), 'decimation factor')
		_utils.check_parameter_valid('range', len(filter_coefficients), [0, _FIR_NUM_BLOCKS * 2**decimation_factor], 'filter coefficient array length')
		for x in range(0, len(filter_coefficients)):
			_utils.check_parameter_valid('range', filter_coefficients[x], [-1.0, 1.0],'normalised coefficient value')

		self._set_output_link(ch, enable, link)
		self._set_samplerate(ch, 2**decimation_factor)
		self._write_coeffs(ch, filter_coefficients)

	@needs_commit
	def disable_output(self, ch):
		"""
		Disables the output of the specified FIR filter channel.

		:type ch : int; {1,2}
		:param ch : target channel
		"""
		if ch == 1:
			self.output_en1 = False
		else:
			self.output_en2 = False

	def _set_samplerate(self, ch, factor):
		if ch == 1:
			self._decfilter1.set_samplerate(factor)
		else:
			self._decfilter2.set_samplerate(factor)
		self._channel_reset(ch)

	def _channel_reset(self, ch):
		if ch == 1:
			self.reset_ch1 = True
		else:
			self.reset_ch2 = True

	def _write_coeffs(self, ch, coeffs):
		# TODO: Rewrite this to NOT use a temporary file
		coeffs = list(coeffs)
		_utils.check_parameter_valid('set', ch, [1,2], 'output channel')
		assert len(coeffs) <= _FIR_NUM_BLOCKS * _FIR_BLOCK_SIZE
		L = int(math.ceil(float(len(coeffs))/_FIR_NUM_BLOCKS))
		blocks = [coeffs[x:x+L] for x in range(0, len(coeffs), L)]
		blocks += [[]] * (_FIR_NUM_BLOCKS - len(blocks))

		if not os.path.exists('.lutdata.dat'):
			open('.lutdata.dat', 'w').close()

		with open('.lutdata.dat', 'r+b') as f:
			#first check and make the file the right size
			f.seek(0, os.SEEK_END)
			size = f.tell()
			f.write('\0'.encode(encoding='UTF-8') * (2**16 * 4  - size))
			f.flush()

			#Leave the previous data file so we just rewite the new part,
			#as we have to upload both channels at once.
			if ch == 1:
				offset = 0
			else:
				offset = 2**15 * 4

			#clear the current contents
			f.seek(offset)
			f.write(b'\x00\x00\x00\x00' * (_FIR_BLOCK_SIZE+1) * _FIR_NUM_BLOCKS)

			for i, b in enumerate(blocks):
				b.reverse()
				f.seek(offset + (i * (_FIR_BLOCK_SIZE+1) * 4))
				f.write(struct.pack('<I', len(b)))
				for j, c in enumerate(b):
					f.seek(offset + (i * (_FIR_BLOCK_SIZE+1) * 4) + ((j+1) * 4))
					f.write(struct.pack('<i', int(round((2.0**24-1) * c))))

			f.flush()

		self._set_mmap_access(True)
		error = self._moku._send_file('j', '.lutdata.dat')
		self._set_mmap_access(False)

_fir_reg_handlers = {
	'reset_ch1':			(REG_FIR_CONTROL,			to_reg_bool(0), from_reg_bool(0)),
	'reset_ch2':			(REG_FIR_CONTROL,			to_reg_bool(1), from_reg_bool(1)),
	'output_en1':			(REG_FIR_CONTROL,			to_reg_bool(2), from_reg_bool(2)),
	'output_en2':			(REG_FIR_CONTROL,			to_reg_bool(3), from_reg_bool(3)),
	'link':					(REG_FIR_CONTROL,			to_reg_bool(4), from_reg_bool(4)),
	'input_en1':			(REG_FIR_CONTROL,			to_reg_bool(5), from_reg_bool(5)),
	'input_en2':			(REG_FIR_CONTROL,			to_reg_bool(6), from_reg_bool(6)),
	'mon1_source':			(REG_FIR_CONTROL,			to_reg_unsigned(8, 3), from_reg_unsigned(8, 3)),
	'mon2_source':			(REG_FIR_CONTROL,			to_reg_unsigned(12, 3), from_reg_unsigned(12, 3)),
	'mon1_gain':			(REG_FIR_CONTROL,			to_reg_bool(11), from_reg_bool(11)),
	'mon2_gain':			(REG_FIR_CONTROL,			to_reg_bool(15), from_reg_bool(15)),

	'input_scale1':			(REG_FIR_IN_SCALE1,			to_reg_signed(0, 18, lambda obj, x: x * 2.0**9), 
														from_reg_signed(0, 18, lambda obj, x : x / (2.0 **9))),
	'input_scale2':			(REG_FIR_IN_SCALE2,			to_reg_signed(0, 18, lambda obj, x: x * 2.0**9), 
														from_reg_signed(0, 18, lambda obj, x : x / (2.0 **9))),

	'input_offset1':		(REG_FIR_IN_OFFSET1,		to_reg_signed(0, 32, lambda obj, x: x * 2.0**12 * 2.0 * (_ADC_DEFAULT_CALIBRATION/(10.0 if obj.get_frontend(1)[1] else 1.0) * obj._adc_gains()[0])), 
														from_reg_signed(0, 32, lambda obj, x: x / (_ADC_DEFAULT_CALIBRATION/(10.0 if obj.get_frontend(1)[1] else 1.0) * obj._adc_gains()[0]) / 2.0**12 / 2.0)),

	'input_offset2':		(REG_FIR_IN_OFFSET2,		to_reg_signed(0, 32, lambda obj, x: x * 2.0**12 * 2.0 * (_ADC_DEFAULT_CALIBRATION/(10.0 if obj.get_frontend(2)[1] else 1.0) * obj._adc_gains()[1])), 
														from_reg_signed(0, 32, lambda obj, x: x / (_ADC_DEFAULT_CALIBRATION/(10.0 if obj.get_frontend(2)[1] else 1.0) * obj._adc_gains()[1]) / 2.0**12 / 2.0)),

	'output_scale1':		(REG_FIR_OUT_SCALE1,		to_reg_signed(0, 18, lambda obj, x: int(round(x * 2.0**10 / (_DAC_DEFAULT_CALIBRATION * obj._dac_gains()[0]) / 2.0**3))), 
														from_reg_signed(0, 18, lambda obj, x: x * 2.0**3 * (_DAC_DEFAULT_CALIBRATION * obj._dac_gains()[0]) / 2.0**10)),

	'output_scale2':		(REG_FIR_OUT_SCALE2,		to_reg_signed(0, 18, lambda obj, x: int(round(x * 2.0**10 / (_DAC_DEFAULT_CALIBRATION * obj._dac_gains()[1]) / 2.0**3))), 
														from_reg_signed(0, 18, lambda obj, x: x * 2.0**3 * (_DAC_DEFAULT_CALIBRATION * obj._dac_gains()[1]) / 2.0**10)),

	'output_offset1':		(REG_FIR_OUT_OFFSET1,		to_reg_signed(0, 32, lambda obj, x: int(round(x * 2.0**15 * (_DAC_DEFAULT_CALIBRATION * obj._dac_gains()[1]) / 2.0**3))), 
														from_reg_signed(0, 32, lambda obj, x: x / (_DAC_DEFAULT_CALIBRATION*obj._dac_gains()[1])/ 2.0**15 / 2.0**3)),

	'output_offset2':		(REG_FIR_OUT_OFFSET2,		to_reg_signed(0, 32, lambda obj, x: int(round(x * 2.0**15 * (_DAC_DEFAULT_CALIBRATION * obj._dac_gains()[1]) / 2.0**3))), 
														from_reg_signed(0, 32, lambda obj, x: x / (_DAC_DEFAULT_CALIBRATION*obj._dac_gains()[1])/ 2.0**15 / 2.0**3)),

	'matrixscale_ch1_ch1':	(REG_FIR_MATRIXGAIN_CH1,	to_reg_signed(0, 16, 
															xform=lambda obj, x: int(round(x * (_ADC_DEFAULT_CALIBRATION / (10.0 if obj.get_frontend(1)[1] else 1.0)) * obj._adc_gains()[0] * 2.0**10))), 
														from_reg_signed(0, 16,
															xform=lambda obj, x: x * ((10.0 if obj.get_frontend(1)[1] else 1.0) / _ADC_DEFAULT_CALIBRATION) / obj._adc_gains()[0] / 2.0**10)),
	'matrixscale_ch1_ch2':	(REG_FIR_MATRIXGAIN_CH1,	to_reg_signed(16, 16, 
															xform=lambda obj, x: int(round(x * (_ADC_DEFAULT_CALIBRATION / (10.0 if obj.get_frontend(2)[1] else 1.0)) * obj._adc_gains()[1] * 2.0**10))), 
														from_reg_signed(16, 16,
															xform=lambda obj, x: x * ((10.0 if obj.get_frontend(2)[1] else 1.0) / _ADC_DEFAULT_CALIBRATION) / obj._adc_gains()[1] / 2.0**10)),
	'matrixscale_ch2_ch1':	(REG_FIR_MATRIXGAIN_CH2,	to_reg_signed(0, 16, 
															xform=lambda obj, x: int(round(x * (_ADC_DEFAULT_CALIBRATION / (10.0 if obj.get_frontend(2)[1] else 1.0)) * obj._adc_gains()[1] * 2.0**10))), 
														from_reg_signed(0, 16,
															xform=lambda obj, x: x * ((10.0 if obj.get_frontend(2)[1] else 1.0) / _ADC_DEFAULT_CALIBRATION) / obj._adc_gains()[1] / 2.0**10)),
	'matrixscale_ch2_ch2':	(REG_FIR_MATRIXGAIN_CH2,	to_reg_signed(16, 16, 
															xform=lambda obj, x: int(round(x * (_ADC_DEFAULT_CALIBRATION / (10.0 if obj.get_frontend(1)[1] else 1.0)) * obj._adc_gains()[0] * 2.0**10))), 
														from_reg_signed(16, 16,
															xform=lambda obj, x: x * ((10.0 if obj.get_frontend(1)[1] else 1.0) / _ADC_DEFAULT_CALIBRATION) / obj._adc_gains()[0] / 2.0**10))
}
