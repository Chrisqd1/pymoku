
import math
import logging

from _instrument import *
import _instrument
import _frame_instrument
import _siggen

# Annoying that import * doesn't pick up function defs??
_sgn = _instrument._sgn
_usgn = _instrument._usgn

log = logging.getLogger(__name__)

REG_LIA_ENABLES		= 96
REG_LIA_PIDGAIN		= 97
REG_LIA_INT_IGAIN	= 98
REG_LIA_INT_IFBGAIN	= 99
REG_LIA_INT_PGAIN	= 100
REG_LIA_DIFF_DGAIN	= 101
REG_LIA_DIFF_PGAIN	= 102
REG_LIA_DIFF_IGAIN	= 103
REG_LIA_DIFF_IFBGAIN	= 104
REG_LIA_FREQDEMOD_L	= 105
REG_LIA_FREQDEMOD_H	= 106
REG_LIA_PHASEDEMOD_L	= 107
REG_LIA_PHASEDEMOD_H	= 108
REG_LIA_DECBITSHIFT	= 109
REG_LIA_DECOUTPUTSELECT = 110
REG_LIA_MONSELECT	= 111
REG_LIA_SINEOUTAMP		= 112

### Every constant that starts with LIA_ will become an attribute of pymoku.instruments ###

LIA_MONITOR_I		= 0
LIA_MONITOR_Q		= 1
LIA_MONITOR_PID		= 2
LIA_MONITOR_INPUT	= 3

_LIA_CONTROL_FS 	= 125e6
_LIA_SINE_FS		= 1e9
_LIA_COEFF_WIDTH	= 16
_LIA_FREQSCALE		= float(1e9) / 2**48
_LIA_PHASESCALE		= 1.0 / 2**48
_LIA_AMPSCALE		= 4.0 / (2**16)


class LockInAmp(_frame_instrument.FrameBasedInstrument):
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
		"""Create a new Lock-In-Amplifier instrument, ready to be attached to a Moku."""
		self.scales = {}

		super(LockInAmp, self).__init__(_frame_instrument.DataFrame)
		self.id = 7
		self.type = "lockinamp"
		self.calibration = None

	def set_defaults(self):
		""" Reset the lockinamp to sane defaults. """
		super(LockInAmp, self).set_defaults()
		#TODO this should reset ALL registers

		self.pid1_en = 1
		self.pid2_en = 1
		self.pid1_int_i_en = 1
		self.pid2_int_i_en = 1
		self.pid1_int_p_en = 0
		self.pid2_int_p_en = 0
		self.pid1_diff_d_en = 0
		self.pid2_diff_d_en = 0
		self.pid1_diff_i_en = 0
		self.pid2_diff_i_en = 0
		self.pid1_bypass = 0
		self.pid2_bypass = 0
		self.lo_reset = 0

		self.pid1_pidgain = 2
		self.pid2_pidgain = 2
		self.pid1_int_i_gain = 5000.0/(2**15 - 1)
		self.pid2_int_i_gain = 5000.0/(2**15-1)
		self.pid1_int_ifb_gain = 1.0 - 2*math.pi*1e6/125e6
		self.pid2_int_ifb_gain = 1.0 - 2*math.pi*1e6/125e6
		self.pid1_int_p_gain = 0
		self.pid2_int_p_gain = 0
		self.pid1_diff_d_gain = 0
		self.pid2_diff_d_gain = 0
		self.pid1_diff_p_gain = 0
		self.pid2_diff_p_gain = 0
		self.pid1_diff_i_gain = 0
		self.pid2_diff_i_gain = 0
		self.pid1_diff_ifb_gain = 0
		self.pid2_diff_ifb_gain = 0
		self.frequency_demod = 10e6
		self.phase_demod = 0
		self.decimation_bitshift = 0#7
		self.decimation_output_select = 0
		self.monitor_select = 0
		self.sineout_amp = 1.0
	# def convert_corner(self, ReqCorner):
	# 	DSPCoeff = (1-ReqCorner/self._LIA_CONTROL_FS)*(2**_LIA_COEFF_WIDTH-1)
	# 	return DSPCoeff

	# def convert_frequency(self, ReqFrequency):
	# 	DSPFreq = 2**48*ReqFrequency/self._LIA_SINE_FS
	# 	return DSPFreq

	# def convert_gain(self, ReqGain):
	# 	DSPGain = ReqGain/(2**(self._LIA_COEFF_WIDTH-1)-1)
	# 	return DSPGain




