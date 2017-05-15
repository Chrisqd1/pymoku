
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


REG_ARB_MODE = 96

_ARB_MODE_1000 = 0x0
_ARB_MODE_500 = 0x1
_ARB_MODE_250 = 0x2
_ARB_MODE_125 = 0x3

class ArbWaveGen(_oscilloscope.Oscilloscope, _siggen.BasicSignalGenerator):
	def __init__(self):
		super(ArbWaveGen, self).__init__()
		self._register_accessors(_arb_reg_handlers)

		self.id = 15
		self.type = "arbwavegen"

	@needs_commit
	def set_defaults(self):
		""" Reset the Oscilloscope to sane defaults. """
		super(ArbWaveGen, self).set_defaults()
		self.mode = _ARB_MODE_1000

_arb_reg_handlers = {
	'mode':				(REG_ARB_MODE,		to_reg_unsigned(0, 2, allow_set=[_ARB_MODE_125, _ARB_MODE_250, _ARB_MODE_500, _ARB_MODE_1000]),
											from_reg_unsigned(0, 2)),
	'interpolation':	(REG_ARB_MODE,		to_reg_bool(8),			from_reg_bool(8))
}
