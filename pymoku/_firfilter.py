
import math
import logging
import os

from ._instrument import *
CHN_BUFLEN = 2**13
from . import _frame_instrument
from pymoku._oscilloscope import _CoreOscilloscope
from . import _utils

log = logging.getLogger(__name__)

#REG_FIR_DECIMATION1 = 96
#REG_FIR_DECIMATION2 = 97
REG_FIR_IN_SCALE1 = 98
REG_FIR_IN_SCALE2 = 99
REG_FIR_IN_OFFSET1 = 100
REG_FIR_IN_OFFSET2 = 101
REG_FIR_OUT_SCALE1 = 102
REG_FIR_OUT_SCALE2 = 103
REG_FIR_OUT_OFFSET1 = 104
REG_FIR_OUT_OFFSET2 = 105
REG_FIR_UPSAMPLING1 = 106
REG_FIR_UPSAMPLING2 = 107
REG_FIR_LINK = 108

REG_FIR_INTERPOLATION_CH0_WDFRATES 	= 109
REG_FIR_INTERPOLATION_CH0_CICRATES 	= 110
REG_FIR_INTERPOLATION_CH0_CTRL 		= 111

REG_FIR_INTERPOLATION_CH1_WDFRATES 	= 112
REG_FIR_INTERPOLATION_CH1_CICRATES 	= 113
REG_FIR_INTERPOLATION_CH1_CTRL 		= 114

REG_FIR_DECIMATION_CH0		= 124
REG_FIR_DECIMATION_CH1		= 125

_FIR_NUM_BLOCKS = 44
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
		self.input_scale1 = 0x0100 #multiplication by x0100 is a unity multiplication
		self.input_offset1 = 0x0000
		self.input_scale2 = 0x0040
		self.input_offset2 = 0x0000
		self.output_scale1 = 0x0080
		self.output_offset1 = 0x0000
		self.output_scale2 = 0x0020
		self.output_offset2 = 0x0000

		self.dec_wdfmuxsel = 1
		self.dec_outmuxsel = 2
		self.dec_cic1_dec = 4
		self.dec_cic1_bitshift = 6
		self.dec_cic2_dec = 2
		self.dec_cic2_bitshift = 9
		self.temp1 = 0
		self.temp2 = 0

		self.int_muxsel = 3
		self.int_highrate_wdf1 = 7
		self.int_highrate_wdf2 = 3
		self.int_ratechange_cic1 = 4
		self.int_ratechange_cic2 = 1
		self.int_interprate_cic1 = 0
		self.int_interprate_cic2 = 0
		self.int_bitshift_cic1 = 4
		self.int_bitshift_cic2 = 2

	@needs_commit
	def set_offset_gain(self, ch, input_scale = 1, output_scale = 1, input_offset = 0, output_offset = 0):
		if ch == 1:
			self.input_scale1 = input_scale * 0x0100
			self.output_scale1 = output_scale * 0x0100
			self.input_offset1 = input_offset
			self.output_offset1 = output_offset
		else:
			self.input_scale2 = input_scale * 0x0100
			self.output_scale2 = output_scale * 0x0100
			self.input_offset2 = input_offset
			self.output_offset2 = output_offset

	@needs_commit
	def set_samplerate(self, ch, decimation_factor = 8):
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


	def write_coeffs(self, ch, coeffs):
		coeffs = list(coeffs)
		_utils.check_parameter_valid('set', ch, [1,2],'output channel')
		assert len(coeffs) <= _FIR_NUM_BLOCKS * _FIR_BLOCK_SIZE
		L = int(math.ceil(float(len(coeffs))/_FIR_NUM_BLOCKS))
		blocks = [coeffs[x:x+L] for x in range(0, len(coeffs), L)]
		print L
		blocks += [[]] * (_FIR_NUM_BLOCKS - len(blocks))

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
					f.write(struct.pack('<i', round((2.0**17-1) * c)))
				f.seek(offset + (i * (_FIR_BLOCK_SIZE+1) * 4) + (_FIR_BLOCK_SIZE * 4))
				f.write(struct.pack('<I', len(b)))

			f.flush()

		self._set_mmap_access(True)
		error = self._moku._send_file('j', '.lutdata.dat')
		self._set_mmap_access(False)

_fir_reg_handlers = {
	'decimation1':			(REG_FIR_DECIMATION1,		to_reg_unsigned(0, 32), from_reg_unsigned(0, 32)),
	'decimation2':			(REG_FIR_DECIMATION2,		to_reg_unsigned(0, 32), from_reg_unsigned(0, 32)),
	'input_scale1':			(REG_FIR_IN_SCALE1,		to_reg_unsigned(0, 18), from_reg_unsigned(0, 18)),
	'input_scale2':			(REG_FIR_IN_SCALE2,		to_reg_unsigned(0, 18), from_reg_unsigned(0, 18)),
	'input_offset1':			(REG_FIR_IN_OFFSET1,		to_reg_unsigned(0, 16), from_reg_unsigned(0, 16)),
	'input_offset2':			(REG_FIR_IN_OFFSET2,		to_reg_unsigned(0, 16), from_reg_unsigned(0, 16)),
	'output_scale1':			(REG_FIR_OUT_SCALE1,		to_reg_unsigned(0, 18), from_reg_unsigned(0, 18)),
	'output_scale2':			(REG_FIR_OUT_SCALE2,		to_reg_unsigned(0, 18), from_reg_unsigned(0, 18)),
	'output_offset1':			(REG_FIR_OUT_OFFSET1,		to_reg_unsigned(0, 16), from_reg_unsigned(0, 16)),
	'output_offset2':			(REG_FIR_OUT_OFFSET2,		to_reg_unsigned(0, 16), from_reg_unsigned(0, 16)),
	'upsampling1':			(REG_FIR_UPSAMPLING1,		to_reg_unsigned(0, 14), from_reg_unsigned(0, 14)),
	'upsampling2':			(REG_FIR_UPSAMPLING2,		to_reg_unsigned(0, 14), from_reg_unsigned(0, 14)),
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
	'int_bitshift_cic2_2':	(REG_FIR_INTERPOLATION_CH1_CTRL, 	to_reg_unsigned(17,4), from_reg_unsigned(17,4))
}
