
import math
import logging

from pymoku._instrument import *
from pymoku._oscilloscope import _CoreOscilloscope, VoltsData
from . import _instrument

log = logging.getLogger(__name__)

REG_LIA_ENABLES			= 96

REG_LIA_PIDGAIN1		= 97
REG_LIA_PIDGAIN2		= 113

REG_LIA_INT_IGAIN1		= 98
REG_LIA_INT_IGAIN2		= 99
REG_LIA_INT_IFBGAIN1	= 100
REG_LIA_INT_IFBGAIN2	= 101
REG_LIA_INT_PGAIN1		= 102
REG_LIA_INT_PGAIN2		= 103

REG_LIA_DIFF_DGAIN1		= 104
REG_LIA_DIFF_DGAIN2		= 119
REG_LIA_DIFF_PGAIN1		= 120
REG_LIA_DIFF_PGAIN2		= 121
REG_LIA_DIFF_IGAIN1		= 122
REG_LIA_DIFF_IGAIN2		= 123
REG_LIA_DIFF_IFBGAIN1	= 124
REG_LIA_DIFF_IFBGAIN2	= 125

REG_LIA_FREQDEMOD_L		= 105
REG_LIA_FREQDEMOD_H		= 106
REG_LIA_PHASEDEMOD_L	= 107
REG_LIA_PHASEDEMOD_H	= 108

REG_LIA_DECBITSHIFT		= 109
REG_LIA_DECOUTPUTSELECT	= 110

REG_LIA_MONSELECT0		= 111
REG_LIA_MONSELECT1		= 114

REG_LIA_SINEOUTAMP		= 112
REG_LIA_SINEOUTOFF		= 127

REG_LIA_IN_OFFSET1		= 115
REG_LIA_OUT_OFFSET1		= 116
REG_LIA_IN_OFFSET2		= 117
REG_LIA_OUT_OFFSET2		= 118

REG_LIA_INPUT_GAIN		= 126


_LIA_MON_NONE	= 0
_LIA_MON_IN		= 1
_LIA_MON_I		= 2
_LIA_MON_Q		= 3
_LIA_MON_PID	= 4 # 5 is also PID for some reason..
_LIA_MON_LO		= 6

_LIA_CONTROL_FS 	= 25.0e6
_LIA_FREQSCALE		= 1.0e9 / 2**48
_LIA_PHASESCALE		= 1.0 / 2**48
_LIA_AMPSCALE		= 1.0 / (2**15 - 1)
_LIA_P_GAINSCALE	= 2.0**16
_LIA_ID_GAINSCALE	= 2.0**24 - 1

