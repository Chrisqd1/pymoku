
import math
import logging
import os

from ._instrument import *
CHN_BUFLEN = 2**13
from . import _frame_instrument
from pymoku._oscilloscope import _CoreOscilloscope
from . import _utils

log = logging.getLogger(__name__)

REG_FIR_DECIMATION_CH0 = 96
REG_FIR_IN_SCALE1 = 98
REG_FIR_IN_OFFSET1 = 100
REG_FIR_OUT_SCALE1 = 102
REG_FIR_OUT_OFFSET1 = 104
REG_FIR_INTERPOLATION_CH0_WDFRATES 	= 106
REG_FIR_INTERPOLATION_CH0_CICRATES 	= 107
REG_FIR_INTERPOLATION_CH0_CTRL 		= 108

REG_FIR_DECIMATION_CH1 = 97
REG_FIR_IN_SCALE2 = 99
REG_FIR_IN_OFFSET2 = 101
REG_FIR_OUT_SCALE2 = 103
REG_FIR_OUT_OFFSET2 = 105
REG_FIR_INTERPOLATION_CH1_WDFRATES 	= 109
REG_FIR_INTERPOLATION_CH1_CICRATES 	= 110
REG_FIR_INTERPOLATION_CH1_CTRL 		= 111

REG_FIR_LINK = 112
REG_FIR_RESET_CH1 = 113
REG_FIR_RESET_CH2 = 114
REG_FIR_MATRIXGAIN_CH1 = 115
REG_FIR_MATRIXGAIN_CH2 = 116
REG_FIR_OUTPUTENABLE = 117
REG_FIR_MONSELECT = 118

_FIR_NUM_BLOCKS = 29
_FIR_BLOCK_SIZE = 511

