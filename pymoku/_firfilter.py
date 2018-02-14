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
	"""
	.. automethod:: pymoku.instruments.FIRFilter.__init__
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
		self.set_offset_gain(1)
		self.set_offset_gain(2)
		self.mon1_source = 1
		self.mon2_source = 4

	@needs_commit
	def set_offset_gain(self, ch, input_scale=1.0, output_scale=1.0, input_offset=0, output_offset=0, matrix_scalar_ch1=None, matrix_scalar_ch2=None):
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

		:type input_offset : int, Volts, [-0.5,0.5]
		:param input_offset, output_offset : channel offsets before and after the IIR filter

		:type output_offset : int, Volts, [-1.0,1.0]
		:param input_offset, output_offset : channel offsets before and after the IIR filter

		:type matrix_scalar_ch1 : int, linear scalar, [0,20]
		:param matrix_scalar_ch1 : scalar controlling proportion of signal coming from channel 1 that is added to the current filter channel

		:type matrix_scalar_ch2 : int, linear scalar, [0,20]
		:param matrix_scalar_ch2 : scalar controlling proportion of signal coming from channel 2 that is added to the current filter channel
		"""
		_utils.check_parameter_valid('set', ch, [1,2],'filter channel')
		_utils.check_parameter_valid('range', input_scale, [0,100],'input scale','linear scalar')
		_utils.check_parameter_valid('range', output_scale, [0,100],'output scale','linear scalar')
		_utils.check_parameter_valid('range', input_offset, [-0.5,0.5],'input offset','Volts')
		_utils.check_parameter_valid('range', output_offset, [-1.0,1.0],'output offset','Volts')
		_utils.check_parameter_valid('range', matrix_scalar_ch1, [-20,20],'matrix ch1 scalar','linear scalar',allow_none=True)
		_utils.check_parameter_valid('range', matrix_scalar_ch2, [-20,20],'matrix ch2 scalar','linear scalar',allow_none=True)

		# Get calibration coefficients
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

		control_matrix_ch1 = int(round(matrix_scalar_ch1 * 3750.0 * adc_calibration * 2**10 / atten)) #scalar in units, default reference calibration, current calibration, normalised hdl 1.0, front/end attenuation
		control_matrix_ch2 = int(round(matrix_scalar_ch2 * 3750.0 * adc_calibration * 2**10 / atten))

		## Calculate input/output scale values
		input_scale_bits = int(round(input_scale * 0x0200)) # not 0100 to account for strange extra div/2 in ScaleOffset. ADC calibration added in control matrix scalar
		output_scale_bits = int(round(output_scale * 0x0400 / 30000 / dac_calibration)) # not 0100 to account for ScaleOffset div/2 and to scale ADC>DAC (other *2 comes from +/- 1V range on ADCs vs +/- 2 V range on DACs) Don't know wehre /3750/8 comes from

		## Calculate input/output offset values
		input_offset_bits = int(round(input_offset * 2**12 * 3750.0 * adc_calibration / 0.5)) #is 2**12 ok, does it need to be 2**12-1? Will addition of scalar make it not saturate? Not sure why / 0.5 is needed
		output_offset_bits = int(round(output_offset * 2**15 / 30000.0 / dac_calibration)) #same as above. /0.5 not needed?

		self._channel_reset(ch)

		if ch == 1:
			self.input_scale1 = input_scale_bits
			self.output_scale1 = output_scale_bits
			self.input_offset1 = input_offset_bits
			self.output_offset1 = output_offset_bits
			self.matrixscale_ch1_ch1 = control_matrix_ch1
			self.matrixscale_ch1_ch2 = control_matrix_ch2
		else:
			self.input_scale2 = input_scale_bits
			self.output_scale2 = output_scale_bits
			self.input_offset2 = input_offset_bits
			self.output_offset2 = output_offset_bits
			self.matrixscale_ch2_ch1 = control_matrix_ch1
			self.matrixscale_ch2_ch2 = control_matrix_ch2

	def set_filter(self, ch, decimation_factor, filter_coefficients, enable=True, link=False):
		"""
		Set FIR filter sample rate and coefficients and toggle channel output on/off.

		:type ch : int; {1,2}
		:param ch : target channel.

		:type decimation_factor : int; {0,1,2,3,4,5,6,7,8,9,10}
		:param decimation_factor : integer respresenting the binary exponent n in the sample rate calculation formula: Fs = 125 MHz / 2^n.

		:type filter_coefficients : array;
		:param filter_coefficients : array of max 2^n * 29 FIR filter coefficients. The array format can be seen in the class documentation above.
		"""

		_utils.check_parameter_valid('set', ch, [1, 2],'filter channel')
		_utils.check_parameter_valid('set', enable, [True, False],'channel output enable')
		_utils.check_parameter_valid('set', link, [True, False],'channel link')
		_utils.check_parameter_valid('set', decimation_factor, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 'decimation factor')
		_utils.check_parameter_valid('range', len(filter_coefficients), [0, _FIR_NUM_BLOCKS * 2**decimation_factor], 'filter coefficient array length')
		for x in range(0, len(filter_coefficients)):
			_utils.check_parameter_valid('range', filter_coefficients[x], [-1.0, 1.0],'normalised coefficient value')

		self._set_output_link(ch, enable, link)
		self._set_samplerate(ch, 2**decimation_factor)
		self._write_coeffs(ch, filter_coefficients)

	@needs_commit
	def _set_samplerate(self, ch, factor):
		if ch == 1:
			self._decfilter1.set_samplerate(factor)
		else:
			self._decfilter2.set_samplerate(factor)
		self._channel_reset(ch)

	@needs_commit
	def _set_output_link(self, ch, enable, link):
		self.link = link
		if ch == 1:
			self.ch1_input = enable
			self.ch1_output = enable
		else
			self.ch2_input = enable
			self.ch2_output = enable

	def _channel_reset(self, ch):
		if ch == 1:
			self.reset_ch1 = 1 if self.reset_ch1 == 0 else 0
		else:
			self.reset_ch2 = 1 if self.reset_ch2 == 0 else 0

	def _write_coeffs(self, ch, coeffs):
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
			f.write('\x00\x00\x00\x00' * (_FIR_BLOCK_SIZE+1) * _FIR_NUM_BLOCKS)

			for i, b in enumerate(blocks):
				b.reverse()
				f.seek(offset + (i * (_FIR_BLOCK_SIZE+1) * 4))
				f.write(struct.pack('<I', len(b)))
				for j, c in enumerate(b):
					f.seek(offset + (i * (_FIR_BLOCK_SIZE+1) * 4) + ((j+1) * 4))
					f.write(struct.pack('<i', round((2.0**24-1) * c)))

			f.flush()

		self._set_mmap_access(True)
		error = self._moku._send_file('j', '.lutdata.dat')
		self._set_mmap_access(False)