class LockInAmp(_CoreOscilloscope):
	def __init__(self):
		super(LockInAmp, self).__init__()
		self._register_accessors(_lia_reg_hdl)

		self.id = 8
		self.type = "lockinamp"

	@needs_commit
	def set_defaults(self):
		""" Reset the lockinamp to sane defaults. """
		super(LockInAmp, self).set_defaults()

		self.pid1_en = 1
		self.pid2_en = 1
		self.pid1_int_i_en = 1
		self.pid2_int_i_en = 1
		self.pid1_int_dc_pole = 0
		self.pid2_int_dc_pole = 0
		self.pid1_int_p_en = 0
		self.pid2_int_p_en = 0
		self.pid1_diff_d_en = 0
		self.pid2_diff_d_en = 0
		self.pid1_diff_i_en = 0
		self.pid2_diff_i_en = 0
		self.pid1_bypass = 0
		self.pid2_bypass = 1
		self.lo_reset = 0

		self._pid_offset = 0

		self.set_filter_parameters(1, 1000, 1)
		self.set_output_offset(0)
		self.set_lo_parameters(40e6, 0)

		self.pid1_int_p_gain = 0.0
		self.pid2_int_p_gain = 0.0
		self.pid1_diff_d_gain = 0.0
		self.pid2_diff_d_gain = 0.0
		self.pid1_diff_p_gain = 0.0
		self.pid2_diff_p_gain = 0.0
		self.pid1_diff_i_gain = 0.0
		self.pid2_diff_i_gain = 0.0
		self.pid1_diff_ifb_gain = 0.0
		self.pid2_diff_ifb_gain = 0.0
		self.decimation_bitshift = 0

		self.monitor_select0 = _LIA_MON_IN
		self.monitor_select1 = _LIA_MON_I

		self.input_gain = 1
		self.set_lo_output(0.5, 0)


	def _recalc_offsets(self):
		if self.slope == 1:
			self.pid1_out_offset = self._pid_offset
			self.pid2_out_offset = 0
		elif self.slope == 2:
			self.pid1_out_offset = 0
			self.pid2_out_offset = self._pid_offset


	@needs_commit
	def set_filter_parameters(self, gain, f_corner, order, integrator=False, mode='range'):
		"""
		:type float:
		:param gain: Overall gain of the low-pass filter (dB)

		:type float:
		:param f_corner: Corner frequency of the low-pass filter (Hz)

		:type order: int {0, 1, 2}
		:param order: filter order; 0 (bypass), first- or second-order.

		:type integrator: bool
		:param integrator: Enable integrator in the filter (add a pole at DC)

		:type mode: string {'range', 'precision'}
		:param mode: Selects signal mode, either optimising for high dynamic range or high precision.
		"""
		impedence_gain = 1 if (self.relays_ch1 & RELAY_LOWZ) else 2
		atten_gain = 1 if (self.relays_ch1 & RELAY_LOWG) else 10
		gain_factor = impedence_gain * atten_gain * (10**(gain / 20.0)) * self._dac_gains()[0] / self._adc_gains()[0]

		coeff = 1 - (math.pi * f_corner) /_LIA_CONTROL_FS

		self.pid1_int_ifb_gain = coeff
		self.pid2_int_ifb_gain = coeff

		self.pid1_int_i_gain = 1.0 - coeff
		self.pid2_int_i_gain = 1.0 - coeff

		self.pid1_int_dc_pole = integrator
		self.pid2_int_dc_pole = integrator

		if order == 0:
			self.pid1_bypass = True
			self.pid2_bypass = True
		if order == 1:
			self.pid1_bypass = False
			self.pid2_bypass = True
			self.slope = 1
		elif order == 2:
			self.pid1_bypass = False
			self.pid2_bypass = False
			self.slope = 2
		else:
			raise ValueOutOfRangeException("Order must be 0 (bypass), 1 or 2; not %d", order)

		if mode == 'precision':
			if order == 1:
				self.input_gain = gain_factor
				self.pid1_pidgain = self.pid2_pidgain = 1.0
			else :
				self.input_gain = self.pid1_pidgain =  math.sqrt(gain_factor)
				self.pid2_pidgain = 1.0
		elif mode == 'range':
			if order == 1:
				self.pid1_pidgain =  gain_factor
				self.input_gain = self.pid2_pidgain = 1.0
			else:
				self.pid1_pidgain = self.pid2_pidgain = math.sqrt(gain_factor)
				self.input_gain = 1.0
		else:
			raise ValueOutOfRangeException('Signal Mode must be one of "precision" or "range", not %s', self.signal_mode)

		self._recalc_offsets()


	@needs_commit
	def set_output_offset(self, offset):
		"""
		Configure lock-in amplifier output offset.

		This output is available on Channel 1 of the Moku:Lab. The amplitude of this
		signal is controlled by the input amplitude and filter gain.

		:type offset: float
		:param offset: (V)
		"""
		self._pid_offset = offset
		self._recalc_offsets()


	@needs_commit
	def set_lo_output(self, amplitude, offset):
		"""
		Configure local oscillator output.

		This output is available on Channel 2 of the Moku:Lab.

		:type amplitude: float
		:param amplitude: (V)

		:type offset: float
		:param offset: (V)
		"""
		self.sineout_amp = amplitude
		self.sineout_offset = offset


	@needs_commit
	def set_lo_parameters(self, frequency, phase, use_q=False):
		"""
		Configure local oscillator parameters

		:type frequency: float
		:param frequency: Hz

		:type phase: float
		:param phase: Degrees, 0-360

		:type use_q: bool
		:param use_q: Use the quadrature output from the mixer (default in-phase)
		"""

		self.frequency_demod = frequency
		self.phase_demod = phase / 360
		self.q_select = use_q


	@needs_commit
	def set_monitor(self, ch, source):
		"""
		Select the point inside the lockin amplifier to monitor.

		There are two monitoring channels available, '1' and '2'; you can mux any of the internal
		monitoring points to either of these channels.

		The source is one of:
			- **none**: Disable monitor channel
			- **input**: ADC Input
			- **out**: Lock-in output
			- **lo**: Local Oscillator output
			- **i**, **q**: Mixer I and Q channels respectively.
		"""
		sources = {
			'none'	: _LIA_MON_NONE,
			'input' : _LIA_MON_IN,
			'out'	: _LIA_MON_PID,
			'lo'	: _LIA_MON_LO,
			'i'		: _LIA_MON_I,
			'q'		: _LIA_MON_Q,
		}

		# Many people naturally use 'I' and 'Q' and I don't care enough to argue
		source = source.lower()

		if ch == 1:
			self.monitor_select0 = sources[source]
		elif ch == 2:
			self.monitor_select1 = sources[source]
		else:
			raise ValueOutOfRangeException("Invalid channel %d", ch)


