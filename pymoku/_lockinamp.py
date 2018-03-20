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

class LockInAmp(PIDController, _CoreOscilloscope):
	def __init__(self):
		super(LockInAmp, self).__init__()
		self._register_accessors(_lia_reg_hdl)

		self.id = 8
		self.type = "lockinamp"

		# Monitor samplerate
		self._input_samplerate = _LIA_INPUT_SMPS

		# Remember gains per channel
		self._g_aux = 1.0
		self._g_main = 1.0

		# Remembers monitor source choice
		self.monitor_a = None
		self.monitor_b = None
		self.demod_mode = None
		self.main_source = None
		self.aux_source = None

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
		self.set_demodulation('internal', 0, 90)
		self.set_outputs('i','demod',0,0)
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

		:type main: string; {'X','Y','I','Q','R','theta','offset','none'}
		:param main: Main output signal

		:type aux: string; {'Y','Q','theta','sine','demod','offset','none'}
		:param aux: Auxillary output signal

		:type main_offset: float; [-1.0,1.0] V
		:param main_offset: Main output offset

		:type aux_offset: float; [-1.0,1.0] V
		:param aux_offset: Auxillary output offset
		"""
		_utils.check_parameter_valid('string', main, desc="main output signal")
		_utils.check_parameter_valid('string', aux, desc="auxillary output signal")

		# Allow uppercase options
		main = main.lower()
		aux = aux.lower()

		_utils.check_parameter_valid('set', main, allowed=['x','y','i','q','r','theta','offset','none'], desc="main output signal")
		_utils.check_parameter_valid('set', aux, allowed=['y','q','theta','sine','demod','offset','none'], desc="auxillary output signal")

		lia_signals = ['x','y','r','theta','i','q']

		# Check for incompatible combinations here
		if ((main in ['x','i'] and aux=='theta') or \
			(main=='r' and aux in ['y','q']) or \
		 	(aux in lia_signals and main in ['y','q','theta'])):
			raise InvalidConfigurationException("Invalid output signal combination. Main - %s, Aux: %s" % (main, aux))

		# I hate having this check here and its complement when trying to set modulation below, ideally they'd
		# come in through a single interface
		if self.demod_mode == 'external' and (
		  aux in lia_signals or main in ['r', 'theta']):
			raise InvalidConfigurationException("Can't use quadrature-related outputs when using external demodulation without a PLL.")

		# Set up main output
		self._set_main_out('ch1' if main in lia_signals else main, offset=main_offset)

		# Set up aux output
		self._set_aux_out('ch2' if aux in lia_signals else aux, offset=aux_offset)

		# Set gain stage/pid stage input signals
		# Assume PID on main channel for now
		# Only set the ones that care about a lockin signal

	def _signal_select_num(sig):
		signal_select_map = [(0,'i'),(0,'x'),(1,'q'),(1,'y'),(2,'r'),(3,'theta')]
		return [i for i,x in signal_select_map if x==sig][0]

		# If the PID is moved, the signals have to be re-selected to be a gain stage or otherwise
		self.pid_signal_select = _signal_select_num(main if self.pid_ch_select==0 else aux)
		self.gain_signal_select = _signal_select_num(main if self.pid_ch_select==0 else aux)

		# Change which lock-in signals are passed into gain/pid stage
		if main in lia_signals:
			if self.pid_ch_select == 0:
				self.pid_signal_select = _signal_select_num(main)
			else:
				self.gain_signal_select = _signal_select_num(main)

		if aux in lia_signals:
			if self.pid_ch_select == 1:
				self.pid_signal_select = _signal_select_num(main)
			else:
				self.gain_signal_select = _signal_select_num(main)

	def _set_main_out(self, sel='ch1', offset=0.0):
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

		self.main_offset = offset

		self.main_source = sel

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

	def _set_aux_out(self, auxsel, offset=0.0):
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

		self.aux_offset = offset

		# Turns on the auxillary output for most cases
		self.ch2_out_en = True
		self.ch2_signal_en = True

		# Unfortunately need to remember this source so we can check for invalid output configuration
		# when selecting demod source
		self.aux_source = auxsel

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
	def set_pid_by_frequency(self, lia_ch, kp=1, i_xover=None, d_xover=None, si=None, sd=None, in_offset=0, out_offset=0):
		"""
		Set which lock-in channel the PID is on and configure it using frequency domain parameters.

		:type ch: string; {'main','aux'}
		:param ch: Lock-in channel name to put PID on

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
		self._set_pid_channel(lia_ch)
		g, kp, ki, kd, kii, si, sd = self._calculate_gains_by_frequency(kp, i_xover, d_xover, None, si, sd)
		self._set_by_gain(1, g, kp, ki, kd, 0, si, sd, in_offset, out_offset, touch_ii=False)

	@needs_commit
	def set_pid_by_gain(self, lia_ch, g, kp=1.0, ki=0, kd=0, si=None, sd=None, in_offset=0, out_offset=0):
		"""
		Set which lock-in channel the PID is on and configure it using gain parameters.

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
		self._set_pid_channel(lia_ch)
		self._set_by_gain(1, g, kp, ki, kd, 0, si, sd, in_offset, out_offset, touch_ii=False)

	set_by_gain = set_pid_by_gain
	set_by_frequency = set_pid_by_frequency

	def _set_pid_channel(self, lia_ch):
		# Helper function which switches connections to gain stage and PID

		_utils.check_parameter_valid('set', lia_ch, allowed=['main','aux'], desc="PID channel")

		# Register value translation
		new_pid_ch_select = (lia_ch=='aux')

		# Check if the PID has swapped channels
		if new_pid_ch_select != self.pid_ch_select:

			# Update the PID output channel
			self.pid_ch_select = new_pid_ch_select

			# Switch the input signal select of PID and Gain stage
			old_pid_input_sig = self.pid_signal_select
			self.pid_signal_select = self.gain_signal_select
			self.gain_signal_select = old_pid_input_sig

		# Restore the gain of the non-PID channel
		if lia_ch == 'main':
			self.gainstage_gain = self._g_aux
		else:
			self.gainstage_gain = self._g_main

	@needs_commit
	def set_gain(self, lia_ch, g):
		"""
			Set the output gain for the specified lock-in channel.

			If you have a PID on the specified channel, it will be configured to a P with the specified gain.

			:type lia_ch: string; {'main','aux'}
			:param lia_ch: Channel name

			:type g: float; [0, 2^16 - 1]
			:param g: Gain
		"""
		_utils.check_parameter_valid('set', lia_ch, allowed=['main','aux'], desc="lock-in channel")
		_utils.check_parameter_valid('range', g, allowed=[0, 2**16 - 1], desc="gain")

		if lia_ch == 'aux':
			# Track gain value for the main channel
			self._g_aux = g
			# If PID is on this channel, treat it like a gain stage
			if self.pid_ch_select == 1:
				self.set_pid_by_gain('aux',g)
			else:
				self.gainstage_gain = g
		elif lia_ch == 'main':
			# Track gain value for the main channel
			self._g_main = g
			# If PID is on this channel, treat it like a gain stage
			if self.pid_ch_select == 0:
				self.set_pid_by_gain('main',g)
			else:
				self.gainstage_gain = g
		else:
			raise Exception("Invalid LIA channel.")

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
		self.lpf_en = 1
		self.lpf_int_i_en = 1
		self.lpf_int_dc_pole = 0
		self.lpf_pen = 0
		self.lpf_diff_d_en = 0
		self.lpf_den = 0

		# It is strictly possible for this filter to have gain separate from the output
		# gain. It's almost always right to leave this at 1 and manipulate the output gain
		gain = 1

		impedence_gain = 1 if (self.relays_ch1 & RELAY_LOWZ) else 2
		atten_gain = 1 if (self.relays_ch1 & RELAY_LOWG) else 10
		gain_factor = impedence_gain * atten_gain * gain / (4.4) * self._dac_gains()[0] / self._adc_gains()[0]

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

		self.input_gain = 1.0
		self.lpf_pidgain = gain_factor if order == 1 else math.sqrt(gain_factor)

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

	'ch1_pid1_in_offset':	(REG_LIA_IN_OFFSET1,	to_reg_signed(16, 16, xform=lambda obj, x: x * obj._dac_gains()[0]),
													from_reg_signed(16, 16, xform=lambda obj, x: x / obj._dac_gains()[0])),

	'ch1_pid1_out_offset':	(REG_LIA_OUT_OFFSET1,	to_reg_signed(16, 16, xform=lambda obj, x: x * obj._dac_gains()[0]),
													from_reg_signed(16, 16, xform=lambda obj, x: x / obj._dac_gains()[0])),

	'main_offset': 		(REG_LIA_OUT_OFFSET1, 	to_reg_signed(0, 16, xform=lambda obj, x: x * obj._dac_gains()[0]),
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
