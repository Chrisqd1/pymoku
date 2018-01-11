import math
import logging
import os

from ._instrument import *
CHN_BUFLEN = 2**13
from . import _frame_instrument
from pymoku._oscilloscope import _CoreOscilloscope
from . import _utils

log = logging.getLogger(__name__)

REG_FIR_DECIMATION1 = 96
REG_FIR_DECIMATION2 = 97
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
		self.input_scale1 = 0x0040
		self.input_offset1 = 0x0000
		self.input_scale2 = 0x0040
		self.input_offset2 = 0x0000
		self.output_scale1 = 0x0020
		self.output_offset1 = 0x0000
		self.output_scale2 = 0x0020
		self.output_offset2 = 0x0000

	def write_coeffs(self, ch, coeffs):
		coeffs = list(coeffs)
		_utils.check_parameter_valid('set', ch, [1,2],'output channel')
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
			f.write('\x00\x00\x00\x00' * _FIR_BLOCK_SIZE * _FIR_NUM_BLOCKS)

			for i, b in enumerate(blocks):
				b.reverse()
				for j, c in enumerate(b):
					f.seek(offset + (i * (_FIR_BLOCK_SIZE+1) * 4) + (j * 4))
					f.write(struct.pack('<i', math.ceil((2.0**24-1) * c)))
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
}
