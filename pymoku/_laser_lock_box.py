
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
from ._embedded_pll import EmbeddedPLL

log = logging.getLogger(__name__)

REGBASE_LLB_DEMOD			= 79
REGBASE_LLB_SCAN			= 88
REGBASE_LLB_AUX_SINE		= 97
REGBASE_LLB_PLL				= 106

REG_LLB_MON_SEL				= 75
REG_LLB_RATE_SEL			= 76
REG_LLB_SCALE				= 77
REG_LLB_SCANSCALE			= 78
REG_LLB_AUX_SCALE			= 34 # TODO find better reg
REG_LLB_PID_OFFSETS			= 35 # TODO find better reg

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

_LLB_SCAN_SAWTOOTH			= 2
_LLB_SCAN_TRIANGLE			= 3

_LLB_SCANSOURCE_DAC1		= 0
_LLB_SCANSOURCE_DAC2		= 1
_LLB_SCANSOURCE_NONE		= 2

_LLB_MON_ERROR 				= 1
_LLB_MON_PID_FAST			= 2
_LLB_MON_PID_SLOW			= 3
_LLB_MON_OFFSET_FAST		= 4
_LLB_MON_OFFSET_SLOW		= 5
_LLB_MON_IN1				= 6
_LLB_MON_IN2				= 7
_LLB_MON_OUT1				= 8
_LLB_MON_OUT2				= 9
_LLB_MON_SCAN				= 10
_LLB_MON_LO 				= 11
_LLB_MON_AUX				= 12

_LLB_SOURCE_A		= 0
_LLB_SOURCE_B		= 1
_LLB_SOURCE_IN1		= 2
_LLB_SOURCE_SCAN	= 3
_LLB_SOURCE_IN2		= 3
_LLB_SOURCE_EXT		= 4

