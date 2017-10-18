import math
import logging

from pymoku._instrument import *
from pymoku._oscilloscope import _CoreOscilloscope, VoltsData
from pymoku._pid_controller import PIDController
from . import _instrument
from . import _utils

log = logging.getLogger(__name__)

REG_LIA_ENABLES			= 96

REG_LIA_PIDGAIN1		= 97
REG_LIA_PIDGAIN2		= 98

REG_LIA_INT_IGAIN1		= 99
REG_LIA_INT_IGAIN2		= 100
REG_LIA_INT_IFBGAIN1	= 101
REG_LIA_INT_IFBGAIN2	= 102
REG_LIA_INT_PGAIN1		= 103
REG_LIA_INT_PGAIN2		= 104

REG_LIA_GAIN_STAGE		= 105
REG_LIA_DIFF_DGAIN2		= 106
REG_LIA_DIFF_PGAIN1		= 107
REG_LIA_DIFF_PGAIN2		= 108
REG_LIA_DIFF_IGAIN1		= 109
REG_LIA_DIFF_IGAIN2		= 110
REG_LIA_DIFF_IFBGAIN1	= 111
REG_LIA_DIFF_IFBGAIN2	= 112  

REG_LIA_IN_OFFSET1		= 113
REG_LIA_OUT_OFFSET1		= 114

REG_LIA_INPUT_GAIN		= 117

REG_LIA_FREQDEMOD_L		= 118
REG_LIA_FREQDEMOD_H		= 119
REG_LIA_PHASEDEMOD_L	= 120
REG_LIA_PHASEDEMOD_H	= 121

REG_LIA_LO_FREQ_L		= 122
REG_LIA_LO_FREQ_H		= 123
REG_LIA_LO_PHASE_L		= 124
REG_LIA_LO_PHASE_H		= 125

REG_LIA_SINEOUTAMP		= 126
REG_LIA_SINEOUTOFF		= 126

REG_LIA_MONSELECT		= 127

REG_LIA_PM_CGAIN 		= 74
REG_LIA_PM_INTSHIFT 	= 74
REG_LIA_PM_CSHIFT 		= 74
REG_LIA_PM_RESET		= 74
REG_LIA_PM_OUTDEC 		= 75
REG_LIA_PM_OUTSHIFT 	= 75
REG_LIA_PM_BW1 			= 71
REG_LIA_PM_AUTOA1 		= 72
REG_LIA_PM_REACQ		= 73
REG_LIA_SIG_SELECT		= 76

_LIA_MON_NONE	= 0
_LIA_MON_IN1	= 1
_LIA_MON_I		= 2
_LIA_MON_Q		= 3
_LIA_MON_OUT	= 4 
_LIA_MON_AUX	= 5
_LIA_MON_IN2	= 6
_LIA_MON_DEMOD	= 7


_LIA_CONTROL_FS 	= 25.0e6
_LIA_FREQSCALE		= 1.0e9 / 2**48
_LIA_PHASESCALE		= 1.0 / 2**48
_LIA_P_GAINSCALE	= 2.0**16
_LIA_ID_GAINSCALE	= 2.0**24 - 1

