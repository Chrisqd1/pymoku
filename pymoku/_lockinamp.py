import math, string
import logging

from pymoku._instrument import *
from pymoku._oscilloscope import _CoreOscilloscope, VoltsData
from pymoku._pid_controller import PIDController
from . import _instrument
from . import _utils

log = logging.getLogger(__name__)

REG_LIA_PM_BW1 			= 90
REG_LIA_PM_AUTOA1 		= 91
REG_LIA_PM_REACQ		= 92
REG_LIA_PM_RESET		= 93
REG_LIA_PM_OUTDEC 		= 94
REG_LIA_PM_OUTSHIFT 	= 94
REG_LIA_SIG_SELECT		= 95

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

_LIA_INPUT_SMPS = ADC_SMP_RATE

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

_LIA_SIGNALS = ['x','y','r','theta']

class LockInAmp(PIDController, _CoreOscilloscope):
	def __init__(self):
		super(LockInAmp, self).__init__()
		self._register_accessors(_lia_reg_hdl)

		self.id = 8
		self.type = "lockinamp"

		# Monitor samplerate
		self._input_samplerate = _LIA_INPUT_SMPS

		# Remember some user settings for when swapping channels
		self.monitor_a = None
		self.monitor_b = None
		self.demod_mode = None
		self.main_source = None
		self.aux_source = None
		self._pid_channel = None
		self._lo_amp = 1.0

	@needs_commit
	def set_defaults(self):
		""" Reset the lockinamp to sane defaults. """

		# Avoid calling the PID controller set_defaults
		_CoreOscilloscope.set_defaults(self)

		# Configure the low-pass filter
		self.set_filter(1e3, 1)
		self.set_gain('aux',1.0)
		self.set_pid_by_gain('main',1.0)
		self.set_lo_output(0.5,1e6,0)
		self.set_monitor('a', 'in1')
		self.set_monitor('b', 'main')
		self.set_demodulation('internal', 0)
		self.set_outputs('x','demod')
		self.set_input_gain(0)

	@needs_commit
	def set_input_gain(self, gain=0):
		"""
		Set the main input gain (Input Channel 1).

		:type gain: int; {-20, 0, 24, 48} dB
		:param gain: Input gain

		"""
		_utils.check_parameter_valid('set', gain, allowed=[-20,0,24,48], desc="main input gain", units="dB")
		front_end_setting = self.get_frontend(1)

		if gain == 0:
			self.input_gain_select = 0
			self.set_frontend(1, fiftyr = front_end_setting[0], atten=False, ac = front_end_setting[2])
		elif gain == 24:
			self.input_gain_select = 1
			self.set_frontend(1, fiftyr = front_end_setting[0], atten=False, ac = front_end_setting[2])
		elif gain == 48:
			self.input_gain_select = 2
			self.set_frontend(1, fiftyr = front_end_setting[0], atten=False, ac = front_end_setting[2])
		elif gain == -20:
			self.input_gain_select = 0
			self.set_frontend(1, fiftyr = front_end_setting[0], atten=True, ac = front_end_setting[2])
		else:
			raise Exception("Invalid input gain value.")

	@needs_commit
	def set_outputs(self, main, aux, main_offset=0.0, aux_offset=0.0):
		"""
		Configures the main (Channel 1) and auxillary (Channel 2) output signals of the Lock-In.

		.. note::
		  When 'external' demodulation is used (that is, without a PLL), the Lock-in Amplifier doesn't know the frequency and therefore
		  can't form the quadrature for full I/Q demodulation. This in turn means it can't distinguish I from Q, X from Y,
		  or form R/Theta. This limits the choices for signals that can be output on the AUX channel to ones not from the
		  Lock-in logic (e.g. demodulation source, auxilliary sine wave etc).

		  An exception will be raised if you attempt to set the auxilliary channel to view aa signal from the Lock-in logic while
		  external demodulation is enabled.

		:type main: string; {'x', 'y', 'r', 'theta', 'offset', 'none'}
		:param main: Main output signal

		:type aux: string; {'x', 'y', 'r', theta', 'sine', 'demod', 'offset', 'none'}
		:param aux: Auxillary output signal

		:type main_offset: float; [-1.0, 1.0] V
		:param main_offset: Main output offset

		:type aux_offset: float; [-1.0, 1.0] V
		:param aux_offset: Auxillary output offset
		"""
		_utils.check_parameter_valid('string', main, desc="main output signal")
		_utils.check_parameter_valid('string', aux, desc="auxillary output signal")

		# Allow uppercase options
		main = main.lower()
		aux = aux.lower()

		_utils.check_parameter_valid('set', main, allowed=['x','y','r','theta','offset','none'], desc="main output signal")
		_utils.check_parameter_valid('set', aux, allowed=['x', 'y','r','theta','sine','demod','offset','none'], desc="auxillary output signal")

		# I hate having this check here and its complement when trying to set modulation below, ideally they'd
		# come in through a single interface
		if self.demod_mode == 'external' and (
		  aux in _LIA_SIGNALS or main in ['r', 'theta']):
			raise InvalidConfigurationException("Can't use quadrature-related outputs when using external demodulation without a PLL.")

		# Main output enables
		self.main_offset = main_offset
		self.main_source = main
		self.ch1_signal_en = main in _LIA_SIGNALS
		self.ch1_out_en = not (main == 'none')

		# Auxillary output enables
		self.aux_offset = aux_offset
		self.aux_source = aux
		self.ch2_signal_en = aux in (_LIA_SIGNALS + ['sine','demod'])
		self.ch2_out_en = not (aux == 'none')
		self.aux_select = 1 if aux in (_LIA_SIGNALS) else (2 if aux == 'demod' else 0) # Defaults to local oscillator i.e. 'sine'

		# PID/Gain stage selects are updated on commit

	def _update_pid_gain_selects(self):
		# Update the PID/Gain signal inputs / channel select ouputs to match the set main/aux source signals

		def _signal_select(sig):
			return 0 if not(sig in _LIA_SIGNALS) else [i for i,x in enumerate(_LIA_SIGNALS) if x==sig][0]

		if self._pid_channel=='main':
			self.pid_sig_select = _signal_select(self.main_source)
			self.pid_ch_select = 0
			self.gain_sig_select = _signal_select(self.aux_source)
		else:
			self.pid_sig_select = _signal_select(self.aux_source)
			self.pid_ch_select = 1
			self.gain_sig_select = _signal_select(self.main_source)

	@needs_commit
	def set_pid_by_frequency(self, lia_ch, kp=1, i_xover=None, d_xover=None, si=None, sd=None, in_offset=0, out_offset=0):
		"""
		Set which lock-in channel the PID is on and configure it using frequency domain parameters.

		This sets the gain stage to be on the opposite channel.

		:type ch: string; {'main','aux'}
		:param ch: Lock-in channel name to put PID on. 

		:type kp: float; [-1e3,1e3]
		:param kp: Proportional gain factor

		:type i_xover: float; [1e-3,1e6] Hz
		:param i_xover: Integrator crossover frequency

		:type d_xover: float; [1,10e6] Hz
		:param d_xover: Differentiator crossover frequency

		:type ii_xover: float; [1, 1e6] Hz
		:param ii_xover: Second integrator crossover frequency

		:type si: float; float; [-1e3,1e3]
		:param si: Integrator gain saturation

		:type sd: float; [-1e3,1e3]
		:param sd: Differentiator gain saturation

		:type in_offset: float; [-1.0,1.0] V
		:param in_offset: Input signal offset

		:type out_offset: float; [-1.0, 1.0] V
		:type out_offset: Output signal offset

		:raises InvalidConfigurationException: if the configuration of PID gains is not possible.
		"""
		self._pid_channel = lia_ch
		g, kp, ki, kd, kii, si, sd = self._calculate_gains_by_frequency(kp, i_xover, d_xover, None, si, sd)
		self._set_by_gain(1, g, kp, ki, kd, 0, si, sd, in_offset, out_offset, touch_ii=False)

	@needs_commit
	def set_pid_by_gain(self, lia_ch, g, kp=1.0, ki=0, kd=0, si=None, sd=None, in_offset=0, out_offset=0):
		"""
		Set which lock-in channel the PID is on and configure it using gain parameters.

		This sets the gain stage to be on the opposite channel.

		:type ch: string; {'main','aux'}
		:param ch: Lock-in channel name to put PID on

		:type g: float; [0,2^16 - 1]
		:param g: Gain

		:type kp: float; [-1e3,1e3]
		:param kp: Proportional gain factor

		:type ki: float;
		:param ki: Integrator gain factor

		:type kd: float;
		:param kd: Differentiator gain factor

		:type kii: float;
		:param kii: Second integrator gain factor

		:type si: float; float; [-1e3,1e3]
		:param si: Integrator gain saturation

		:type sd: float; [-1e3,1e3]
		:param sd: Differentiator gain saturation

		:type in_offset: float; [-1.0,1.0] V
		:param in_offset: Input signal offset

		:type out_offset: float; [-1.0, 1.0] V
		:type out_offset: Output signal offset

		:raises InvalidConfigurationException: if the configuration of PID gains is not possible.
		"""
		self._pid_channel = lia_ch
		self._set_by_gain(1, g, kp, ki, kd, 0, si, sd, in_offset, out_offset, touch_ii=False)

	# Overload the PID API functions 
	set_by_gain = set_pid_by_gain
	set_by_frequency = set_pid_by_frequency

	@needs_commit
	def set_gain(self, lia_ch, g):
		"""
		Sets the gain stage to be on the specified lock-in channel, and configures its gain.

		This sets the PID stage to be on the opposite channel.

		:type lia_ch: string; {'main','aux'}
		:param lia_ch: Channel name

		:type g: float; [0, 2^16 - 1]
		:param g: Gain
		"""
		_utils.check_parameter_valid('set', lia_ch, allowed=['main','aux'], desc="lock-in channel")
		_utils.check_parameter_valid('range', g, allowed=[0, 2**16 - 1], desc="gain")

		# Store selected PID channel locally. Signal select regs are updated on commit.
		self._pid_channel = 'main' if lia_ch=='aux' else 'aux'

		# Set the desired gain
		self.gainstage_gain = g / self._dac_gains()[0 if lia_ch == 'main' else 1] / 31.25 / 2.0**12

	@needs_commit
	def set_demodulation(self, mode, frequency=1e6, phase=0):
		"""
		Configure the demodulation stage.

		The mode is one of:
			- **internal** : for an internally set local oscillator
			- **external** : to directly use an external signal for demodulation (Note: Q is not selectable in this mode)
			- **external_pll** : to use an external signal for demodulation after running it through an internal PLL.

		.. note::
		  When 'external' is used (that is, without a PLL), the Lock-in Amplifier doesn't know the frequency and therefore
		  can't form the quadrature for full I/Q demodulation. This in turn means it can't distinguish I from Q, X from Y,
		  or form R/Theta. This limits the choices for signals that can be output on the Main and AUX channels to ones not
		  formed from the quadrature signal.

		  An exception will be raised if you attempt to set the demodulation to 'external' while viewing one of these signals.

		:type mode: string; {'internal', 'external', 'external_pll'}
		:param mode: Demodulation mode

		:type frequency: float; [0, 200e6] Hz
		:param frequency: Internal demodulation signal frequency (ignored for all 'external' modes)

		:type phase: float; [0, 360] deg
		:param phase: Internal demodulation signal phase (ignored in 'external' mode)

		"""
		_utils.check_parameter_valid('range', frequency, allowed=[0,200e6], desc="demodulation frequency", units="Hz")
		_utils.check_parameter_valid('range', phase, allowed=[0,360], desc="demodulation phase", units="degrees")
		_utils.check_parameter_valid('set', mode, allowed=['internal', 'external', 'external_pll'] )

		if mode == 'external' and (
		  self.aux_source == 'ch2' or self.main_source in ['r', 'theta']):
			raise InvalidConfigurationException("Can't use external demodulation source without a PLL with quadrature-related outputs.")

		self.autoacquire = 1
		self.bandwidth = 0
		self.lo_PLL_reset = 0
		self.lo_reacquire = 0

		if mode == 'internal':
			self.ext_demod = 0
			self.lo_PLL = 0
			self.frequency_demod = frequency
			self.phase_demod = phase
			self.demod_mode = mode
		elif mode == 'external':
			self.ext_demod = 1
			self.lo_PLL = 0
			self.demod_mode = mode
		elif mode == 'external_pll':
			self.ext_demod = 0
			self.lo_PLL = 1
			self.lo_reacquire = 1
			self.phase_demod = phase
			self.demod_mode = mode
		else :
			# Should not happen
			raise ValueOutOfRangeException('Demodulation mode must be one of "internal", "external" or "external_pll", not %s', mode)

	@needs_commit
	def set_filter(self, f_corner, order):
		"""
		Set the low-pass filter parameters.

		:type f_corner: float
		:param f_corner: Corner frequency of the low-pass filter (Hz)

		:type order: int; [0, 1, 2]
		:param order: filter order; 0 (bypass), first- or second-order.

		"""
		# Ensure the right parts of the filter are enabled
		self.lpf_den = 0

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

		self.input_gain = 1.0

		gain_factor = 2.0**12 * self._adc_gains()[0] / (10.0 if self.get_frontend(1)[1] else 1.0)
		self.lpf_pidgain = gain_factor if order == 1 else math.sqrt(gain_factor)

		ifb = 1.0 - 2.0*(math.pi * f_corner)/_LIA_CONTROL_FS
		self.lpf_int_ifb_gain = ifb
		self.lpf_int_i_gain = 1.0 - ifb

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

		# The sine amplitude register also scales the LIA signal outputs (eek!), so it must only be updated
		# if the auxillary output is set to a non-filtered signal.
		self._lo_amp = amplitude
		self.lo_frequency = frequency
		self.lo_phase = phase

	@needs_commit
	def set_monitor(self, monitor_ch, source):
		"""
		Select the point inside the lockin amplifier to monitor.

		There are two monitoring channels available, 'A' and 'B'; you can mux any of the internal
		monitoring points to either of these channels.

		The source is one of:
			- **none**: Disable monitor channel
			- **in1**, **in2**: Input Channel 1/2
			- **main**: Lock-in output (Output Channel 1)
			- **aux**: Auxillary output (Output Channel 2)
			- **demod**: Demodulation signal input to mixer
			- **i**, **q**: Mixer I and Q channels respectively.

		:type monitor_ch: string; {'A','B'}
		:param monitor_ch: Monitor channel
		:type source: string; {'none','in1','in2','main','aux','demod','i','q'}
		:param source: Signal to monitor
		"""
		_utils.check_parameter_valid('string', monitor_ch, desc="monitor channel")
		_utils.check_parameter_valid('string', source, desc="monitor signal")

		monitor_ch = monitor_ch.lower()
		source = source.lower()

		_utils.check_parameter_valid('set', monitor_ch, allowed=['a','b'], desc="monitor channel")
		_utils.check_parameter_valid('set', source, allowed=['none', 'in1', 'in2', 'main', 'aux', 'demod', 'i','q'], desc="monitor source")

		sources = {
			'none'	: _LIA_MON_NONE,
			'in1'	: _LIA_MON_IN1,
			'in2'	: _LIA_MON_IN2,
			'main'	: _LIA_MON_OUT,
			'aux'	: _LIA_MON_AUX,
			'demod'	: _LIA_MON_DEMOD,
			'i'		: _LIA_MON_I,
			'q'		: _LIA_MON_Q,
		}

		if monitor_ch == 'a':
			self.monitor_a = source
			self.monitor_select0 = sources[source]
		elif monitor_ch == 'b':
			self.monitor_b = source
			self.monitor_select1 = sources[source]
		else:
			raise ValueOutOfRangeException("Invalid channel %d", monitor_ch)

	@needs_commit
	def set_trigger(self, source, edge, level, hysteresis=False, hf_reject=False, mode='auto'):
		"""
			Set the trigger for the monitor signals. This can be either of the input channel signals
			or monitor channel signals.

			:type source: string; {'in1','in2','A','B','ext'}
			:param source: Trigger channel

			:type edge: string, {'rising','falling','both'}
			:param edge: Which edge to trigger on.

			:type level: float, [-10.0, 10.0] volts
			:param level: Trigger level

			:type hysteresis: bool
			:param hysteresis: Enable Hysteresis around trigger point.

			:type hf_reject: bool
			:param hf_reject: Enable high-frequency noise rejection

			:type mode: string, {'auto', 'normal'}
			:param mode: Trigger mode.
		"""
		_utils.check_parameter_valid('string', source, desc="trigger source")
		source = source.lower()
		_utils.check_parameter_valid('set', source, allowed=['in1','in2','a','b','ext'], desc="trigger source")

		# Translate the LIA trigger sources to Oscilloscope sources
		_str_to_osc_trig_source = {
			'a' : 'in1',
			'b' : 'in2',
			'in1' : 'out1',
			'in2' : 'out2',
			'ext' : 'ext'
		}

		source = _utils.str_to_val(_str_to_osc_trig_source, source, 'trigger source')

		super(LockInAmp, self).set_trigger(source=source, edge=edge, level=level, hysteresis=hysteresis, hf_reject=hf_reject, mode=mode)

	def _calculate_scales(self):
		# This calculates scaling factors for the internal Oscilloscope frames
		scales = super(LockInAmp, self)._calculate_scales()

		# Change the scales we care about
		deci_gain = self._deci_gain()
		atten1 = self.get_frontend(1)
		atten2 = self.get_frontend(2)

		def _demod_mode_to_gain(mode):
			if mode == 'internal' or 'external_pll':
				return 1.0/deci_gain/2**11
			elif mode == 'external':
				return 1.0/deci_gain/scales['gain_adc2']/(10.0 if atten else 1.0)
			else:
				return 1.0

		monitor_source_gains = {
			'none'	: 1.0,
			'in1'	: scales['gain_adc1']*(10.0 if atten1 else 1.0), # Undo range scaling
			'in2'	: scales['gain_adc2']*(10.0 if atten2 else 1.0),
			'main'	: scales['gain_dac1']*(2**4), # 12bit ADC - 16bit DAC
			'aux'	: scales['gain_dac2']*(2**4),
			'demod'	: _demod_mode_to_gain(self.demod_mode),
			'i'		: scales['gain_adc1']*(10.0 if atten1 else 1.0),
			'q'		: scales['gain_adc1']*(10.0 if atten1 else 1.0)
		}

		# Replace scaling factors depending on the monitor signal source
		scales['scale_ch1'] = 1.0 if not self.monitor_a else monitor_source_gains[self.monitor_a]
		scales['scale_ch2'] = 1.0 if not self.monitor_b else monitor_source_gains[self.monitor_b]

		return scales

	def _update_dependent_regs(self, scales):
		super(LockInAmp, self)._update_dependent_regs(scales)

		# Update PID/Gain stage input/output selects as they may have swapped channels
		self._update_pid_gain_selects()

		if self.aux_source in _LIA_SIGNALS:
			# If aux is set to a filtered signal, set this to maximum gain setting.
			# If you don't do this, the filtered signal is scaled by < 1.0.
			self.sineout_amp = 2**16 - 1
		else:
			# If aux is set to LO, set the sine amplitude as desired. 
			# Only ever output on Channel 2.
			self.sineout_amp = self._lo_amp / self._dac_gains()[1]

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

	'input_gain_select': (REG_LIA_ENABLES,		to_reg_unsigned(28, 2),
												from_reg_unsigned(28,2)),

	'ch1_pid1_in_offset':	(REG_LIA_IN_OFFSET1,	to_reg_signed(16, 16, xform=lambda obj, x: x / obj._dac_gains()[0]),
													from_reg_signed(16, 16, xform=lambda obj, x: x * obj._dac_gains()[0])),

	'ch1_pid1_out_offset':	(REG_LIA_OUT_OFFSET1,	to_reg_signed(16, 16, xform=lambda obj, x: x / obj._dac_gains()[0]),
													from_reg_signed(16, 16, xform=lambda obj, x: x * obj._dac_gains()[0])),

	'main_offset': 		(REG_LIA_OUT_OFFSET1, 	to_reg_signed(0, 16, xform=lambda obj, x: x / obj._dac_gains()[0]),
												  	from_reg_signed(0, 16, xform=lambda obj, x: x * obj._dac_gains()[0])),

	'lpf_pidgain':		(REG_LIA_PIDGAIN1,			to_reg_signed(0, 32, xform=lambda obj, x : x * 2**15),
													from_reg_signed(0, 32, xform=lambda obj, x: x / 2**15)),

	'ch1_pid1_pidgain':		(REG_LIA_PIDGAIN2,		to_reg_signed(0, 32, xform=lambda obj, x : x),
													from_reg_signed(0, 32, xform=lambda obj, x: x)),

	'lpf_int_i_gain':	(REG_LIA_INT_IGAIN1,		to_reg_signed(0, 25, xform=lambda obj, x: x * _LIA_ID_GAINSCALE),
													from_reg_signed(0, 25, xform=lambda obj, x: x / _LIA_ID_GAINSCALE)),

	'ch1_pid1_int_i_gain':	(REG_LIA_INT_IGAIN2,	to_reg_signed(0, 25, xform=lambda obj, x: x),
													from_reg_signed(0, 25, xform=lambda obj, x: x)),

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

	'sineout_amp':		(REG_LIA_SINEOUTAMP,	to_reg_unsigned(0, 16, xform=lambda obj, x: x),
												from_reg_unsigned(0, 16, xform=lambda obj, x: x)),

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

	'pid_sig_select':	(REG_LIA_SIG_SELECT, to_reg_unsigned(0,2),
											from_reg_unsigned(0,2)),

	'gain_sig_select':	(REG_LIA_SIG_SELECT, to_reg_unsigned(2,2),
											 from_reg_unsigned(2,2)),

	'output_decimation':	(REG_LIA_PM_OUTDEC,	to_reg_unsigned(0,17),
												from_reg_unsigned(0,17)),

	'output_shift':			(REG_LIA_PM_OUTSHIFT, 	to_reg_unsigned(17,5),
													from_reg_unsigned(17,5)),

	'autoacquire':		(REG_LIA_PM_AUTOA1, to_reg_bool(0),
											from_reg_bool(0))
}