class FIRFilter(_CoreOscilloscope):
	"""
	.. automethod:: pymoku.instruments.FIRFilter.__init__
	"""

	def __init__(self):
		super(FIRFilter, self).__init__()
		self._register_accessors(_fir_reg_handlers)
		self.id = 10
		self.type = "firfilter"

	@needs_commit
	def set_defaults(self):
		super(FIRFilter, self).set_defaults()
		self.set_offset_gain(1, input_scale = 0, output_scale = 0, input_offset = 0, output_offset = 0, matrix_scalar_ch1=None, matrix_scalar_ch2=None)
		self.set_offset_gain(2, input_scale = 0, output_scale = 0, input_offset = 0, output_offset = 0, matrix_scalar_ch1=None, matrix_scalar_ch2=None)

	@needs_commit
	def set_offset_gain(self, ch, input_scale = 1, output_scale = 1, input_offset = 0, output_offset = 0, matrix_scalar_ch1=None, matrix_scalar_ch2=None):
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
		control_matrix_ch2 = int(round(matrix_scalar_ch2 * adc_calibration * 2**10 / atten))

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

	def set_filter(self, ch, decimation_factor, filter_coefficients=None, on_off = 'on'):	
		"""
		Set FIR filter sample rate and coefficients and toggle channel output on/off. 

		:type ch : int; {1,2}
		:param ch : target channel.

		:type decimation_factor : int; {0,1,2,3,4,5,6,7,8,9,10}
		:param decimation_factor : integer respresenting the binary exponent n in the sample rate calculation formula: Fs = 125 MHz / 2^n.

		:type filter_coefficients : array;
		:param filter_coefficients : array of max 2^n * 29 FIR filter coefficients. The array format can be seen in the class documentation above.
		"""

		_utils.check_parameter_valid('set', ch, [1,2],'filter channel')
		_utils.check_parameter_valid('set', decimation_factor, [0,1,2,3,4,5,6,7,8,9,10],'decimation factor')
		_utils.check_parameter_valid('range', len(filter_coefficients), [0,29*2**decimation_factor],'filter coefficient array length')
		for x in range(0, len(filter_coefficients)):
			_utils.check_parameter_valid('range', filter_coefficients[x], [-1.0,1.0],'normalised coefficient value')

		if ch == 1:
			self.ch1_output = 1 if on_off == 'on' else 0
			self._set_samplerate(1,2**decimation_factor)
			self._write_coeffs(1, filter_coefficients)
		else:
			self.ch2_output = 1 if on_off == 'on' else 0
			self._set_samplerate(2,2**decimation_factor)	
			self._write_coeffs(2, filter_coefficients)

	@needs_commit
	def _set_samplerate(self, ch, decimation_factor = 8):
		self._channel_reset(ch)

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
		if decimation_factor == 1:
			d_outmuxsel = 0 			
			i_muxsel = 0
		elif decimation_factor == 2:
			d_wdfmuxsel = 0
			d_outmuxsel = 1
			i_muxsel = 1
			i_highrate_wdf1 = 0
		elif decimation_factor == 4:
			d_wdfmuxsel = 0
			d_outmuxsel = 2
			i_muxsel = 2
			i_highrate_wdf1 = decimation_factor/2 - 1
			i_highrate_wdf2 = 0
		elif 8 <= decimation_factor <= 64:
			d_wdfmuxsel = 1
			d_outmuxsel = 2
			d_cic1_dec = decimation_factor/4
			d_cic1_bitshift = 12 - math.log(d_cic1_dec**3,2)
			i_muxsel = 3
			i_ratechange_cic1 = decimation_factor/4
			i_interprate_cic1 = 0
			i_bitshift_cic1 = math.log(i_ratechange_cic1**2,2)
			i_highrate_wdf1 = decimation_factor/2 - 1
			i_highrate_wdf2 = decimation_factor/4 - 1
		else: # 128 <= decimation_factor <= 1024
			d_wdfmuxsel = 2
			d_outmuxsel = 2	
			d_cic1_dec = 16
			d_cic1_bitshift = 0
			d_cic2_dec = decimation_factor/64
			d_cic2_bitshift = math.log(d_cic2_dec**3,2)
			i_muxsel = 4
			i_ratechange_cic2 = decimation_factor/64
			i_interprate_cic2 = 0
			i_bitshift_cic2 = math.log(i_ratechange_cic2**2,2)
			i_ratechange_cic1 = 16
			i_bitshift_cic1 = 8
			i_interprate_cic1 = i_ratechange_cic2 - 1
			i_highrate_wdf1 = decimation_factor/2 - 1
			i_highrate_wdf2 = decimation_factor/4 - 1

		if ch == 1:
			self.dec_wdfmuxsel_1 = d_wdfmuxsel
			self.dec_outmuxsel_1 = d_outmuxsel
			self.dec_cic1_dec_1 = d_cic1_dec
			self.dec_cic1_bitshift_1 = d_cic1_bitshift
			self.dec_cic2_dec_1 = d_cic2_dec
			self.dec_cic2_bitshift_1 = d_cic2_bitshift

			self.int_muxsel_1 = i_muxsel
			self.int_highrate_wdf1_1 = i_highrate_wdf1
			self.int_highrate_wdf2_1 = i_highrate_wdf2
			self.int_ratechange_cic1_1 = i_ratechange_cic1
			self.int_ratechange_cic2_1 = i_ratechange_cic2
			self.int_interprate_cic1_1 = i_interprate_cic1
			self.int_interprate_cic2_1 = i_interprate_cic2
			self.int_bitshift_cic1_1 = i_bitshift_cic1
			self.int_bitshift_cic2_1 = i_bitshift_cic2
		else:
			self.dec_wdfmuxsel_2 = d_wdfmuxsel
			self.dec_outmuxsel_2 = d_outmuxsel
			self.dec_cic1_dec_2 = d_cic1_dec
			self.dec_cic1_bitshift_2 = d_cic1_bitshift
			self.dec_cic2_dec_2 = d_cic2_dec
			self.dec_cic2_bitshift_2 = d_cic2_bitshift

			self.int_muxsel_2 = i_muxsel
			self.int_highrate_wdf1_2 = i_highrate_wdf1
			self.int_highrate_wdf2_2 = i_highrate_wdf2
			self.int_ratechange_cic1_2 = i_ratechange_cic1
			self.int_ratechange_cic2_2 = i_ratechange_cic2
			self.int_interprate_cic1_2 = i_interprate_cic1
			self.int_interprate_cic2_2 = i_interprate_cic2
			self.int_bitshift_cic1_2 = i_bitshift_cic1
			self.int_bitshift_cic2_2 = i_bitshift_cic2

	def _channel_reset(self, ch):
		if ch == 1:
			self.reset_ch1 = 1 if self.reset_ch1 == 0 else 0
		else:
			self.reset_ch2 = 1 if self.reset_ch2 == 0 else 0

	def _write_coeffs(self, ch, coeffs):
		coeffs = list(coeffs)
		_utils.check_parameter_valid('set', ch, [1,2],'output channel')
		assert len(coeffs) <= _FIR_NUM_BLOCKS * _FIR_BLOCK_SIZE
		L = int(math.ceil(float(len(coeffs))/_FIR_NUM_BLOCKS))
		blocks = [coeffs[x:x+L] for x in range(0, len(coeffs), L)]
		print L
		blocks += [[]] * (_FIR_NUM_BLOCKS - len(blocks))
		print(blocks)

		print map(len, blocks)
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
			f.write('\x00\x00\x00\x00' * _FIR_BLOCK_SIZE * _FIR_NUM_BLOCKS)

			for i, b in enumerate(blocks):
				b.reverse()
				for j, c in enumerate(b):
					f.seek(offset + (i * (_FIR_BLOCK_SIZE+1) * 4) + (j * 4))
					f.write(struct.pack('<i', round((2.0**24-1) * c)))
				f.seek(offset + (i * (_FIR_BLOCK_SIZE+1) * 4) + (_FIR_BLOCK_SIZE * 4))
				f.write(struct.pack('<I', len(b)))

			f.flush()	

		self._set_mmap_access(True)
		error = self._moku._send_file('j', '.lutdata.dat')
		self._set_mmap_access(False)

