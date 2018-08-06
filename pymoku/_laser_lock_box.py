
import math
import logging

from pymoku._instrument import *
from pymoku._oscilloscope import _CoreOscilloscope, VoltsData
from . import _instrument
from . import _frame_instrument
from . import _utils
from ._pid import PID
from ._sweep_generator import SweepGenerator
from ._iir_block import IIRBlock

log = logging.getLogger(__name__)

REGBASE_LLB_DEMOD			= 79
REGBASE_LLB_SCAN			= 88
REGBASE_LLB_AUX_SINE		= 97

REG_LLB_MON_SEL				= 75
REG_LLB_RATE_SEL			= 76
REG_LLB_SCALE				= 77

REGBASE_LLB_IIR				= 28

REGBASE_LLB_PID1			= 110
REGBASE_LLB_PID2			= 119

_LLB_PHASESCALE				= 2**64 / 360.0
_LLB_FREQSCALE				= 2**64 / 1e9
_LLB_SWEEP_WTYPE_SAWTOOTH	= 2
_LLB_SWEEP_MAX_STOP			= 2**64 - 1
_LLB_HIGH_RATE				= 0
_LLB_LOW_RATE				= 1

_LLB_COEFFICIENT_WIDTH		= 24

_LLB_TRIG_SRC_CH1			= 0
_LLB_TRIG_SRC_CH2			= 1
_LLB_TRIG_SRC_EXT			= 2

_LLB_MON_ERROR 				= 1
_LLB_MON_PID_FAST			= 2
_LLB_MON_PID_SLOW			= 3
_LLB_MON_IN1				= 4
_LLB_MON_IN2				= 5
_LLB_MON_OUT1				= 6
_LLB_MON_OUT2				= 7
_LLB_MON_SCAN				= 8
_LLB_MON_LO 				= 9
_LLB_MON_AUX				= 10
_LLB_MON_SLOW_SCAN			= 11

_LLB_SOURCE_A		= 0
_LLB_SOURCE_B		= 1
_LLB_SOURCE_IN1		= 2
_LLB_SOURCE_IN2		= 3
_LLB_SOURCE_EXT		= 4

_LLB_OSC_SOURCES = {
	'a' : _LLB_SOURCE_A,
	'b' : _LLB_SOURCE_B,
	'in1' : _LLB_SOURCE_IN1,
	'in2' : _LLB_SOURCE_IN2,
	'ext' : _LLB_SOURCE_EXT
}

_ADC_DEFAULT_CALIBRATION = 3750.0
_DAC_DEFAULT_CALIBRATION = _ADC_DEFAULT_CALIBRATION * 2.0**3