_LLB_OSC_SOURCES = {
	'a' : _LLB_SOURCE_A,
	'b' : _LLB_SOURCE_B,
	'scan': _LLB_SOURCE_SCAN,
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
		self.iir_filter = IIRBlock(self, reg_base=REGBASE_LLB_IIR, num_stages = 1, gain_frac_width = 9, coeff_frac_width = 16, use_mmap = False)
		self.embedded_pll = EmbeddedPLL(self, reg_base=REGBASE_LLB_PLL)

	@needs_commit
	def set_defaults(self):
		super(LaserLockBox, self).set_defaults()
		self.set_sample_rate('high')

		default_filt_coeff = 	[[1.0],
						# [1.0, 0.0346271318590754, -0.0466073336600009, 0.0346271318590754, 1.81922686243757, -0.844637126033068]]
						[1, 1, 0, 0, 0, 0]]
		self.set_filter_coeffs(default_filt_coeff)
		self.set_local_oscillator()
		# self.set_scan(0, 0, 'fast', 0)
		# self.set_scan(frequency=0.0, phase=0.0, pid='slow', amplitude=0.0)

		self._set_scale()
		self.MuxDec = 0
		self.MuxFast = 0
		self.MuxInt = 2
	

	def _update_dependent_regs(self, scales):
		super(LaserLockBox, self)._update_dependent_regs(scales)
		self._set_scale()
		
	@needs_commit
	def _set_scale(self):
		# incorporate adc2 scaling if local oscillator source is set to 'external'. Move this global to set_lo?
		self.lo_scale_factor = 1.0 if self.MuxLOSignal == 0 else self._adc_gains()[1] * 2**12

		self._fast_scale = self._adc_gains()[0] / self._dac_gains()[0] / 2**3 * self.lo_scale_factor
		self._slow_scale = self._adc_gains()[0] / self._dac_gains()[1] / 2**3 * self.lo_scale_factor

	@needs_commit
	def set_filter_coeffs(self, filt_coeffs):
		"""
		Configure the filter coefficients in the IIR filter.

		:type filt_coeffs: array;
		:param filt_coeffs: array containg SOS filter coefficients.
		"""
		self.iir_filter.write_coeffs(filt_coeffs)

	@needs_commit
	def set_pid_by_gain(self, pid_block, g=1, kp=1, ki=0, kd=0, si=None, sd=None, input_offset = 0):
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
		pid_array[pid_block -1].gain = pid_array[pid_block -1].gain * 2**15

		if pid_block == 1:
			self.fast_offset = input_offset / (self._adc_gains()[0] * 2**12) / self.lo_scale_factor
		else:
			self.slow_offset = input_offset / (self._adc_gains()[0] * 2**12) / self.lo_scale_factor

	@needs_commit
	def set_pid_enable(self, pid_block, en=True):
		pid_array = [self.fast_pid, self.slow_pid]
		pid_array[pid_block-1].enable = en

	@needs_commit
	def set_pid_bypass(self, pid_block, bypass = False):
		pid_array = [self.fast_pid, self.slow_pid]
		pid_array[pid_block-1].bypass = bypass

	@needs_commit
	def set_pid_by_freq(self, pid_block, kp=1, i_xover=None, d_xover=None, si=None, sd=None, input_offset = 0):
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
		pid_array[pid_block -1].gain = pid_array[pid_block -1].gain * 2**15

		if pid_block == 1:
			self.fast_offset = input_offset / (self._adc_gains()[0] * 2**12) / self.lo_scale_factor
		else:
			self.slow_offset = input_offset / (self._adc_gains()[0] * 2**12) / self.lo_scale_factor

	@needs_commit
	def set_local_oscillator(self, frequency=0.0, phase=0.0, source = 'internal', pll_auto_acq = True):
		"""
		Configure the demodulation stage.

		:type source : list; ['internal', 'external', 'pll']
		:param source : Local Oscillator Source

		:type frequency : float; [0, 200e6] Hz
		:param frequency : Internal demodulation frequency

		:type phase : float; [0, 360] degrees
		:param phase : float; Internal demodulation phase

		:type pll_auto_acq : bool
		:param pll_auto_acq : Enable PLL Auto Acquire

		"""
		self.demod_sweep.step = frequency * _LLB_FREQSCALE
		self.demod_sweep.stop = 2**64 -1
		self.demod_sweep.duration = 0
		self.demod_sweep.waveform = 2
		self.demod_sweep.start = phase * _LLB_PHASESCALE
		self.demod_sweep.wait_for_trig = False
		self.demod_sweep.hold_last = False

		self.embedded_pll.bandwidth = 0
		self.embedded_pll.pllreset = 0
		self.embedded_pll.autoacquire = 1 if pll_auto_acq == True else False
		self.embedded_pll.reacquire = 0

		if source == 'internal':
			self.MuxLOPhase = 0
			self.MuxLOSignal = 0
		elif source == 'external':
			self.MuxLOPhase = 0
			self.MuxLOSignal = 1
			#stubbed for now
		elif source == 'external_pll':
			self.embedded_pll.reacquire = 1
			self.MuxLOPhase = 1
			self.MuxLOSignal = 0
		else:
			#shouldn't happen
			raise ValueOutOfRangeException('Demodulation mode must be one of "internal", "external" or "external_pll", not %s', mode)

		# update scales
		self._set_scale()

	@needs_commit
	def set_aux_sine(self, amplitude = 2.0, frequency = 0.0, phase = 0.0, sync_to_lo = False):
		"""
		Configure the aux sine signal.

		:type frequency : float; [0, 200e6] Hz
		:param frequency : Internal demodulation frequency

		:type phase : float; [0, 360] degrees
		:param phase : float; Internal demodulation phase

		"""
		self.aux_sine_sweep.step = frequency * _LLB_FREQSCALE
		self.aux_sine_sweep.stop = 2**64 -1
		self.aux_sine_sweep.duration = 0
		self.aux_sine_sweep.waveform = 2
		self.aux_sine_sweep.start = phase * _LLB_PHASESCALE
		self.aux_sine_sweep.wait_for_trig = False
		self.aux_sine_sweep.hold_last = False

		self._aux_scale = (amplitude / 2.0) / self._dac_gains()[1] / 2**15

		if sync_to_lo == True:
			self.MuxAuxPhase = 1
		else:
			self.MuxAuxPhase = 0

	@needs_commit
	def set_scan(self, frequency, phase,  amplitude, waveform = 'triangle', output = 'out1'):
		"""
		Configure the scanning generator

		:type frequency : float; [0, 200e6] Hz
		:param frequency : scan frequency

		:type phase : float; [0, 360] degrees
		:param phase : scan phase

		:type amplitude : float; [0, 2]
		:param amplitude : scan amplitude

		:type output : int; [1, 2]
		:param output : selects which output the scan linked to.


		"""
		_str_to_waveform = {
			'sawtooth' 	: _LLB_SCAN_SAWTOOTH,
			'triangle'	: _LLB_SCAN_TRIANGLE
		}
		waveform = _str_to_waveform[waveform]

		_str_to_scansource = {
			'out1' 	: _LLB_SCANSOURCE_DAC1,
			'out2'	: _LLB_SCANSOURCE_DAC2,
			'none'	: _LLB_SCANSOURCE_NONE
		}
		output = _str_to_scansource[output]

		self.scan_sweep.step = frequency * _LLB_FREQSCALE if waveform == _LLB_SCAN_SAWTOOTH else frequency * _LLB_FREQSCALE * 2
		self.scan_sweep.stop = 2**64 -1
		self.scan_sweep.duration = 0
		self.scan_sweep.waveform = waveform
		self.scan_sweep.start = phase * _LLB_PHASESCALE
		self.scan_sweep.wait_for_trig = False
		self.scan_sweep.hold_last = False



		if output == _LLB_SCANSOURCE_DAC1:
			self.fast_scan_enable = True
			self.slow_scan_enable = False
			self.scan_amplitude = (amplitude / 2.0) / self._dac_gains()[0] / 2**15
		elif output == _LLB_SCANSOURCE_DAC2:
			self.fast_scan_enable = False
			self.slow_scan_enable = True
			self.scan_amplitude = (amplitude / 2.0) / self._dac_gains()[1] / 2**15
		else:
			self.fast_scan_enable = False
			self.slow_scan_enable = False
			self.scan_amplitude = (amplitude / 2.0) / self._dac_gains()[0] / 2**15 # default to out 1 scale

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
			'error'			: scales['gain_adc1'] * 2.0,
			'pid_fast'		: scales['gain_dac1'] * 2**4,
			'pid_slow'		: scales['gain_dac2'] * 2**4,
			'offset_fast'	: scales['gain_dac1'] * 2**4,
			'offset_slow'	: scales['gain_dac2'] * 2**4,
			'in1' 			: scales['gain_adc1'] / (10.0 if scales['atten_ch1'] else 1.0),
			'in2' 			: scales['gain_adc2'] / (10.0 if scales['atten_ch2'] else 1.0),
			'out1'			: scales['gain_dac1'] * 2**4,
			'out2'			: scales['gain_dac2'] * 2**4,
			'scan'			: scales['gain_dac1'] * 2**4,
			'lo'			: 2**-11 if self.MuxLOSignal == 0 else scales['gain_adc2'] * 2.0,
			'aux'			: scales['gain_dac2'] * 2**4
			# 'slow_scan'		: scales['gain_dac2'] * 2**4
		}
		return monitor_source_gains[source]

	@needs_commit
	def set_trigger(self, source, edge, level, minwidth=None, maxwidth=None, hysteresis=10e-2, hf_reject=False, mode='auto', trig_on_scan_rising = False):
		""" 
		Set the trigger source for the monitor channel signals. This can be either of the input or
		monitor signals, or the external input.

		:type source: string, {'in1','in2','scan','error_rising','A','B','ext'}
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

		# TODO: decide whether trig_on_scan_rising can be set independently of source

		if source == 'scan':
			self.trig_aux = 1
		else:
			self.trig_aux = 0

		if trig_on_scan_rising:
			self.cond_trig = 1
		else:
			self.cond_trig = 0

		# Define the trigger sources appropriate to the LockInAmp instrument
		source = _utils.str_to_val(_LLB_OSC_SOURCES, source, 'trigger source')
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
		_utils.check_parameter_valid('set', source, allowed=['error', 'pid_fast', 'pid_slow', 'offset_fast', 'offset_slow', 'in1', 'in2', 'out1', 'out2', 'scan', 'lo', 'aux', 'slow_scan'], desc="monitor source")

		monitor_sources = {
			'error'			: _LLB_MON_ERROR,
			'pid_fast'		: _LLB_MON_PID_FAST,
			'pid_slow'		: _LLB_MON_PID_SLOW,
			'offset_fast'	: _LLB_MON_OFFSET_FAST,
			'offset_slow'	: _LLB_MON_OFFSET_SLOW,
			'in1'			: _LLB_MON_IN1,
			'in2'			: _LLB_MON_IN2,
			'out1'			: _LLB_MON_OUT1,
			'out2'			: _LLB_MON_OUT2,
			'scan'			: _LLB_MON_SCAN,
			'lo'			: _LLB_MON_LO,
			'aux'			: _LLB_MON_AUX
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

	'_aux_scale' : 	(REG_LLB_AUX_SCALE, to_reg_signed(0, 16, xform = lambda obj, x : x * 2**14),
										from_reg_signed(0, 16, xform = lambda obj, x : x / 2**14)),

	'scan_amplitude' :	(REG_LLB_SCANSCALE, to_reg_signed(0, 16, xform = lambda obj,  x : x * 2**14),
										from_reg_signed(0, 16, xform = lambda obj, x : x / 2**14)),

	'fast_scan_enable': (REG_LLB_SCANSCALE, to_reg_unsigned(16, 1),
											from_reg_unsigned(16, 1)),

	'slow_scan_enable': (REG_LLB_SCANSCALE, to_reg_unsigned(17, 1),
											from_reg_unsigned(17, 1)),

	'fast_offset':	(REG_LLB_PID_OFFSETS, to_reg_signed(0, 16, xform = lambda obj, x : x * 2**15),
											from_reg_signed(0, 16, xform = lambda obj, x : x / 2**15)),

	'slow_offset':	(REG_LLB_PID_OFFSETS, to_reg_signed(16, 16, xform = lambda obj, x : x * 2**15),
											from_reg_signed(16, 16, xform = lambda obj, x : x / 2**15)),

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

	'MuxLOPhase':	(REG_LLB_RATE_SEL,	to_reg_unsigned(5, 1),
										from_reg_unsigned(5, 1)),

	'MuxLOSignal':	(REG_LLB_RATE_SEL,	to_reg_unsigned(6, 1),
										from_reg_unsigned(6, 1)),

	'MuxAuxPhase':	(REG_LLB_RATE_SEL,	to_reg_unsigned(7, 1),
										from_reg_unsigned(7, 1)),

	'trig_aux':		(REG_LLB_MON_SEL,	to_reg_unsigned(8, 1),
										from_reg_unsigned(8, 1)),

	'cond_trig': (REG_LLB_MON_SEL, 	to_reg_unsigned(9, 1),
									from_reg_unsigned(9, 1))
}