_lia_reg_hdl = {
	'pid1_en':			(REG_LIA_ENABLES,		to_reg_bool(0),
												from_reg_bool(0)),

	'pid2_en':			(REG_LIA_ENABLES,		to_reg_bool(1),
												from_reg_bool(1)),

	'pid1_int_i_en':	(REG_LIA_ENABLES,		to_reg_bool(2),
												from_reg_bool(2)),

	'pid2_int_i_en':	(REG_LIA_ENABLES,		to_reg_bool(3),
												from_reg_bool(3)),

	'pid1_int_p_en':	(REG_LIA_ENABLES,		to_reg_bool(4),
												from_reg_bool(4)),

	'pid2_int_p_en':	(REG_LIA_ENABLES,		to_reg_bool(5),
												from_reg_bool(5)),

	'pid1_diff_d_en':	(REG_LIA_ENABLES,		to_reg_bool(6),
												from_reg_bool(6)),

	'pid2_diff_d_en':	(REG_LIA_ENABLES,		to_reg_bool(7),
												from_reg_bool(7)),

	'pid1_diff_p_en':	(REG_LIA_ENABLES,		to_reg_bool(8),
												from_reg_bool(8)),

	'pid2_diff_p_en':	(REG_LIA_ENABLES,		to_reg_bool(9),
												from_reg_bool(9)),

	'pid1_diff_i_en':	(REG_LIA_ENABLES,		to_reg_bool(10),
												from_reg_bool(10)),

	'pid2_diff_i_en':	(REG_LIA_ENABLES,		to_reg_bool(11),
												from_reg_bool(11)),

	'pid1_bypass':		(REG_LIA_ENABLES,		to_reg_bool(12),
												from_reg_bool(12)),

	'pid2_bypass':		(REG_LIA_ENABLES,		to_reg_bool(13),
												from_reg_bool(13)),

	'lo_reset':			(REG_LIA_ENABLES,		to_reg_bool(14),
												from_reg_bool(14)),

	'pid1_int_dc_pole':	(REG_LIA_ENABLES,		to_reg_bool(15),
												from_reg_bool(15)),

	'pid2_int_dc_pole':	(REG_LIA_ENABLES,		to_reg_bool(16),
												from_reg_bool(16)),

	'q_select':			(REG_LIA_ENABLES,		to_reg_bool(17),
												from_reg_bool(17)),

	'pid1_in_offset':	(REG_LIA_IN_OFFSET1,	to_reg_signed(0, 16),
												from_reg_signed(0, 16)),

	'pid2_in_offset':	(REG_LIA_IN_OFFSET2,	to_reg_signed(0, 16),
												from_reg_signed(0, 16)),

	'pid1_out_offset':	(REG_LIA_OUT_OFFSET1,	to_reg_signed(0, 16, xform=lambda obj, x: x * obj._dac_gains()[0]),
												from_reg_signed(0, 16, xform=lambda obj, x: x / obj._dac_gains()[0])),

	'pid2_out_offset':	(REG_LIA_OUT_OFFSET2,	to_reg_signed(0, 16, xform=lambda obj, x: x * obj._dac_gains()[0]),
												from_reg_signed(0, 16, xform=lambda obj, x: x / obj._dac_gains()[0])),

	'pid1_pidgain':		(REG_LIA_PIDGAIN1,		to_reg_signed(0, 32, xform=lambda obj, x : x * _LIA_P_GAINSCALE),
												from_reg_signed(0, 32, xform=lambda obj, x: x / _LIA_P_GAINSCALE)),

	'pid2_pidgain':		(REG_LIA_PIDGAIN2,		to_reg_signed(0, 32, xform=lambda obj, x : x * _LIA_P_GAINSCALE),
												from_reg_signed(0, 32, xform=lambda obj, x: x / _LIA_P_GAINSCALE)),

	'pid1_int_i_gain':	(REG_LIA_INT_IGAIN1,	to_reg_signed(0, 25, xform=lambda obj, x: x * _LIA_ID_GAINSCALE),
												from_reg_signed(0, 25, xform=lambda obj, x: x / _LIA_ID_GAINSCALE)),

	'pid2_int_i_gain':	(REG_LIA_INT_IGAIN2,	to_reg_signed(0, 25, xform=lambda obj, x: x * _LIA_ID_GAINSCALE),
												from_reg_signed(0, 25, xform=lambda obj, x: x / _LIA_ID_GAINSCALE)),

	'pid1_int_ifb_gain':(REG_LIA_INT_IFBGAIN1,	to_reg_signed(0, 25, xform=lambda obj, x: x*_LIA_ID_GAINSCALE),
												from_reg_signed(0, 25, xform=lambda obj, x: x / _LIA_ID_GAINSCALE)),

	'pid2_int_ifb_gain':(REG_LIA_INT_IFBGAIN2,	to_reg_signed(0, 25, xform=lambda obj, x: x*_LIA_ID_GAINSCALE),
												from_reg_signed(0, 25, xform=lambda obj, x: x / _LIA_ID_GAINSCALE)),

	'pid1_int_p_gain':	(REG_LIA_INT_PGAIN1,	to_reg_signed(0, 25, xform=lambda obj, x: x*_LIA_ID_GAINSCALE),
												from_reg_signed(0, 25, xform=lambda obj, x: x / _LIA_ID_GAINSCALE)),

	'pid2_int_p_gain':	(REG_LIA_INT_PGAIN2,	to_reg_signed(0, 25, xform=lambda obj, x: x*_LIA_ID_GAINSCALE),
												from_reg_signed(0, 25, xform=lambda obj, x: x / _LIA_ID_GAINSCALE)),

	'pid1_diff_d_gain':	(REG_LIA_DIFF_DGAIN1,	to_reg_signed(0, 25, xform=lambda obj, x: x*_LIA_ID_GAINSCALE),
												from_reg_signed(0, 25, xform=lambda obj, x: x / _LIA_ID_GAINSCALE)),

	'pid2_diff_d_gain':	(REG_LIA_DIFF_DGAIN2,	to_reg_signed(0, 25, xform=lambda obj, x: x*_LIA_ID_GAINSCALE),
												from_reg_signed(0, 25, xform=lambda obj, x: x / _LIA_ID_GAINSCALE)),

	'pid1_diff_p_gain':	(REG_LIA_DIFF_PGAIN1,	to_reg_signed(0, 25, xform=lambda obj, x: x*_LIA_ID_GAINSCALE),
												from_reg_signed(0, 25, xform=lambda obj, x: x / _LIA_ID_GAINSCALE)),

	'pid2_diff_p_gain':	(REG_LIA_DIFF_PGAIN2,	to_reg_signed(0, 25, xform=lambda obj, x: x*_LIA_ID_GAINSCALE),
												from_reg_signed(0, 25, xform=lambda obj, x: x / _LIA_ID_GAINSCALE)),

	'pid1_diff_i_gain':	(REG_LIA_DIFF_IGAIN1,	to_reg_signed(0, 25, xform=lambda obj, x: x*_LIA_ID_GAINSCALE),
												from_reg_signed(0, 25, xform=lambda obj, x: x / _LIA_ID_GAINSCALE)),

	'pid2_diff_i_gain':	(REG_LIA_DIFF_IGAIN2,	to_reg_signed(0, 25, xform=lambda obj, x: x*_LIA_ID_GAINSCALE),
												from_reg_signed(0, 25, xform=lambda obj, x: x / _LIA_ID_GAINSCALE)),

	'pid1_diff_ifb_gain':(REG_LIA_DIFF_IFBGAIN1,	to_reg_signed(0, 25, xform=lambda obj, x: x*_LIA_ID_GAINSCALE),
												from_reg_signed(0, 25, xform=lambda obj, x: x / _LIA_ID_GAINSCALE)),

	'pid2_diff_ifb_gain':(REG_LIA_DIFF_IFBGAIN2,	to_reg_signed(0, 25, xform=lambda obj, x: x*_LIA_ID_GAINSCALE),
												from_reg_signed(0, 25, xform=lambda obj, x: x / _LIA_ID_GAINSCALE)),

	'frequency_demod':	((REG_LIA_FREQDEMOD_H, REG_LIA_FREQDEMOD_L),
												to_reg_unsigned(0, 48, xform=lambda obj, x: x / _LIA_FREQSCALE),
												from_reg_unsigned(0, 48, xform=lambda obj, x: x * _LIA_FREQSCALE)),

	'phase_demod':		((REG_LIA_PHASEDEMOD_H, REG_LIA_PHASEDEMOD_L),
												to_reg_unsigned(0, 48, xform=lambda obj, x: x / _LIA_PHASESCALE),
												from_reg_unsigned(0, 48, xform=lambda obj, x: x * _LIA_PHASESCALE)),

	'decimation_bitshift':(REG_LIA_DECBITSHIFT,	to_reg_unsigned(0, 4),
												from_reg_unsigned(0, 4)),

	'monitor_select0':	(REG_LIA_MONSELECT0,	to_reg_unsigned(0, 3, allow_set=[_LIA_MON_NONE, _LIA_MON_IN, _LIA_MON_PID, _LIA_MON_I, _LIA_MON_Q, _LIA_MON_LO]),
												from_reg_unsigned(0, 3)),

	'monitor_select1':	(REG_LIA_MONSELECT1,	to_reg_unsigned(0, 3, allow_set=[_LIA_MON_NONE, _LIA_MON_IN, _LIA_MON_PID, _LIA_MON_I, _LIA_MON_Q, _LIA_MON_LO]),
												from_reg_unsigned(0, 3)),

	'sineout_amp':		(REG_LIA_SINEOUTAMP,	to_reg_signed(0, 16, xform=lambda obj, x: x / _LIA_AMPSCALE),#*  obj._dac_gains()[1] / _LIA_AMPSCALE),
												from_reg_signed(0, 16, xform=lambda obj, x: x * _LIA_AMPSCALE)), #* _LIA_AMPSCALE /  obj._dac_gains()[1])),

	'sineout_offset':	(REG_LIA_SINEOUTOFF,	to_reg_signed(0, 16, xform=lambda obj, x: x * obj._dac_gains()[1] / _LIA_AMPSCALE),
												from_reg_signed(0, 16, xform=lambda obj, x: x * _LIA_AMPSCALE / obj._dac_gains()[1])),

	'input_gain':		(REG_LIA_INPUT_GAIN,	to_reg_signed(0,32, xform=lambda obj, x: x * _LIA_P_GAINSCALE),
												from_reg_signed(0,32, xform=lambda obj, x: x / _LIA_P_GAINSCALE)),
}
