
import math
import logging
import re

from ._instrument import *
CHN_BUFLEN = 2**13
from . import _frame_instrument
from . import _siggen
from . import _oscilloscope
import _utils

log = logging.getLogger(__name__)

REG_MMAP_ACCESS = 62 #TODO this should go somewhere more instrument generic

REG_ARB_SETTINGS = 96
REG_ARB_PHASE_STEP1_L = 97
REG_ARB_PHASE_STEP1_H = 98
REG_ARB_PHASE_OFFSET1_L = 101
REG_ARB_PHASE_OFFSET1_H = 102
REG_ARB_AMPLITUDE1 = 105
REG_ARB_PHASE_MOD1_L = 107
REG_ARB_PHASE_MOD1_H = 108
REG_ARB_DEAD_VALUE1 = 111
REG_ARB_LUT_LENGTH1 = 113
REG_ARB_OFFSET1 = 115

REG_ARB_PHASE_STEP2_L = 99
REG_ARB_PHASE_STEP2_H = 100
REG_ARB_PHASE_OFFSET2_L = 103
REG_ARB_PHASE_OFFSET2_H = 104
REG_ARB_AMPLITUDE2 = 106
REG_ARB_PHASE_MOD2_L = 109
REG_ARB_PHASE_MOD2_H = 110
REG_ARB_DEAD_VALUE2 = 112
REG_ARB_LUT_LENGTH2 = 114
REG_ARB_OFFSET2 = 116

_ARB_MODE_1000 = 0x0
_ARB_MODE_500 = 0x1
_ARB_MODE_250 = 0x2
_ARB_MODE_125 = 0x3

class ArbWaveGen(_oscilloscope.Oscilloscope):
	def __init__(self):
		super(ArbWaveGen, self).__init__()
		self._register_accessors(_arb_reg_handlers)
		self.id = 15
		self.type = "arbwavegen"

	@needs_commit
	def set_defaults(self):
		super(ArbWaveGen, self).set_defaults()
		self.mode1 = _ARB_MODE_1000
		self.lut_length1 = 8192
		self.phase_modulo1 = 2**29
		self.dead_value1 = 0
		self.interpolation1 = False
		self.phase_step1 = 2**17
		self.phase_step2 = 2**17
		self.enable1 = False
		self.enable2 = False

_arb_reg_handlers = {
	'mmap_access':		(REG_MMAP_ACCESS,		to_reg_bool(0),			from_reg_bool(0)),
	'enable1':			(REG_ARB_SETTINGS,		to_reg_bool(16),		from_reg_bool(16)),
	'phase_rst1':		(REG_ARB_SETTINGS,		to_reg_bool(20),		from_reg_bool(20)),
	'phase_sync1':		(REG_ARB_SETTINGS,		to_reg_bool(22),		from_reg_bool(22)),
	'mode1':			(REG_ARB_SETTINGS,		to_reg_unsigned(0, 2, allow_set=[_ARB_MODE_125, _ARB_MODE_250, _ARB_MODE_500, _ARB_MODE_1000]),
												from_reg_unsigned(0, 2)),
	'interpolation1':	(REG_ARB_SETTINGS,		to_reg_bool(4),			from_reg_bool(4)),
	'lut_length1':		(REG_ARB_LUT_LENGTH1,	to_reg_unsigned(0, 16), from_reg_signed(0, 16)),
	'dead_value1':		(REG_ARB_DEAD_VALUE1,	to_reg_signed(0, 16), 	from_reg_signed(0, 16)),
	'amplitude1':		(REG_ARB_AMPLITUDE1,	to_reg_signed(0, 16), 	from_reg_signed(0, 16)),
	'offset1':			(REG_ARB_OFFSET1,		to_reg_signed(0, 16), 	from_reg_signed(0, 16)),
	'phase_modulo1':	((REG_ARB_PHASE_MOD1_H, REG_ARB_PHASE_MOD1_L),
												to_reg_unsigned(0, 64), from_reg_unsigned(0, 64)),
	'phase_offset1':	((REG_ARB_PHASE_OFFSET1_H, REG_ARB_PHASE_OFFSET1_L),
												to_reg_unsigned(0, 64), from_reg_unsigned(0, 64)),
	'phase_step1':		((REG_ARB_PHASE_STEP1_H, REG_ARB_PHASE_STEP1_L),
												to_reg_unsigned(0, 48), from_reg_unsigned(0, 48)),
	'enable2':			(REG_ARB_SETTINGS,		to_reg_bool(17),		from_reg_bool(17)),
	'phase_rst2':		(REG_ARB_SETTINGS,		to_reg_bool(21),		from_reg_bool(21)),
	'phase_sync2':		(REG_ARB_SETTINGS,		to_reg_bool(23),		from_reg_bool(23)),
	'mode2':			(REG_ARB_SETTINGS,		to_reg_unsigned(8, 2, allow_set=[_ARB_MODE_125, _ARB_MODE_250, _ARB_MODE_500, _ARB_MODE_1000]),
												from_reg_unsigned(8, 2)),
	'interpolation2':	(REG_ARB_SETTINGS,		to_reg_bool(12),			from_reg_bool(12)),
	'lut_length2':		(REG_ARB_LUT_LENGTH2,	to_reg_unsigned(0, 16), from_reg_signed(0, 16)),
	'dead_value2':		(REG_ARB_DEAD_VALUE2,	to_reg_signed(0, 16), 	from_reg_signed(0, 16)),
	'amplitude2':		(REG_ARB_AMPLITUDE2,	to_reg_signed(0, 16), 	from_reg_signed(0, 16)),
	'offset2':			(REG_ARB_OFFSET2,		to_reg_signed(0, 16), 	from_reg_signed(0, 16)),
	'phase_modulo2':	((REG_ARB_PHASE_MOD2_H, REG_ARB_PHASE_MOD2_L),
												to_reg_unsigned(0, 64), from_reg_unsigned(0, 64)),
	'phase_offset2':	((REG_ARB_PHASE_OFFSET2_H, REG_ARB_PHASE_OFFSET2_L),
												to_reg_unsigned(0, 64), from_reg_unsigned(0, 64)),
	'phase_step2':		((REG_ARB_PHASE_STEP2_H, REG_ARB_PHASE_STEP2_L),
												to_reg_unsigned(0, 48), from_reg_unsigned(0, 48))
}
