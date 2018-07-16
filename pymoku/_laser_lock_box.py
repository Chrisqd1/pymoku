
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

REG_LLB_RATE_SEL			= 76

REGBASE_LLB_IIR				= 28

REGBASE_LLB_PID1			= 106
REGBASE_LLB_PID2			= 117

_LLB_PHASESCALE				= 2**64 / 360.0
_LLB_FREQSCALE				= 2**64 / 1e9
_LLB_HIGH_RATE				= 0
_LLB_LOW_RATE				= 1

_LLB_COEFFICIENT_WIDTH		= 24

_LLB_TRIG_SRC_CH1			= 0
_LLB_TRIG_SRC_CH2			= 1
_LLB_TRIG_SRC_EXT			= 2

class LaserLockBox(_frame_instrument.FrameBasedInstrument):
	def __init__(self):
		super(LaserLockBox, self).__init__()
		self._register_accessors(_llb_reg_hdl)

		self.id = 16
		self.type = "laserlockbox"

		self.fast_fs = 31.25e6
		self.slow_fs = 31.25e6

		self.fast_pid = PID(self, reg_base = REGBASE_LLB_PID1, fs=self.fast_fs)
		self.slow_pid = PID(self, reg_base = REGBASE_LLB_PID2, fs=self.slow_fs)

		self.demod_sweep = SweepGenerator(self, reg_base = REGBASE_LLB_DEMOD)
		self.scan_sweep = SweepGenerator(self, reg_base = REGBASE_LLB_SCAN)
		self.aux_sine_sweep = SweepGenerator(self, reg_base = REGBASE_LLB_AUX_SINE)		
		self.iir_filter = IIRBlock(self, reg_base=REGBASE_LLB_IIR, use_mmap = False)

	@needs_commit
	def set_defaults(self):
		self.set_sample_rate('high')

		# self.demod_sweep.step = 0
		# self.demod_sweep.stop = 2**64 -1
		# self.demod_sweep.duration = 0
		# self.demod_sweep.waveform = 2
		# self.demod_sweep.start = 0
		# self.demod_sweep.wait_for_trig = False
		# self.demod_sweep.hold_last = False

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
						[1.0, 1.0, 1.0, 1.0, 1.0, 1.0]]
		self.set_filter_coeffs(default_filt_coeff)
		self.set_local_oscillator(10e6 ,0)

	def _signal_source_volts_per_bit(self, source, scales, trigger=False):
		"""
			Converts volts to bits depending on the signal source. 
			To do: complete this function when osc functionality added to awg, stubbed for now.
		"""
		if (source == _LLB_TRIG_SRC_CH1):
			level = scales['gain_adc1']
		elif (source == _LLB_TRIG_SRC_CH2):
			level = scales['gain_adc2']
		elif (source == _LLB_TRIG_SRC_EXT):
			level = 1.0
		else:
			level = 1.0

		return level

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
		pid_array[pid_block -1].set_reg_by_frequency(kp, i_xover, d_xover, si, sd)

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
		self.demod_sweep.start = phase * _LLB_PHASESCALE

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

_llb_reg_hdl = {
	'rate_sel':		(REG_LLB_RATE_SEL,	to_reg_unsigned(0, 1),
										from_reg_unsigned(0, 1)),
}