_fir_reg_handlers = {
	'input_scale1':			(REG_FIR_IN_SCALE1,		to_reg_unsigned(0, 18), from_reg_unsigned(0, 18)),
	'input_scale2':			(REG_FIR_IN_SCALE2,		to_reg_unsigned(0, 18), from_reg_unsigned(0, 18)),
	'input_offset1':			(REG_FIR_IN_OFFSET1,		to_reg_unsigned(0, 16), from_reg_unsigned(0, 16)),
	'input_offset2':			(REG_FIR_IN_OFFSET2,		to_reg_unsigned(0, 16), from_reg_unsigned(0, 16)),
	'output_scale1':			(REG_FIR_OUT_SCALE1,		to_reg_unsigned(0, 18), from_reg_unsigned(0, 18)),
	'output_scale2':			(REG_FIR_OUT_SCALE2,		to_reg_unsigned(0, 18), from_reg_unsigned(0, 18)),
	'output_offset1':			(REG_FIR_OUT_OFFSET1,		to_reg_unsigned(0, 16), from_reg_unsigned(0, 16)),
	'output_offset2':			(REG_FIR_OUT_OFFSET2,		to_reg_unsigned(0, 16), from_reg_unsigned(0, 16)),
	'link':			(REG_FIR_LINK,		to_reg_bool(0), from_reg_bool(0)),

	'dec_wdfmuxsel_1':	(REG_FIR_DECIMATION_CH0,		to_reg_unsigned(0, 2), from_reg_unsigned(0, 2)),
	'dec_outmuxsel_1':	(REG_FIR_DECIMATION_CH0,		to_reg_unsigned(2, 2), from_reg_unsigned(2, 2)),
	'dec_cic1_bitshift_1':		(REG_FIR_DECIMATION_CH0,		to_reg_unsigned(4, 4), from_reg_unsigned(4, 4)),
	'dec_cic2_bitshift_1':		(REG_FIR_DECIMATION_CH0,		to_reg_unsigned(8, 4), from_reg_unsigned(8, 4)),
	'dec_cic1_dec_1':		(REG_FIR_DECIMATION_CH0,		to_reg_unsigned(12, 5), from_reg_unsigned(12, 5)),
	'dec_cic2_dec_1':		(REG_FIR_DECIMATION_CH0,		to_reg_unsigned(17, 5), from_reg_unsigned(17, 5)),

	'dec_wdfmuxsel_2':	(REG_FIR_DECIMATION_CH1,		to_reg_unsigned(0, 2), from_reg_unsigned(0, 2)),
	'dec_outmuxsel_2':	(REG_FIR_DECIMATION_CH1,		to_reg_unsigned(2, 2), from_reg_unsigned(2, 2)),
	'dec_cic1_bitshift_2':		(REG_FIR_DECIMATION_CH1,		to_reg_unsigned(4, 4), from_reg_unsigned(4, 4)),
	'dec_cic2_bitshift_2':		(REG_FIR_DECIMATION_CH1,		to_reg_unsigned(8, 4), from_reg_unsigned(8, 4)),
	'dec_cic1_dec_2':		(REG_FIR_DECIMATION_CH1,		to_reg_unsigned(12, 5), from_reg_unsigned(12, 5)),
	'dec_cic2_dec_2':		(REG_FIR_DECIMATION_CH1,		to_reg_unsigned(17, 5), from_reg_unsigned(17, 5)),

	'int_highrate_wdf1_1': 	(REG_FIR_INTERPOLATION_CH0_WDFRATES, 	to_reg_unsigned(0,16), from_reg_unsigned(0,16)),
	'int_highrate_wdf2_1': 	(REG_FIR_INTERPOLATION_CH0_WDFRATES, 	to_reg_unsigned(16,16), from_reg_unsigned(16,16)),
	'int_interprate_cic1_1': 	(REG_FIR_INTERPOLATION_CH0_CICRATES, 	to_reg_unsigned(0,16), from_reg_unsigned(0,16)),
	'int_interprate_cic2_1': 	(REG_FIR_INTERPOLATION_CH0_CICRATES, 	to_reg_unsigned(16,16), from_reg_unsigned(16,16)),
	'int_muxsel_1': 			(REG_FIR_INTERPOLATION_CH0_CTRL, 	to_reg_unsigned(0,3), from_reg_unsigned(0,3)),
	'int_ratechange_cic1_1':	(REG_FIR_INTERPOLATION_CH0_CTRL, 	to_reg_unsigned(3,5), from_reg_unsigned(3,5)),
	'int_ratechange_cic2_1':	(REG_FIR_INTERPOLATION_CH0_CTRL, 	to_reg_unsigned(8,5), from_reg_unsigned(8,5)),
	'int_bitshift_cic1_1':	(REG_FIR_INTERPOLATION_CH0_CTRL, 	to_reg_unsigned(13,4), from_reg_unsigned(13,4)),
	'int_bitshift_cic2_1':	(REG_FIR_INTERPOLATION_CH0_CTRL, 	to_reg_unsigned(17,4), from_reg_unsigned(17,4)),

	'int_highrate_wdf1_2': 	(REG_FIR_INTERPOLATION_CH1_WDFRATES, 	to_reg_unsigned(0,16), from_reg_unsigned(0,16)),
	'int_highrate_wdf2_2': 	(REG_FIR_INTERPOLATION_CH1_WDFRATES, 	to_reg_unsigned(16,16), from_reg_unsigned(16,16)),
	'int_interprate_cic1_2': 	(REG_FIR_INTERPOLATION_CH1_CICRATES, 	to_reg_unsigned(0,16), from_reg_unsigned(0,16)),
	'int_interprate_cic2_2': 	(REG_FIR_INTERPOLATION_CH1_CICRATES, 	to_reg_unsigned(16,16), from_reg_unsigned(16,16)),
	'int_muxsel_2': 			(REG_FIR_INTERPOLATION_CH1_CTRL, 	to_reg_unsigned(0,3), from_reg_unsigned(0,3)),
	'int_ratechange_cic1_2':	(REG_FIR_INTERPOLATION_CH1_CTRL, 	to_reg_unsigned(3,5), from_reg_unsigned(3,5)),
	'int_ratechange_cic2_2':	(REG_FIR_INTERPOLATION_CH1_CTRL, 	to_reg_unsigned(8,5), from_reg_unsigned(8,5)),
	'int_bitshift_cic1_2':	(REG_FIR_INTERPOLATION_CH1_CTRL, 	to_reg_unsigned(13,4), from_reg_unsigned(13,4)),
	'int_bitshift_cic2_2':	(REG_FIR_INTERPOLATION_CH1_CTRL, 	to_reg_unsigned(17,4), from_reg_unsigned(17,4)),

	'matrixscale_ch1_ch1': (REG_FIR_MATRIXGAIN_CH1,	to_reg_signed(0,16), from_reg_signed(0,16)),
	'matrixscale_ch1_ch2': (REG_FIR_MATRIXGAIN_CH1,	to_reg_signed(16,16), from_reg_signed(16,16)),
	'matrixscale_ch2_ch1': (REG_FIR_MATRIXGAIN_CH2,	to_reg_signed(0,16), from_reg_signed(0,16)),
	'matrixscale_ch2_ch2': (REG_FIR_MATRIXGAIN_CH2,	to_reg_signed(16,16), from_reg_signed(16,16)),

	'reset_ch1':	(REG_FIR_RESET_CH1, to_reg_unsigned(0,1), from_reg_unsigned(0,1)),
	'reset_ch2':	(REG_FIR_RESET_CH2, to_reg_unsigned(0,1), from_reg_unsigned(0,1)),
	'ch1_output':		(REG_FIR_OUTPUTENABLE,			to_reg_unsigned(0,1), from_reg_unsigned(0,1)),
	'ch2_output':		(REG_FIR_OUTPUTENABLE,			to_reg_unsigned(1,1), from_reg_unsigned(1,1))
}