class LockInAmp(PIDController, _CoreOscilloscope):
	def __init__(self):
		super(LockInAmp, self).__init__()
		self._register_accessors(_lia_reg_hdl)

		self.id = 8
		self.type = "lockinamp"

	@needs_commit
	def set_defaults(self):
		""" Reset the lockinamp to sane defaults. """
		#super(LockInAmp, self).set_defaults()

		# Avoid calling the PID controller set_defaults
		_CoreOscilloscope.set_defaults(self)

		self.lpf_en = 1
		self.lpf_int_i_en = 0
		self.lpf_int_dc_pole = 0
		self.lpf_pen = 1
		self.lpf_diff_d_en = 0 #TODO Not used according to Confluence, should we touch it at all?
		self.lpf_den = 0

		self.lo_reset = 0 #TODO: Not used, we shouldn't set this in defaults

		self.ch1_pid1_en = 1
		self.ch1_pid1_ien = 0
		self.ch1_pid1_int_dc_pole = 0
		self.ch1_pid1_pen = 1
		self.ch1_pid1_den = 0
		self.pid1_ch1_den = 0

		self._pid_offset = 0

		self.lpf_int_p_gain = 2**12 / 2**24
		self.lpf_diff_d_gain = 0.0
		self.lpf_diff_p_gain = 0.0
		self.lpf_diff_i_gain = 0.0
		self.lpf_diff_ifb_gain = 0.0

		self.ch1_pid1_pidgain = 1.0
		self.gainstage_gain = 1.0
		self.ch1_pid1_int_p_gain = 2**12 / 2**24
		self.ch1_pid1_diff_p_gain = 0.0
		self.ch1_pid1_diff_i_gain = 0.0
		self.ch1_pid1_diff_ifb_gain = 0.0
		self.decimation_bitshift = 0

		self.monitor_select0 = _LIA_MON_IN1
		self.monitor_select1 = _LIA_MON_IN2

		self.autoacquire = 1
		self.bandwidth = 0
		self.lo_PLL = 0
		self.pid_select = 0
		self.gain_select = 1
		self.pid_ch_select = 0
		self.aux_select = 1
		self.autoacquire = 1
		self.lo_PLL_reset = 0
		self.lo_reacquire = 0
		self.ext_demod = 0

		self.output_decimation = 1
		self.output_bitshift = 0

		self.set_filter_parameters(1e3, 2)


		self.set_demod_parameters(1e6, 0)
		self.set_main_out()
		self.set_aux_out('demod')

		self.set_lo_output(0.5, 10e6, 0)
		self.set_demodulation('internal', 1e6, 0)

		self.set_pid_channel(1)
		self.set_signal_mode('iq')
		self.set_aux_out('sine')
		self.set_main_out('ch1')

		self.input_gain = 1.0

		self.filt_bypass1 = 1
		self.filt_bypass2 = 1
		self.lpf_bypass = 1
		self.ch1_pid1_bypass = 1
		self.set_by_gain(1, kp=1)
		# self.filt_bypass = 0

	@needs_commit
	def set_pid_by_gain(self, g, kp=0, ki=0, kd=0, si=None, sd=None, in_offset=0, out_offset=0):
		self._set_by_gain(1, g, kp, ki, kd, 0, si, sd, in_offset, out_offset, touch_ii=False)

	@needs_commit
	def set_pid_by_frequency(self, kp=1, i_xover=None, d_xover=None, si=None, sd=None, in_offset=0, out_offset=0):
		g, kp, ki, kd, kii, si, sd = self._calculate_gains_by_frequency(kp, i_xover, d_xover, None, si, sd)
		self._set_by_gain(1, g, kp, ki, kd, 0, si, sd, in_offset, out_offset, touch_ii=False)

	set_by_gain = set_pid_by_gain
	set_by_frequency = set_pid_by_frequency

	@needs_commit
	def set_main_out(self, sel='ch1', offset=0.0):
		"""
		Selects the signal that is routed to the Main Output Channel 1.

		sel is one of:
			- **ch1** -  the lock-in amplifier signal
			- **offset** - the main output offset voltage
			- **none** - disable the output

		:type sel: string; {'ch1','offset','none'}
		:param sel: Main output signal select

		:type offset: float; [-1.0,1.0] V
		:param offset: Main output offset

		"""
		_utils.check_parameter_valid('set', sel, allowed=['ch1','offset','none'], desc="main output signal select")
		_utils.check_parameter_valid('range', offset, allowed=[-1.0,1.0], desc="main output offset")

		# TODO: Double-check this logic?
		self._pid_offset = offset
		self._recalc_offsets()

		# Turn on the auxillary output
		if sel == 'ch1':
			self.ch1_signal_en = True
			self.ch1_out_en = True
		elif sel == 'offset':
			self.ch1_signal_en = False
			self.ch1_out_en = True
		elif sel == 'none':
			self.ch1_out_en = False
		else:
			# Should never be reached
			raise Exception("Invalid main output selection.")

	@needs_commit
	def set_aux_out(self, auxsel, offset=0.0):
		"""
		Selects the signal that is routed to the Auxillary Output Channel 2.

		auxsel is one of:
			- **sine** - a sine wave that has independent parameters to the internal local oscillator
			- **ch2** -  the second lock-in amplifier signal
			- **demod** - the signal used for demodulation
			- **offset** - the auxillary output offset voltage
			- **none** - disable the output

		:type auxsel: string; {'sine', 'ch2', 'demod', 'offset','none'}
		:param auxsel: Auxillary output signal select

		"""
		_utils.check_parameter_valid('set', auxsel, allowed=['sine', 'demod', 'ch2','offset','none'], desc="auxillary output signal select")
		_utils.check_parameter_valid('range', offset, allowed=[-1.0,1.0], desc="auxillary output offset")

		# Turns on the auxillary output for most cases
		self.ch2_out_en = True

		if auxsel == 'sine':
			self.aux_select = 0
		elif auxsel == 'ch2':
			self.aux_select = 1
		elif auxsel == 'demod':
			self.aux_select = 2
		elif auxsel == 'offset':
			self.ch2_signal_en = False
		elif auxsel == 'none':
			self.ch2_out_en = False
		else:
			# Should never be reached
			raise Exception("Invalid auxillary output selection.")

	@needs_commit
	def set_single_channel_sig(self, signal='i'):
		"""

		Selects the signal sent to ch 1 when only one lockin signal is active
		
		signal is one of:
			- **i** : the i channel coming from the mixer
			- **q** : the q channel coming from the mixer
			- **R** : the magnitude of the input signal 
			- **theta** : the phase of the signal with resepct to the local oscillator

		:type string:
		:param signal: signal routed to output channel 1

		"""
		if self.aux_select == 1 :
			raise InvalidConfigurationException('Channel 2 active. Cannot change channel 1 output.')
		elif signal == 'i' :
			self.pid_select = 0
			self.pid_mode_select = 0
		elif signal == 'q' :
			self.pid_select = 1
			self.pid_mode_select = 0
		elif signal == 'r' :
			self.pid_select = 0
			self.pid_mode_select = 1
		elif signal == 'theta' :
			self.pid_select = 1
			self.pid_mode_select = 1
		else :
			raise ValueOutOfRangeException('Signal Mode must be one of "i", "q", "r" or "theta", not %s. Value unchanged', signal)

	@needs_commit
	def set_signal_mode(self, mode='iq'):
		"""
		Sets "I/Q" mode or "R/Theta" mode

		:type string:
		:param mode: set the signal mode either  IQ or R/Theta 

		"""
		if mode == 'r_theta':
			self.pid_mode_select = 1
			self.gain_mode_select = 1
		elif mode == 'iq':
			self.pid_mode_select = 0
			self.gain_mode_select = 0
		else :
			self.pid_mode_select = 0
			self.gain_mode_select = 0
			raise ValueOutOfRangeException('Signal Mode must be one of "r_theta" or "iq", not %s. Defaulted to iq mode.', mode)

	@needs_commit
	def set_pid_channel(self, ch=1):
		"""
		Sets which output channel is used by the PID.

		Only selectable when both channels are active.

		:type int: ch; [1,2]
		:param channel: Determines the output channel of the PID controller. 
	
		"""
		_utils.check_parameter_valid('set', ch, allowed=[1,2], desc="PID output channel")

		if (self.aux_select != 1)  and (ch == 2):
			self.pid_ch_select = 0
			raise InvalidConfigurationException('Cannot place pid on second channel. Only one channel selected. Output routed to channel 1') 
		else:
			self.pid_ch_select = self.pid_select = ch - 1

	@needs_commit
	def set_gain(self, gain):
		"""
		Set the gain of the gain stage.

		:type gain: float; [0,10e3]
		:param gain: Gain
		"""
		utils.check_parameter_valid('range', gain, allowed=[0,10e3], desc="gain")

		self.gainstage_gain = gain

	@needs_commit
	def set_demodulation(self, mode, frequency, phase=0):
		"""
		Configure the demodulation stage
		
		The mode is one of:
			- **internal** : for an internally set LO
			- **external** : to directly use an external signal for demodulation (Note: Q is not selectable in this mode)
			- **external_pll** : to use an external signal for demodulation after running it through an internal pll

		:type mode: string; {'internal', 'external', 'external_pll'}
		:param mode: Demodulation mode

		:type frequency: float; [0, 200e6] Hz
		:param frequency: Demodulation signal frequency

		:type phase: float; [0, 360] deg
		:param phase: Demodulation signal phase


		"""
		_utils.check_parameter_valid('range', frequency, allowed=[0,200e6], desc="demodulation frequency", units="Hz")
		_utils.check_parameter_valid('range', phase, allowed=[0,360], desc="demodulation phase", units="degrees")

		self.frequency_demod = frequency
		self.phase_demod = phase

		if mode == 'internal':
			self.ext_demod = 0
			self.lo_PLL = 0
		elif mode == 'external':
			self.ext_demod = 1
			self.lo_PLL = 0
		elif mode == 'external_pll':
			self.ext_demod = 0
			self.lo_PLL = 1
			self.lo_reacquire = 1
		else :
			raise ValueOutOfRangeException('LO Mode must be one of "internal", "external" or "external_pll", not %s', mode)


	def _recalc_offsets(self):
		if self.slope == 1:
			self.lpf_out_offset = self._pid_offset
			self.pid2_out_offset = 0
		elif self.slope == 2:
			self.lpf_out_offset = 0
			self.pid2_out_offset = self._pid_offset


	@needs_commit
	def set_filter_parameters(self, f_corner, order, gain=1.0):
		"""
		Set the low-pass filter parameters. 

		:type f_corner: float; # TODO: Range?
		:param f_corner: Corner frequency of the low-pass filter (Hz)

		:type order: int; [0, 1, 2]
		:param order: filter order; 0 (bypass), first- or second-order.

		:type gain: float; # TODO: Range?
		:param gain: Overall gain of low-pass filter

		"""
		impedence_gain = 1 if (self.relays_ch1 & RELAY_LOWZ) else 2
		atten_gain = 1 if (self.relays_ch1 & RELAY_LOWG) else 10
		gain_factor = impedence_gain * atten_gain * (10**(gain / 20.0)) * self._dac_gains()[0] / self._adc_gains()[0]

		coeff = 1 - 2*(math.pi * f_corner) /_LIA_CONTROL_FS

		self.lpf_int_ifb_gain = coeff
	
		self.lpf_int_i_gain = 1.0 - coeff

		if order == 0:
			self.filt_bypass1 = True
			self.filt_bypass2 = True
		if order == 1:
			self.filt_bypass1 = False
			self.filt_bypass2 = True
			self.slope = 1
		elif order == 2:
			self.filt_bypass1 = False
			self.filt_bypass2 = False
			self.slope = 2
		else:
			raise ValueOutOfRangeException("Order must be 0 (bypass), 1 or 2; not %d" % order)

		if order == 1:
			self.lpf_pidgain =  gain_factor
			self.input_gain = 1.0
		else:
			self.lpf_pidgain = math.sqrt(gain_factor)
			self.input_gain = 1.0

		self._recalc_offsets()


	@needs_commit
	def set_lo_output(self, amplitude, frequency, phase):
		"""
		Configure local oscillator output.

		This output is available on Channel 2 of the Moku:Lab.

		:type amplitude: float; [0.0, 2.0] Vpp
		:param amplitude: Amplitude

		:type frequency: float; [0, 200e6] Hz
		:param frequency: Frequency

		:type phase: float; [0, 360] deg
		:param phase: Phase
		"""
		_utils.check_parameter_valid('range', amplitude, allowed=[0, 2.0], desc="local oscillator amplitude", units="Vpp")
		_utils.check_parameter_valid('range', frequency, allowed=[0,200e6], desc="local oscillator frequency", units="Hz")
		_utils.check_parameter_valid('range', phase, allowed=[0,360], desc="local oscillator phase", units="degrees")

		self.sineout_amp = amplitude
		self.lo_frequency = frequency
		self.lo_phase = phase

	@needs_commit
	def set_monitor(self, ch, source):
		"""
		Select the point inside the lockin amplifier to monitor.

		There are two monitoring channels available, '1' and '2'; you can mux any of the internal
		monitoring points to either of these channels.

		The source is one of:
			- **none**: Disable monitor channel
			- **input1**, **input1**: Input Channel 1/2
			- **out**: Lock-in output
			- **aux**: Auxillary output
			- **demod**: Demodulation signal input to mixer
			- **i**, **q**: Mixer I and Q channels respectively.

		:type ch: int; [1,2]
		:param ch: Monitor channel number
		:type source: string; {'none','input1','input2','out','aux','demod','i','q'}
		:param source: Signal to monitor
		"""
		_utils.check_parameter_valid('set', ch, allowed=[1,2], desc="monitor channel")
		_utils.check_parameter_valid('set', source, allowed=['none', 'input1', 'input2', 'out', 'aux', 'demod', 'i','q'], desc="monitor source")

		sources = {
			'none'	: _LIA_MON_NONE,
			'input1': _LIA_MON_IN1,
			'input2': _LIA_MON_IN2,
			'out'	: _LIA_MON_OUT,
			'aux'	: _LIA_MON_AUX,
			'demod'	: _LIA_MON_DEMOD,
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
	'lpf_en':			(REG_LIA_ENABLES,		to_reg_bool(0),
												from_reg_bool(0)),

	'ch1_pid1_en':		(REG_LIA_ENABLES,		to_reg_bool(1),
												from_reg_bool(1)),

	'ch1_pid1_ien':		(REG_LIA_ENABLES,		to_reg_bool(3),
												from_reg_bool(3)),

	'ch1_pid1_pen':		(REG_LIA_ENABLES,		to_reg_bool(5),
												from_reg_bool(5)),

	'ch1_out_en': 		(REG_LIA_ENABLES,		to_reg_bool(8), 
												from_reg_bool(8)),

	'ch2_out_en': 		(REG_LIA_ENABLES, 		to_reg_bool(9), 
												from_reg_bool(9)),

	'lpf_den':			(REG_LIA_ENABLES,		to_reg_bool(10),
												from_reg_bool(10)),

	'pid1_ch1_den':		(REG_LIA_ENABLES,		to_reg_bool(11),
												from_reg_bool(11)),

	'ch1_pid1_bypass':	(REG_LIA_ENABLES,		to_reg_bool(13),
												from_reg_bool(13)),

	'ch1_signal_en':	(REG_LIA_ENABLES,		to_reg_bool(14),
												from_reg_bool(14)),

	'ch1_pid1_int_dc_pole':	(REG_LIA_ENABLES,	to_reg_bool(16),
												from_reg_bool(16)),

	'ch2_signal_en':	(REG_LIA_ENABLES,		to_reg_bool(17),
												from_reg_bool(17)),

	'ext_demod':		(REG_LIA_ENABLES, 		to_reg_bool(18),
												from_reg_bool(18)),

	'lo_PLL':			(REG_LIA_ENABLES, 		to_reg_bool(19),
												from_reg_bool(19)),

	'filt_bypass1':		(REG_LIA_ENABLES,		to_reg_bool(21),
												from_reg_bool(21)),

	'filt_bypass2':		(REG_LIA_ENABLES, 		to_reg_bool(22),
												from_reg_bool(22)),

	'pid_ch_select':	(REG_LIA_ENABLES, 		to_reg_bool(23),
												from_reg_bool(23)),

	'aux_select':		(REG_LIA_ENABLES, 		to_reg_unsigned(26, 2),
												from_reg_unsigned(26, 2)),

	'ch1_pid1_in_offset':	(REG_LIA_IN_OFFSET1,	to_reg_signed(16, 16, xform=lambda obj, x: x * obj._dac_gains()[0]),
													from_reg_signed(16, 16, xform=lambda obj, x: x / obj._dac_gains()[0])),

	'ch1_pid1_out_offset':	(REG_LIA_OUT_OFFSET1,	to_reg_signed(16, 16, xform=lambda obj, x: x * obj._dac_gains()[0]),
													from_reg_signed(16, 16, xform=lambda obj, x: x / obj._dac_gains()[0])),

	'ch1_out_offset': 		(REG_LIA_OUT_OFFSET1, 	to_reg_signed(0, 16, xform=lambda obj, x: x * obj._dac_gains()[0]),
												  	from_reg_signed(0, 16, xform=lambda obj, x: x / obj._dac_gains()[0])),

	'lpf_pidgain':		(REG_LIA_PIDGAIN1,			to_reg_signed(0, 32, xform=lambda obj, x : x * 2**15),
													from_reg_signed(0, 32, xform=lambda obj, x: x / 2**15)),

	'ch1_pid1_pidgain':		(REG_LIA_PIDGAIN2,		to_reg_signed(0, 32, xform=lambda obj, x : x * 2**15),
													from_reg_signed(0, 32, xform=lambda obj, x: x / 2**15)),

	'lpf_int_i_gain':	(REG_LIA_INT_IGAIN1,		to_reg_signed(0, 25, xform=lambda obj, x: x * _LIA_ID_GAINSCALE),
													from_reg_signed(0, 25, xform=lambda obj, x: x / _LIA_ID_GAINSCALE)),

	'ch1_pid1_int_i_gain':	(REG_LIA_INT_IGAIN2,	to_reg_signed(0, 25, xform=lambda obj, x: x * _LIA_ID_GAINSCALE),
													from_reg_signed(0, 25, xform=lambda obj, x: x / _LIA_ID_GAINSCALE)),

	'lpf_int_ifb_gain':(REG_LIA_INT_IFBGAIN1,		to_reg_signed(0, 25, xform=lambda obj, x: x*_LIA_ID_GAINSCALE),
													from_reg_signed(0, 25, xform=lambda obj, x: x / _LIA_ID_GAINSCALE)),

	'ch1_pid1_int_ifb_gain':(REG_LIA_INT_IFBGAIN2,	to_reg_signed(0, 25, xform=lambda obj, x: x*_LIA_ID_GAINSCALE),
													from_reg_signed(0, 25, xform=lambda obj, x: x / _LIA_ID_GAINSCALE)),

	'lpf_int_p_gain':	(REG_LIA_INT_PGAIN1,		to_reg_signed(0, 25, xform=lambda obj, x: x*_LIA_ID_GAINSCALE),
													from_reg_signed(0, 25, xform=lambda obj, x: x / _LIA_ID_GAINSCALE)),

	'ch1_pid1_int_p_gain':	(REG_LIA_INT_PGAIN2,	to_reg_signed(0, 25, xform=lambda obj, x: x*2**11),
													from_reg_signed(0, 25, xform=lambda obj, x: x / 2**11)),

	'gainstage_gain':	(REG_LIA_GAIN_STAGE,		to_reg_signed(0, 32, xform=lambda obj, x: x* 2**15),
													from_reg_signed(0, 32, xform=lambda obj, x: x / 2**15)),

	'ch1_pid1_diff_p_gain':	(REG_LIA_DIFF_PGAIN2,	to_reg_signed(0, 25, xform=lambda obj, x: x*_LIA_ID_GAINSCALE),
													from_reg_signed(0, 25, xform=lambda obj, x: x / _LIA_ID_GAINSCALE)),

	'ch1_pid1_diff_i_gain':	(REG_LIA_DIFF_IGAIN2,	to_reg_signed(0, 25, xform=lambda obj, x: x),
													from_reg_signed(0, 25, xform=lambda obj, x: x)),

	'ch1_pid1_diff_ifb_gain':(REG_LIA_DIFF_IFBGAIN2,	to_reg_signed(0, 25, xform=lambda obj, x: x*_LIA_ID_GAINSCALE),
														from_reg_signed(0, 25, xform=lambda obj, x: x / _LIA_ID_GAINSCALE)),

	'frequency_demod':	((REG_LIA_FREQDEMOD_H, REG_LIA_FREQDEMOD_L),
												to_reg_unsigned(0, 48, xform=lambda obj, x: x / _LIA_FREQSCALE),
												from_reg_unsigned(0, 48, xform=lambda obj, x: x * _LIA_FREQSCALE)),

	'phase_demod':		((REG_LIA_PHASEDEMOD_H, REG_LIA_PHASEDEMOD_L),
												to_reg_unsigned(0, 48, xform=lambda obj, x: x / (360.0 * _LIA_PHASESCALE)),
												from_reg_unsigned(0, 48, xform=lambda obj, x: x * (360.0 * _LIA_PHASESCALE))),

	'lo_frequency':		((REG_LIA_LO_FREQ_H, REG_LIA_LO_FREQ_L),
												to_reg_unsigned(0, 48, xform=lambda obj, x: x / _LIA_FREQSCALE),
												from_reg_unsigned(0, 48, xform=lambda obj, x: x * _LIA_FREQSCALE)),

	'lo_phase':			((REG_LIA_LO_PHASE_H, REG_LIA_LO_PHASE_L),
												to_reg_unsigned(0, 48, xform=lambda obj, x: x / (360.0 * _LIA_PHASESCALE)),
												to_reg_unsigned(0, 48, xform=lambda	obj, x: x * (360.0 * _LIA_PHASESCALE))),

	'monitor_select0':	(REG_LIA_MONSELECT,		to_reg_unsigned(0, 3, allow_set=[_LIA_MON_NONE, _LIA_MON_IN1, _LIA_MON_I, _LIA_MON_Q, _LIA_MON_OUT, _LIA_MON_AUX, _LIA_MON_IN2, _LIA_MON_DEMOD]),
												from_reg_unsigned(0, 3)),

	'monitor_select1':	(REG_LIA_MONSELECT,		to_reg_unsigned(3, 3, allow_set=[_LIA_MON_NONE, _LIA_MON_IN1, _LIA_MON_I, _LIA_MON_Q, _LIA_MON_OUT, _LIA_MON_AUX, _LIA_MON_IN2, _LIA_MON_DEMOD]),
												from_reg_unsigned(0, 3)),

	'sineout_amp':		(REG_LIA_SINEOUTAMP,	to_reg_signed(0, 16, xform=lambda obj, x: x / obj._dac_gains()[1]),
												from_reg_signed(0, 16, xform=lambda obj, x: x * obj._dac_gains()[1])),

	'aux_offset':	(REG_LIA_SINEOUTOFF,		to_reg_signed(16, 16, xform=lambda obj, x: x / obj._dac_gains()[1]),
												from_reg_signed(16, 16, xform=lambda obj, x: x * obj._dac_gains()[1])),

	'input_gain':		(REG_LIA_INPUT_GAIN,	to_reg_signed(0,32, xform=lambda obj, x: x * 2**15),
												from_reg_signed(0,32, xform=lambda obj, x: x / 2**15)),

	'bandwidth':		(REG_LIA_PM_BW1, 	to_reg_signed(0,5, xform=lambda obj, b: b),
											from_reg_signed(0,5, xform=lambda obj, b: b)),

	'lo_PLL_reset':		(REG_LIA_PM_RESET, 	to_reg_bool(31),
											from_reg_bool(31)),

	'lo_reacquire':		(REG_LIA_PM_REACQ, 	to_reg_bool(0),
											from_reg_bool(0)),

	'pid_select':	(REG_LIA_SIG_SELECT, 	to_reg_bool(0),
											from_reg_bool(0)),

	'pid_mode_select':	(REG_LIA_SIG_SELECT, to_reg_bool(1),
											 from_reg_bool(1)),

	'gain_select':	(REG_LIA_SIG_SELECT, 	to_reg_bool(2),
											from_reg_bool(2)),

	'gain_mode_select':	(REG_LIA_SIG_SELECT, to_reg_bool(3),
											 from_reg_bool(3)),

	'output_decimation':	(REG_LIA_PM_OUTDEC,	to_reg_unsigned(0,17),
												from_reg_unsigned(0,17)),

	'output_shift':			(REG_LIA_PM_OUTSHIFT, 	to_reg_unsigned(17,5),
													from_reg_unsigned(17,5)),

	'autoacquire':		(REG_LIA_PM_AUTOA1, to_reg_bool(0), 
											from_reg_bool(0))
}