_lia_reg_hdl = [
	('pid1_en',		REG_LIA_ENABLES,		lambda s, old: (old & ~1) | int(s),
											lambda rval: rval & 1),
	('pid2_en',		REG_LIA_ENABLES,		lambda s, old: (old & ~2) | int(s) << 1,
											lambda rval: rval & 2 >> 1),
	('pid1_int_i_en',	REG_LIA_ENABLES,	lambda s, old: (old & ~2**2) | int(s) << 2,
											lambda rval: rval & 2 >> 2),
	('pid2_int_i_en',	REG_LIA_ENABLES,	lambda s, old: (old & ~2**3) | int(s) << 3,
											lambda rval: rval & 2 >> 3),
	('pid1_int_p_en',	REG_LIA_ENABLES,	lambda s, old: (old & ~2**4) | int(s) << 4,
											lambda rval: rval & 2 >> 4),
	('pid2_int_p_en',	REG_LIA_ENABLES,	lambda s, old: (old & ~2**5) | int(s) << 5,
											lambda rval: rval & 2 >> 5),
	('pid1_diff_d_en',	REG_LIA_ENABLES,	lambda s, old: (old & ~2**6) | int(s) << 6,
											lambda rval: rval & 2 >> 6),
	('pid2_diff_d_en',	REG_LIA_ENABLES,	lambda s, old: (old & ~2**7) | int(s) << 7,
											lambda rval: rval & 2 >> 7),
	('pid1_diff_p_en',	REG_LIA_ENABLES,	lambda s, old: (old & ~2**8) | int(s) << 8,
											lambda rval: rval & 2 >> 8),
	('pid2_diff_p_en',	REG_LIA_ENABLES,	lambda s, old: (old & ~2**9) | int(s) << 9,
											lambda rval: rval & 2 >> 9),
	('pid1_diff_i_en',	REG_LIA_ENABLES,	lambda s, old: (old & ~2**10) | int(s) << 10,
											lambda rval: rval & 2 >> 10),
	('pid2_diff_i_en',	REG_LIA_ENABLES,	lambda s, old: (old & ~2**11) | int(s) << 11,
											lambda rval: rval & 2 >> 11),
	('pid1_bypass',	REG_LIA_ENABLES,		lambda s, old: (old & ~2**12) | int(s) << 12,
											lambda rval: rval & 2 >> 12),
	('pid2_bypass',	REG_LIA_ENABLES,		lambda s, old: (old & ~2**13) | int(s) << 13,
											lambda rval: rval & 2 >> 13),
	('lo_reset',	REG_LIA_ENABLES,		lambda s, old: (old & ~2**14) | int(s) << 14,
											lambda rval: rval & 2 >> 14),
	('pid1_pidgain',	REG_LIA_PIDGAIN,	lambda s, old: (old & ~0x0000FFFF) | _sgn(s,16), 
											lambda rval: (rval & 0x0000FFFF)*(2**15 -1)),
	('pid2_pidgain',	REG_LIA_PIDGAIN,	lambda s, old: (old & ~0xFFFF0000) | _sgn(s,16) << 16, 
											lambda rval: (rval & 0xFFFF0000)*(2**15 -1)),
	('pid1_int_i_gain',	REG_LIA_INT_IGAIN,	lambda s, old: (old & ~0x0000FFFF) | _sgn(s * (2**15 - 1), 16), 
											lambda rval: (rval & 0x0000FFFF)*(2**15 -1)),
	('pid2_int_i_gain',	REG_LIA_INT_IGAIN,	lambda s, old: (old & ~0xFFFF0000) | _sgn(s * (2**15 - 1), 16) << 16, 
											lambda rval: (rval & 0xFFFF0000)*(2**15 -1)),
	('pid1_int_ifb_gain',	REG_LIA_INT_IFBGAIN,
											lambda s, old: (old & ~0x0000FFFF) | _sgn(s * (2**15 - 1), 16), 
											lambda rval: (rval & 0x0000FFFF)*(2**15 -1)),
	('pid2_int_ifb_gain',	REG_LIA_INT_IFBGAIN,
											lambda s, old: (old & ~0xFFFF0000) | _sgn(s * (2**15 - 1) ,16) << 16, 
											lambda rval: (rval & 0xFFFF0000)*(2**15 -1)),
	('pid1_int_p_gain',	REG_LIA_INT_PGAIN,
											lambda s, old: (old & ~0x0000FFFF) | _sgn(s * (2**15 - 1), 16), 
											lambda rval: (rval & 0x0000FFFF)*(2**15 -1)),
	('pid2_int_p_gain',	REG_LIA_INT_PGAIN,
											lambda s, old: (old & ~0xFFFF0000) | _sgn(s * (2**15 - 1), 16) << 16, 
											lambda rval: (rval & 0xFFFF0000)*(2**15 -1)),
	('pid1_diff_d_gain',	REG_LIA_DIFF_DGAIN,
											lambda s, old: (old & ~0x0000FFFF) | _sgn(s * (2**15 - 1), 16), 
											lambda rval: (rval & 0x0000FFFF)*(2**15 -1)),
	('pid2_diff_d_gain',	REG_LIA_DIFF_DGAIN,
											lambda s, old: (old & ~0xFFFF0000) | _sgn(s * (2**15 - 1), 16) << 16, 
											lambda rval: (rval & 0xFFFF0000) * (2**15 - 1)),
	('pid1_diff_p_gain',	REG_LIA_DIFF_PGAIN,
											lambda s, old: (old & ~0x0000FFFF) | _sgn(s * (2**15 - 1), 16), 
											lambda rval: (rval & 0x0000FFFF)*(2**15 -1)),
	('pid2_diff_p_gain',	REG_LIA_DIFF_PGAIN,
											lambda s, old: (old & ~0xFFFF0000) | _sgn(s * (2**15 - 1), 16) << 16, 
											lambda rval: (rval & 0xFFFF0000)*(2**15 -1)),
	('pid1_diff_i_gain',	REG_LIA_DIFF_IGAIN,
											lambda s, old: (old & ~0x0000FFFF) | _sgn(s * (2**15 - 1), 16), 
											lambda rval: (rval & 0x0000FFFF)*(2**15 -1)),
	('pid2_diff_i_gain',	REG_LIA_DIFF_IGAIN,
											lambda s, old: (old & ~0xFFFF0000) | _sgn(s * (2**15 - 1), 16) << 16, 
											lambda rval: (rval & 0xFFFF0000) * (2**15 -1)),
	('pid1_diff_ifb_gain',	REG_LIA_DIFF_IFBGAIN,
											lambda s, old: (old & ~0x0000FFFF) | _sgn(s * (2**15 - 1), 16), 
											lambda rval: (rval & 0x0000FFFF) * (2**15 -1)),
	('pid2_diff_ifb_gain',	REG_LIA_DIFF_IFBGAIN,
											lambda s, old: (old & ~0xFFFF0000) | _sgn(s * (2**15 - 1), 16) << 16, 
											lambda rval: (rval & 0xFFFF0000) * (2**15 -1)),
	('frequency_demod', 	(REG_LIA_FREQDEMOD_H, REG_LIA_FREQDEMOD_L),
											lambda s, old: ((old[0] & ~0x0000FFFF) | _usgn(s / _LIA_FREQSCALE, 48) >> 32 , _usgn(s / _LIA_FREQSCALE, 48) & 0xFFFFFFFF),
											lambda rval: _LIA_FREQSCALE * ((rval[0] & 0x0000FFFF) << 32 | rval[1])),
	('phase_demod', 		(REG_LIA_PHASEDEMOD_H, REG_LIA_PHASEDEMOD_L),
											lambda s, old: ((old[0] & ~0x0000FFFF) | _usgn(s / _LIA_PHASESCALE, 48) >> 32 , _usgn(s / _LIA_PHASESCALE, 48) & 0xFFFFFFFF),
											lambda rval: _LIA_PHASESCALE * ((rval[0] & 0x0000FFFF) << 32 | rval[1])),
	('decimation_bitshift',	REG_LIA_DECBITSHIFT,
											lambda s, old: (old & ~0x0000000F) | int(s), 
											lambda rval: rval & 0x0000000F),
	('decimation_output_select', REG_LIA_DECOUTPUTSELECT,
											lambda s, old: (old & ~0x0000000F) | int(s),
											lambda rval: rval & 0x0000000F),
	('monitor_select', 		REG_LIA_MONSELECT,
											lambda s, old: (old & ~3) | int(s),
											lambda rval: rval & 3),
	('sineout_amp',			REG_LIA_SINEOUTAMP,
											lambda s, old: (old & ~0x0000FFFF) | _usgn(s / _LIA_AMPSCALE,16),
											lambda rval: (rval & 0x0000FFFF) * _LIA_AMPSCALE),
	]
_instrument._attach_register_handlers(_lia_reg_hdl, LockInAmp)