class LaserLockBox(_CoreOscilloscope):
	def __init__(self):
		super(LaserLockBox, self).__init__()
		self._register_accessors(_llb_reg_hdl)

		self.id = 16
		self.type = "laserlockbox"

		self._set_source(1, _LLB_SOURCE_A)
		self._set_source(2, _LLB_SOURCE_B)

		self.monitor_a = 'in1'
		self.monitor_b = 'in2'

		self.fast_fs = 31.25e6
		self.slow_fs = 31.25e6

		self.fast_pid = PID(self, reg_base = REGBASE_LLB_PID1, fs=self.fast_fs)
		self.slow_pid = PID(self, reg_base = REGBASE_LLB_PID2, fs=self.slow_fs)

		self.demod_sweep = SweepGenerator(self, reg_base = REGBASE_LLB_DEMOD)
		self.scan_sweep = SweepGenerator(self, reg_base = REGBASE_LLB_SCAN)
		self.aux_sine_sweep = SweepGenerator(self, reg_base = REGBASE_LLB_AUX_SINE)		
		self.iir_filter = IIRBlock(self, reg_base=REGBASE_LLB_IIR, num_stages = 1, gain_frac_width = 9, coeff_frac_width = 23, use_mmap = False)

	@needs_commit
	def set_defaults(self):
		super(LaserLockBox, self).set_defaults()
		self.set_sample_rate('high')

		self.set_local_oscillator(10e6, 0)

		# self.scan_sweep.step = 0
		# self.scan_sweep.stop = 2**64 -1
		# self.scan_sweep.duration = 0
		# self.scan_sweep.waveform = 2
		# self.scan_sweep.start = 0
		# self.scan_sweep.wait_for_trig = False
		# self.scan_sweep.hold_last = False

		# self.aux_sine_sweep.step = 0
		# self.aux_sine_sweep.stop = 2**64 -1
		# self.aux_sine_sweep.duration = 0
		# self.aux_sine_sweep.waveform = 2
		# self.aux_sine_sweep.start = 0
		# self.aux_sine_sweep.wait_for_trig = False
		# self.aux_sine_sweep.hold_last = False
		# self.set_pid_by_gain(1)

		default_filt_coeff = 	[[1.0],
						# [1.0, 0.0346271318590754, -0.0466073336600009, 0.0346271318590754, 1.81922686243757, -0.844637126033068]]
						[1, 1, 0, 0, 0, 0]]
		self.set_filter_coeffs(default_filt_coeff)
		self.set_local_oscillator(10e6 ,0)

		self._set_scale()
		self.MuxDec = 0
		self.MuxFast = 0
		self.MuxInt = 2
		self.TrigPort2 = 0


	def _update_dependent_regs(self, scales):
		super(LaserLockBox, self)._update_dependent_regs(scales)
		self._set_scale()
		
	@needs_commit
	def _set_scale(self):
		
		self._fast_scale = self._adc_gains()[0] / self._dac_gains()[0] / 2**3
		self._slow_scale = self._adc_gains()[0] / self._dac_gains()[1] / 2**3


	@needs_commit
	def set_filter_coeffs(self, filt_coeffs):
		"""
		Configure the filter coefficients in the IIR filter.

		:type filt_coeffs: array;
		:param filt_coeffs: array containg SOS filter coefficients.
		"""
		self.iir_filter.write_coeffs(filt_coeffs)

	@needs_commit
	def set_pid_by_gain(self, pid_block, g=1, kp=1, ki=0, kd=0, si=None, sd=None):
		"""
		Configure the selected PID controller using gain coefficients.

		:type ch: int; [1,2]
		:param ch: Channel of the PID controller to be configured.

		:type g: float; [0,2^16 - 1]
		:param g: Gain

		:type kp: float; [-1e3,1e3]
		:param kp: Proportional gain factor

		:type ki: float;
		:param ki: Integrator gain factor

		:type kd: float;
		:param kd: Differentiator gain factor

		:type si: float; float; [-1e3,1e3]
		:param si: Integrator gain saturation

		:type sd: float; [-1e3,1e3]
		:param sd: Differentiator gain saturation

		:raises InvalidConfigurationException: if the configuration of PID gains is not possible.
		"""
		pid_array = [self.fast_pid, self.slow_pid]

		pid_array[pid_block -1].set_reg_by_gain(g, kp, ki, kd, si, sd)
		pid_array[pid_block -1].gain = pid_array[pid_block -1].gain / self._dac_gains()[pid_block-1]

	@needs_commit
	def set_pid_enable(self, pid_block, en=True):
		pid_array = [self.fast_pid, self.slow_pid]
		pid_array[pid_block-1].enable = en

	@needs_commit
	def set_pid_bypass(self, pid_block, bypass = False):
		pid_array = [self.fast_pid, self.slow_pid]
		pid_array[pid_block-1].bypass = bypass

	@needs_commit
	def set_pid_by_freq(self, pid_block, kp=1, i_xover=None, d_xover=None, si=None, sd=None):
		"""

		Configure the selected PID controller using crossover frequencies.

		:type ch: int; [1,2]
		:param ch: PID controller to  configure

		:type kp: float; [-1e3,1e3]
		:param kp: Proportional gain factor

		:type i_xover: float; [1e-3,1e6] Hz
		:param i_xover: Integrator crossover frequency

		:type d_xover: float; [1,10e6] Hz
		:param d_xover: Differentiator crossover frequency

		:type si: float; float; [-1e3,1e3]
		:param si: Integrator gain saturation

		:type sd: float; [-1e3,1e3]
		:param sd: Differentiator gain saturation

		:raises InvalidConfigurationException: if the configuration of PID gains is not possible.
		"""
		pid_array = [self.fast_pid, self.slow_pid]
		pid_array[pid_block -1].set_reg_by_frequency(scaled_kp, i_xover, d_xover, si, sd)
		pid_array[pid_block -1].gain = pid_array[pid_block -1].gain / self._dac_gains()[pid_block-1]

	@needs_commit
	def set_local_oscillator(self, frequency, phase):
		"""
		Configure the demodulation stage.

		:type frequency : float; [0, 200e6] Hz
		:param frequency : Internal demodulation frequency

		:type phase : float; [0, 360] degrees
		:param phase : float; Internal demodulation phase

		"""
		self.demod_sweep.step = frequency * _LLB_FREQSCALE
		self.demod_sweep.stop = 2**64 -1
		self.demod_sweep.duration = 0
		self.demod_sweep.waveform = 2
		self.demod_sweep.start = phase * _LLB_PHASESCALE
		self.demod_sweep.wait_for_trig = False
		self.demod_sweep.hold_last = False

	@needs_commit
	def set_scan(self, frequency, phase):
		"""
		Configure the scan signal.

		:type frequency : float; [0, 200e6] Hz
		:param frequency : Internal demodulation frequency

		:type phase : float; [0, 360] degrees
		:param phase : float; Internal demodulation phase

		"""
		self.scan_sweep.step = frequency * _LLB_FREQSCALE
		seld.scan_sweep.start = phase * _LLB_PHASESCALE

	@needs_commit
	def set_aux_sine(self, frequency, phase):
		"""
		Configure the aux sine signal.

		:type frequency : float; [0, 200e6] Hz
		:param frequency : Internal demodulation frequency

		:type phase : float; [0, 360] degrees
		:param phase : float; Internal demodulation phase

		"""
		self.aux_sine_sweep.step = frequency * _LLB_FREQSCALE
		seld.aux_sine_sweep.start = phase * _LLB_PHASESCALE

	@needs_commit
	def set_sample_rate(self, rate):
		"""
		Configure the sample rate of the filters and pid controllers of the laser locker.
		
		selectable rates:
			-**high** : 62.5 MHz
			-**low**  : 31.25 MHz
		
		:type rate : string; {'high', 'low'}
		:param rate: sample rate

		"""
		_str_to_rate = {
			'high' 	: _LLB_HIGH_RATE,
			'low'	: _LLB_LOW_RATE
		}
		self.rate_sel = _utils.str_to_val(_str_to_rate, rate, 'sampling rate')

	def _signal_source_volts_per_bit(self, source, scales, trigger=False):
		"""
			Converts volts to bits depending on the signal source. 
			To do: complete this function when osc functionality added to awg, stubbed for now.
		"""

		# Decimation gain is applied only when using precision mode data
		if (not trigger and self.is_precision_mode()) or (trigger and self.trig_precision):
			deci_gain = self._deci_gain()
		else:
			deci_gain = 1.0

		if (source == _LLB_SOURCE_A):
			level = self._monitor_source_volts_per_bit(self.monitor_a, scales)/deci_gain
		elif (source == _LLB_SOURCE_B):
			level = self._monitor_source_volts_per_bit(self.monitor_b, scales)/deci_gain
		elif (source == _LLB_TRIG_SRC_EXT):
			level = 1.0
		else:
			level = 1.0 #used to be 0.0. Gave divide by zero error when triggering on in2

		return level

	@needs_commit
	def _monitor_source_volts_per_bit(self, source, scales):
		monitor_source_gains = {
			'error'		: scales['gain_adc1'] / (4.0 if self.rate_sel else 2.0),
			'pid_fast'	: scales['gain_adc1'] / (4.0 if self.rate_sel else 2.0),
			'pid_slow'	: scales['gain_adc1'] / (4.0 if self.rate_sel else 2.0),
			'in1' 		: scales['gain_adc1'] / (10.0 if scales['atten_ch1'] else 1.0),
			'in2' 		: scales['gain_adc2'] / (10.0 if scales['atten_ch2'] else 1.0),
			'out1'		: scales['gain_dac1'] / 2**4,
			'out2'		: scales['gain_dac2'] / 2**4,
			'scan'		: scales['gain_dac1'] / 2**4, # TODO need to account for where the scan is going
			'lo'		: scales['gain_dac2'] / 2**4,
			'aux'		: scales['gain_dac2'] / 2**4,
			'slow_scan'	: scales['gain_dac2'] / 2**4
		}
		return monitor_source_gains[source]

	@needs_commit
	def set_trigger(self, source, edge, level, minwidth=None, maxwidth=None, hysteresis=10e-2, hf_reject=False, mode='auto'):
		""" 
		Set the trigger source for the monitor channel signals. This can be either of the input or
		monitor signals, or the external input.

		:type source: string, {'in1','in2','A','B','ext'}
		:param source: Trigger Source. May be either an input or monitor channel (as set by 
				:py:meth:`~pymoku.instruments.LockInAmp.set_monitor`), or external. External refers 
				to the back-panel connector of the same	name, allowing triggering from an 
				externally-generated digital [LV]TTL or CMOS signal.

		:type edge: string, {'rising','falling','both'}
		:param edge: Which edge to trigger on. In Pulse Width modes this specifies whether the pulse is positive (rising)
				or negative (falling), with the 'both' option being invalid.

		:type level: float, [-10.0, 10.0] volts
		:param level: Trigger level

		:type minwidth: float, seconds
		:param minwidth: Minimum Pulse Width. 0 <= minwidth < (2^32/samplerate). Can't be used with maxwidth.

		:type maxwidth: float, seconds
		:param maxwidth: Maximum Pulse Width. 0 <= maxwidth < (2^32/samplerate). Can't be used with minwidth.

		:type hysteresis: float, [100e-6, 1.0] volts
		:param hysteresis: Hysteresis around trigger point.

		:type hf_reject: bool
		:param hf_reject: Enable high-frequency noise rejection

		:type mode: string, {'auto', 'normal'}
		:param mode: Trigger mode.
		"""
		# Define the trigger sources appropriate to the LockInAmp instrument
		source = _utils.str_to_val(_LLB_OSC_SOURCES, source, 'trigger source')
		print source
		# This function is the portion of set_trigger shared among instruments with embedded scopes. 
		self._set_trigger(source, edge, level, minwidth, maxwidth, hysteresis, hf_reject, mode)

	@needs_commit
	def set_monitor(self, monitor_ch, source):
		"""
		Select the point inside the lockin amplifier to monitor.

		There are two monitoring channels available, 'A' and 'B'; you can mux any of the internal
		monitoring points to either of these channels.

		The source is one of:
			- **none**: Disable monitor channel
			- **in1**, **in2**: Input Channel 1/2
			- **error_signal**: error signal (before fast PID controller)
			- **pid_fast**: output of the fast pid
			- **pid_slow**: output of the slow pid
			- **lo**: local oscillator to the demodulation
			- **sine**: sine output
			- **out1**: output 1
			- **out2**: output 2
			- **scan**: scan signal

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
		_utils.check_parameter_valid('set', source, allowed=['error', 'pid_fast', 'pid_slow', 'in1', 'in2', 'out1', 'out2', 'scan', 'lo', 'aux', 'slow_scan'], desc="monitor source")

		monitor_sources = {
			'error'			: _LLB_MON_ERROR,
			'pid_fast'		: _LLB_MON_PID_FAST,
			'pid_slow'		: _LLB_MON_PID_SLOW,
			'in1'			: _LLB_MON_IN1,
			'in2'			: _LLB_MON_IN2,
			'out1'			: _LLB_MON_OUT1,
			'out2'			: _LLB_MON_OUT2,
			'scan'			: _LLB_MON_SCAN,
			'lo'			: _LLB_MON_LO,
			'aux'			: _LLB_MON_AUX,
			'slow_scan'		: _LLB_MON_SLOW_SCAN
		}

		if monitor_ch == 'a':
			self.monitor_a = source
			self.monitor_select0 = monitor_sources[source]
		elif monitor_ch == 'b':
			self.monitor_b = source
			self.monitor_select1 = monitor_sources[source]
		else:
			raise ValueOutOfRangeException("Invalid channel %d", monitor_ch)


_llb_reg_hdl = {
	'_fast_scale' :		(REG_LLB_SCALE, to_reg_signed(0, 16, xform = lambda obj,  x : x * 2**14),
										from_reg_signed(0, 16, xform = lambda obj, x : x / 2**14)),

	'_slow_scale' : 	(REG_LLB_SCALE, to_reg_signed(16, 16, xform = lambda obj, x : x * 2**14),
										from_reg_signed(16, 16, xform = lambda obj, x : x / 2**14)),

	'monitor_select0' :	(REG_LLB_MON_SEL, 	to_reg_unsigned(0, 4),
											from_reg_unsigned(0,4)),

	'monitor_select1' : (REG_LLB_MON_SEL,	to_reg_unsigned(4, 4),
											from_reg_unsigned(4, 4)),

	'rate_sel':		(REG_LLB_RATE_SEL,	to_reg_unsigned(0, 1),
										from_reg_unsigned(0, 1)),

	'MuxDec':		(REG_LLB_RATE_SEL,	to_reg_unsigned(1, 1),
										from_reg_unsigned(1, 1)),

	'MuxFast':		(REG_LLB_RATE_SEL,	to_reg_unsigned(2, 1),
										from_reg_unsigned(2, 1)),

	'MuxInt':		(REG_LLB_RATE_SEL,	to_reg_unsigned(3, 2),
										from_reg_unsigned(3, 2)),

	'TrigPort2':		(REG_LLB_MON_SEL,	to_reg_unsigned(8, 1),
										from_reg_unsigned(8, 1)) 
}