_fir_reg_handlers = {
	'reset_ch1':			(REG_FIR_CONTROL,			to_reg_bool(0), from_reg_bool(0)),
	'reset_ch2':			(REG_FIR_CONTROL,			to_reg_bool(1), from_reg_bool(1)),
	'ch1_output':			(REG_FIR_CONTROL,			to_reg_bool(2), from_reg_bool(2)),
	'ch2_output':			(REG_FIR_CONTROL,			to_reg_bool(3), from_reg_bool(3)),
	'link':					(REG_FIR_CONTROL,			to_reg_bool(4), from_reg_bool(4)),
	'ch1_input':			(REG_FIR_CONTROL,			to_reg_bool(5), from_reg_bool(5)),
	'ch2_input':			(REG_FIR_CONTROL,			to_reg_bool(6), from_reg_bool(6)),
	'mon1_source':			(REG_FIR_CONTROL,			to_reg_unsigned(8, 3), from_reg_unsigned(8, 3)),
	'mon2_source':			(REG_FIR_CONTROL,			to_reg_unsigned(12, 3), from_reg_unsigned(12, 3)),
	'mon1_gain':			(REG_FIR_CONTROL,			to_reg_bool(11), from_reg_bool(11)),
	'mon2_gain':			(REG_FIR_CONTROL,			to_reg_bool(15), from_reg_bool(15)),

	'input_scale1':			(REG_FIR_IN_SCALE1,			to_reg_signed(0, 18), from_reg_signed(0, 18)),
	'input_scale2':			(REG_FIR_IN_SCALE2,			to_reg_signed(0, 18), from_reg_signed(0, 18)),
	'input_offset1':		(REG_FIR_IN_OFFSET1,		to_reg_signed(0, 32), from_reg_signed(0, 32)),
	'input_offset2':		(REG_FIR_IN_OFFSET2,		to_reg_signed(0, 32), from_reg_signed(0, 32)),
	'output_scale1':		(REG_FIR_OUT_SCALE1,		to_reg_signed(0, 18), from_reg_signed(0, 18)),
	'output_scale2':		(REG_FIR_OUT_SCALE2,		to_reg_signed(0, 18), from_reg_signed(0, 18)),
	'output_offset1':		(REG_FIR_OUT_OFFSET1,		to_reg_signed(0, 32), from_reg_signed(0, 32)),
	'output_offset2':		(REG_FIR_OUT_OFFSET2,		to_reg_signed(0, 32), from_reg_signed(0, 32)),

	'matrixscale_ch1_ch1':	(REG_FIR_MATRIXGAIN_CH1,	to_reg_signed(0, 16), from_reg_signed(0, 16)),
	'matrixscale_ch1_ch2':	(REG_FIR_MATRIXGAIN_CH1,	to_reg_signed(16, 16), from_reg_signed(16, 16)),
	'matrixscale_ch2_ch1':	(REG_FIR_MATRIXGAIN_CH2,	to_reg_signed(0, 16), from_reg_signed(0, 16)),
	'matrixscale_ch2_ch2':	(REG_FIR_MATRIXGAIN_CH2,	to_reg_signed(16, 16), from_reg_signed(16, 16))
}
