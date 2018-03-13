
import math
import logging

from ._instrument import *
from ._instrument import _usgn, _sgn
from . import _utils
from ._trigger import Trigger
from ._sweep_generator import SweepGenerator

log = logging.getLogger(__name__)

REG_SG_TrigDutyInternalCH0_L		= 69
REG_SG_TrigDutyInternalCH0_H		= 70
REG_SG_TrigDutyInternalCH1_L		= 71
REG_SG_TrigDutyInternalCH1_H		= 72
REG_SG_TrigPeriodInternalCH0_L		= 73
REG_SG_TrigPeriodInternalCH0_H		= 74
REG_SG_TrigPeriodInternalCH1_L		= 75
REG_SG_TrigPeriodInternalCH1_H		= 76
REG_SG_ADCThreshold		= 77
REG_SG_DACThreshold		= 78
REG_SG_NCycles_TrigDutyCH0_L		= 79
REG_SG_NCycles_TrigDutyCH0_H		= 80
REG_SG_NCycles_TrigDutyCH1_L		= 81
REG_SG_NCycles_TrigDutyCH1_H		= 82
REG_SG_TrigSweepMode 	= 83
REG_SG_SweepLengthCh0_L = 84
REG_SG_SweepLengthCh0_H = 85
REG_SG_SweepLengthCh1_L = 86
REG_SG_SweepLengthCh1_H = 87
REG_SG_SweepInitFreqCh0_L = 88
REG_SG_SweepInitFreqCh0_H = 89
REG_SG_SweepInitFreqCh1_L = 90
REG_SG_SweepInitFreqCh1_H = 91
REG_SG_SweepIncrementCh0_L = 92
REG_SG_SweepIncrementCh0_H = 93
REG_SG_SweepIncrementCh1_L = 94
REG_SG_SweepIncrementCh1_H = 95

REG_SG_WAVEFORMS	= 96
REG_SG_MODSOURCE	= 123
REG_SG_PRECLIP		= 124

REG_SG_FREQ1_L		= 97
REG_SG_FREQ1_H		= 105
REG_SG_PHASE1		= 98
REG_SG_AMP1			= 99
REG_SG_MODF1_L		= 100
REG_SG_MODF1_H		= 101
REG_SG_T01			= 102
REG_SG_T11			= 103
REG_SG_T21			= 104
REG_SG_RISERATE1_L	= 106
REG_SG_FALLRATE1_L	= 107
REG_SG_RFRATE1_H	= 108
REG_SG_MODA1		= 121

REG_SG_FREQ2_L		= 109
REG_SG_FREQ2_H		= 117
REG_SG_PHASE2		= 110
REG_SG_AMP2			= 111
REG_SG_MODF2_L		= 112
REG_SG_MODF2_H		= 113
REG_SG_T02			= 114
REG_SG_T12			= 115
REG_SG_T22			= 116
REG_SG_RISERATE2_L	= 118
REG_SG_FALLRATE2_L	= 119
REG_SG_RFRATE2_H	= 120
REG_SG_MODA2		= 122


REG_WG_SQRT0_CH1			= 20
REG_WG_SQRT1_CH1			= 21
REG_WG_SQRT2_CH1			= 22
REG_WG_INVERSEFREQ_CH1		= 23
REG_WG_RISERATEH_CH1		= 24
REG_WG_RISERATEL_CH1		= 25
REG_WG_FALLRATEH_CH1		= 26
REG_WG_FALLRATEL_CH1		= 27

REG_WG_TEMPPHASE			= 124

REG_WG_CONTROL 				= 64
REG_WG_MODDEPTH_CH1 		= 65
REG_WG_GATETHRESH_CH1		= 66
REG_WG_AMP_CH1 				= 67
REG_WG_OFFSET_CH1 			= 68
REG_WG_MODDEPTH_CH2 		= 94
REG_WG_GATETHRESH_CH2		= 95
REG_WG_AMP_CH2 				= 96
REG_WG_OFFSET_CH2 			= 97

_SG_WAVE_SINE		= 0
_SG_WAVE_SQUARE		= 1
_SG_WAVE_TRIANGLE	= 2
_SG_WAVE_PULSE		= 3
_SG_WAVE_DC			= 4

_SG_MOD_NONE		= 0
_SG_MOD_AMPL		= 1
_SG_MOD_FREQ		= 2
_SG_MOD_PHASE		= 4

_SG_MODSOURCE_INT	= 0
_SG_MODSOURCE_ADC	= 1
_SG_MODSOURCE_DAC	= 2

_SG_FREQSCALE		= 1.0e9 / 2**64
_SG_PHASESCALE		= 360.0 / (2**32) # Wraps
_SG_RISESCALE		= 1e9 / 2**48
_SG_AMPSCALE		= 4.0 / (2**15 - 1)
_SG_DEPTHSCALE		= 1.0 / 2**15
_SG_MAX_RISE		= 1e9 - 1
_SG_TIMESCALE 		= 1.0 / (2**32 - 1) # Doesn't wrap

_SG_MOD_FREQ_MAX 	= 62.5e6 # Hz
_SG_SQUARE_CLIPSINE_THRESH = 25e3 # Hz

_SG_TRIG_ADC 		= 0
_SG_TRIG_DAC		= 1
_SG_TRIG_EXT		= 2
_SG_TRIG_INTER		= 3

_SG_MOD_ADC 		= 0
_SG_MOD_DAC			= 1
_SG_MOD_INTER		= 2
_SG_MOD_GATE		= 3

_SG_GATE_ADC 		= 0
_SG_GATE_DAC		= 1
_SG_GATE_EXT		= 2
_SG_GATE_SWEEP		= 3

_SG_TRIG_MODE_OFF 	= 0
_SG_TRIG_MODE_GATE	= 1
_SG_TRIG_MODE_START = 2
_SG_TRIG_MODE_NCYCLE= 3
_SG_TRIG_MODE_SWEEP = 4

_SG_TRIGLVL_ADC_MAX = 5.0 # V
_SG_TRIGLVL_ADC_MIN = -5.0 # V

_SG_TRIGLVL_DAC_MAX = 1.0 # V
_SG_TRIGLVL_DAC_MIN = -1.0 # V

class BasicWaveformGenerator(MokuInstrument):
	"""

	.. automethod:: pymoku.instruments.WaveformGenerator.__init__

	"""
	def __init__(self):
		""" Create a new WaveformGenerator instance, ready to be attached to a Moku."""
		super(BasicWaveformGenerator, self).__init__()
		self._register_accessors(_siggen_reg_handlers)
		self.id = 4
		self.type = "signal_generator"
		self._trigger1 = Trigger(self, 69, 1.0/500e6)
		self._trigger2 = Trigger(self, 98, 1.0/500e6)
		self._sweep1 = SweepGenerator(self, 76)
		self._sweep2 = SweepGenerator(self, 105)		

	@needs_commit
	def set_defaults(self):
		super(BasicWaveformGenerator, self).set_defaults()
		self.out1_enable = True
		self.out2_enable = True
		self.out1_amplitude = 0
		self.out2_amplitude = 0
		self.out1_frequency = 0
		self.out2_frequency = 0
		self.adc1_statuslight = False
		self.adc2_statuslight = False

		# Burst/sweep mode exception variables:
		self.ch1_is_ramp = False
		self.ch2_is_ramp = False
		self.ch1_edgetime_nonzero = False
		self.ch2_edgetime_nonzero = False

		# Disable inputs on hardware that supports it
		self.en_in_ch1 = True
		self.en_in_ch2 = True
		self.trig_sweep_mode_ch1 = _SG_TRIG_MODE_OFF
		self.trig_sweep_mode_ch2 = _SG_TRIG_MODE_OFF

		# Configure front end:
		self._set_frontend(channel = 1, fiftyr=True, atten=False, ac=False)
		self._set_frontend(channel = 2, fiftyr=True, atten=False, ac=False)

		self.trigger_select_ch1 = 0
		self.trigger_select_ch2 = 0

		self.trig_source_ch1 = 0
		self.mod_source_ch1 = 0
		self.gate_source_ch1 = 0
		self.amod_enable_ch1 = 0
		self.mod_depth_ch1 = 0
		self.gate_thresh_ch1 = 0
		self.waveform_type_ch1 = 0

		self.trig_source_ch2 = 0
		self.mod_source_ch2 = 0
		self.gate_source_ch2 = 0
		self.amod_enable_ch2 = 0
		self.mod_depth_ch2 = 0
		self.gate_thresh_ch2 = 0
		self.waveform_type_ch2 = 0

		self._trigger1.trigtype = 0
		self._trigger1.edge = 0
		self._trigger1.level = 2**10

	def _set_sweepgenerator(self, sweepgen=None, waveform=None, waitfortrig=None, frequency=None, offset=None, logsweep=None, duration=None):
		sweepgen.waveform = waveform
		sweepgen.waitfortrig = waitfortrig
		sweepgen.start = offset / 360.0 * (2**64 - 1)
		sweepgen.stop = 2**64 - 1
		sweepgen.step = frequency/_SG_FREQSCALE
		sweepgen.duration = duration * 125.0e6

	def _set_trig(self, trig, trigtype=None, edge=None, pulsetype=None, hysteresis=None, timer=None, holdoff=None, auto_holdoff=None, ntrigger=None, ntrigger_mode=None, level=None, duration=None, timestep=None):
		trig.trigtype = trigtype
		trig.edge = edge
		trig.pulsetype = pulsetype
		trig.hysteresis = hysteresis
		trig.timer = timer
		trig.holdoff = holdoff
		trig.auto_holdoff = auto_holdoff
		trig.ntrigger = ntrigger
		trig.ntrigger_mode = ntrigger_mode
		trig.level = level
		trig.duration = duration
		trig.timestep = timestep

	@needs_commit
	def gen_sinewave(self, ch, amplitude, frequency, offset=0, phase=0.0):
		""" Generate a Sine Wave with the given parameters on the given channel.

		:type ch: int; {1,2}
		:param ch: Channel on which to generate the wave

		:type amplitude: float, [0.0,2.0] Vpp
		:param amplitude: Waveform peak-to-peak amplitude

		:type frequency: float, [0,250e6] Hz
		:param frequency: Frequency of the wave

		:type offset: float, [-1.0,1.0] Volts
		:param offset: DC offset applied to the waveform

		:type phase: float, [0-360] degrees
		:param phase: Phase offset of the wave

		:raises ValueError: if the channel number is invalid
		:raises ValueOutOfRangeException: if wave parameters are out of range

		"""
		_utils.check_parameter_valid('set', ch, [1,2],'output channel')
		_utils.check_parameter_valid('range', amplitude, [0.0, 2.0],'sinewave amplitude','Volts')
		_utils.check_parameter_valid('range', frequency, [0,250e6],'sinewave frequency', 'Hz')
		_utils.check_parameter_valid('range', phase, [0,360], 'sinewave phase', 'degrees')

		# Ensure offset does not cause signal to exceed allowable 2.0Vpp range
		upper_voltage = offset + (amplitude/2.0)
		lower_voltage = offset - (amplitude/2.0)
		if (upper_voltage > 1.0) or (lower_voltage < -1.0):
			raise ValueOutOfRangeException("Sinewave offset limited by amplitude (max output range 2.0Vpp).")

		if ch == 1:
			self.out1_waveform = _SG_WAVE_SINE
			self.enable_ch1 = 1
			self._set_sweepgenerator(self._sweep1, 0, 0, frequency, phase, 0, 0)
			self.amplitude_ch1 = amplitude / 2 * ((2**17-1))
			self.offset_ch1 = offset * (2**15 - 1)

			# global frequency tracker:
			self.out1_frequency = frequency 
		elif ch == 2:
			self.out2_waveform = _SG_WAVE_SINE
			self.enable_ch2 = 1
			self._set_sweepgenerator(self._sweep2, 0, 0, frequency, phase, 0, 0)
			self.amplitude_ch2 = amplitude / 2 * (2**17 - 1)
			self.offset_ch2 = offset * (2**15 - 1)		
			self.out2_frequency = frequency	

	@needs_commit
	def gen_squarewave(self, ch, amplitude, frequency, offset=0, duty=0.5, risetime=0, falltime=0, phase=0.0):
		""" Generate a Square Wave with given parameters on the given channel.

		:type ch: int; {1,2}
		:param ch: Channel on which to generate the wave

		:type amplitude: float, volts
		:param amplitude: Waveform peak-to-peak amplitude

		:type frequency: float, hertz
		:param frequency: Frequency of the wave

		:type offset: float, volts
		:param offset: DC offset applied to the waveform

		:type duty: float, 0-1
		:param duty: Fractional duty cycle

		:type risetime: float, 0-1
		:param risetime: Fraction of a cycle taken for the waveform to rise

		:type falltime: float 0-1
		:param falltime: Fraction of a cycle taken for the waveform to fall

		:type phase: float, degrees 0-360
		:param phase: Phase offset of the wave

		:raises ValueError: invalid channel number
		:raises ValueOutOfRangeException: input parameters out of range or incompatible with one another
		"""
		_utils.check_parameter_valid('set', ch, [1,2],'output channel')
		_utils.check_parameter_valid('range', amplitude, [0.0, 2.0],'squarewave amplitude','Volts')
		_utils.check_parameter_valid('range', frequency, [0,100e6],'squarewave frequency', 'Hz')
		_utils.check_parameter_valid('range', offset, [-1.0,1.0], 'squarewave offset', 'cycles')
		_utils.check_parameter_valid('range', duty, [0,1.0], 'squarewave duty', 'cycles')
		_utils.check_parameter_valid('range', risetime, [0,1.0], 'squarewave risetime', 'cycles')
		_utils.check_parameter_valid('range', falltime, [0,1.0], 'squarewave falltime', 'cycles')
		_utils.check_parameter_valid('range', phase, [0,360], 'squarewave phase', 'degrees')

		# Ensure offset does not cause signal to exceed allowable 2.0Vpp range
		upper_voltage = offset + (amplitude/2.0)
		lower_voltage = offset - (amplitude/2.0)
		if (upper_voltage > 1.0) or (lower_voltage < -1.0):
			raise ValueOutOfRangeException("Squarewave offset limited by amplitude (max output range 2.0Vpp).")

		if duty < risetime:
			raise ValueOutOfRangeException("Squarewave duty too small for given rise time.")
		elif duty + falltime > 1:
			raise ValueOutOfRangeException("Squarewave duty and fall time too big.")

		# Check rise/fall times are within allowable DAC frequency

		# TODO: Implement clipped sine squarewave above threshold
		if frequency > _SG_SQUARE_CLIPSINE_THRESH:
			log.warning("Squarewave may experience edge jitter above %d kHz.", _SG_SQUARE_CLIPSINE_THRESH/1e3)

		riserate = frequency / risetime if risetime else _SG_MAX_RISE
		fallrate = frequency / falltime if falltime else _SG_MAX_RISE
		# Raise warning if calculated rise/fall rate is > max rise/fall rate. Set values to max if this occurs.
		if riserate > _SG_MAX_RISE:
			riserate = _SG_MAX_RISE
			log.warning("Riserate restricted to maximum value of %d s.",_SG_MAX_RISE)
		if fallrate > _SG_MAX_RISE:
			fallrate = _SG_MAX_RISE
			log.warning("Fallrate restricted to maximum value of %d s.",_SG_MAX_RISE)

		if ch == 1:
			self.out1_waveform = _SG_WAVE_SQUARE
			self.enable_ch1 = 1
			self._set_sweepgenerator(self._sweep1, 0, 0, frequency, phase, 0, 0)
			self.amplitude_ch1 = amplitude / 2 * (2**15 - 1)
			self.offset_ch1 = offset * (2**15 - 1)

			# This is overdefined, but saves the FPGA doing a tricky division
			self.t0_ch1 = risetime
			self.t1_ch1 = duty
			self.t2_ch1 = duty + falltime
			self.riserate_ch1 = riserate
			self.fallrate_ch1 = fallrate
			self.frequency_ch1 = frequency/_SG_FREQSCALE

		elif ch == 2:
			self.out2_waveform = _SG_WAVE_SQUARE
			self.enable_ch2 = 1
			self._set_sweepgenerator(self._sweep2, 0, 0, frequency, phase, 0, 0)
			self.amplitude_ch2 = amplitude / 2 * (2**15 - 1)
			self.offset_ch2 = offset * (2**15 - 1)	
			self.t0_ch2 = risetime
			self.t1_ch2 = duty
			self.t2_ch2 = duty + falltime
			self.riserate_ch2 = riserate
			self.fallrate_ch2 = fallrate
			self.frequency_ch2 = frequency/_SG_FREQSCALE

		# if ch == 1:
		# 	self.out1_waveform = _SG_WAVE_SQUARE
		# 	self.out1_enable = True
		# 	self.out1_amplitude = amplitude
		# 	self.out1_frequency = frequency
		# 	self.out1_offset = offset
		# 	self.out1_clipsine = False # TODO: Should switch to clip depending on freq or user

		# 	# This is overdefined, but saves the FPGA doing a tricky division
		# 	self.out1_t0 = risetime
		# 	self.out1_t1 = duty
		# 	self.out1_t2 = duty + falltime
		# 	self.out1_riserate = riserate
		# 	self.out1_fallrate = fallrate
		# 	self.out1_phase =  phase

		# 	# Parameters used to determine burst/sweep mode exception cases:
		# 	self.ch1_edgetime_nonzero = True if (risetime != 0 or falltime != 0) else False
		# 	self.dac = False
		# elif ch == 2:
		# 	self.out2_waveform = _SG_WAVE_SQUARE
		# 	self.out2_enable = True
		# 	self.out2_amplitude = amplitude
		# 	self.out2_frequency = frequency
		# 	self.out2_offset = offset
		# 	self.out2_clipsine = False
		# 	self.out2_t0 = risetime
		# 	self.out2_t1 = duty
		# 	self.out2_t2 = duty + falltime
		# 	self.out2_riserate = frequency / risetime if risetime else _SG_MAX_RISE
		# 	self.out2_fallrate = frequency / falltime if falltime else _SG_MAX_RISE
		# 	self.out2_phase = phase
		# 	self.ch2_edgetime_nonzero = 1 if (risetime != 0 or falltime != 0) else 0
		# 	self.ch2_is_ramp = False

	@needs_commit
	def gen_rampwave(self, ch, amplitude, frequency, offset=0, symmetry=0.5, phase= 0.0):
		""" Generate a Ramp with the given parameters on the given channel.

		This is a wrapper around the Square Wave generator, using the *riserate* and *fallrate*
		parameters to form the ramp.

		:type ch: int; {1,2}
		:param ch: Channel on which to generate the wave

		:type amplitude: float, volts
		:param amplitude: Waveform peak-to-peak amplitude

		:type frequency: float, hertz
		:param frequency: Frequency of the wave

		:type offset: float, volts
		:param offset: DC offset applied to the waveform

		:type symmetry: float, 0-1
		:param symmetry: Fraction of the cycle rising.

		:type phase: float, degrees 0-360
		:param phase: Phase offset of the wave

		:raises ValueError: invalid channel number
		:raises ValueOutOfRangeException: invalid waveform parameters
		"""
		_utils.check_parameter_valid('set', ch, [1,2],'output channel')
		_utils.check_parameter_valid('range', amplitude, [0.0, 2.0],'rampwave amplitude','Volts')
		_utils.check_parameter_valid('range', frequency, [0,100e6],'rampwave frequency', 'Hz')
		_utils.check_parameter_valid('range', offset, [-1.0,1.0], 'rampwave offset', 'cycles')
		_utils.check_parameter_valid('range', symmetry, [0,1.0], 'rampwave symmetry', 'fraction')
		_utils.check_parameter_valid('range', phase, [0,360], 'rampwave phase', 'degrees')

		# Ensure offset does not cause signal to exceed allowable 2.0Vpp range
		upper_voltage = offset + (amplitude/2.0)
		lower_voltage = offset - (amplitude/2.0)
		if (upper_voltage > 1.0) or (lower_voltage < -1.0):
			raise ValueOutOfRangeException("Rampwave offset limited by amplitude (max output range 2.0Vpp).")

		self.gen_squarewave(ch, amplitude, frequency,
			offset = offset, duty = symmetry,
			risetime = symmetry,
			falltime = 1 - symmetry,
			phase = phase)

		# Ramp waveforms not allowed for burst/sweep modes
		if ch == 1:
			self.ch1_is_ramp = True
		else:
			self.ch2_is_ramp = True


	@needs_commit
	def gen_off(self, ch=None):
		""" Turn Waveform Generator output(s) off.

		The channel will be turned on when configuring the waveform type but can be turned off
		using this function. If *ch* is None (the default), both channels will be turned off,
		otherwise just the one specified by the argument.

		:type ch: int; {1,2} or None
		:param ch: Channel to turn off, or both.

		:raises ValueError: invalid channel number
		:raises ValueOutOfRangeException: if the channel number is invalid
		"""
		_utils.check_parameter_valid('set', ch, [1,2],'output channel', allow_none=True)

		if ch is None or ch == 1:
			self.out1_enable = False

		if ch is None or ch == 2:
			self.out2_enable = False


class WaveformGenerator(BasicWaveformGenerator):
	""" Waveform Generator instrument object.

	To run a new Waveform Generator instrument, this should be instantiated and deployed via a connected
	:any:`Moku` object using :any:`deploy_instrument`. Alternatively, a pre-configured instrument object
	can be obtained by discovering an already running Waveform Generator instrument on a Moku:Lab device via
	:any:`discover_instrument`.

	.. automethod:: pymoku.instruments.WaveformGenerator.__init__

	.. attribute:: type
		:annotation: = "signal_generator"

		Name of this instrument.

	"""
	def __init__(self):
		""" Create a new WaveformGenerator instance, ready to be attached to a Moku."""
		super(WaveformGenerator, self).__init__()
		self._register_accessors(_siggen_mod_reg_handlers)

		# Define any (non-register-mapped) properties that are used when committing
		# as a commit is called when the instrument is set running
		self.trig_volts_ch1 = 0.0
		self.trig_volts_ch2 = 0.0
		self._sweepmod1 = SweepGenerator(self, 85)
		self._sweepmod2 = SweepGenerator(self, 115)

	@needs_commit
	def set_trigger(self, ch, mode, ncycles=1, sweep_start_freq=None, sweep_end_freq=0, sweep_duration=0, trigger_source='external', trigger_threshold=0.0, internal_trig_period=1.0, internal_trig_high=0.5):
		""" Configure gated, start, ncycle or sweep trigger mode on target channel.

		The trigger event can come from an ADC input channel, the opposite generated waveform, the external
		trigger input (for hardware that supports that) or a internally-generated clock of configurable
		period.

		The trigger event can be used in several different ways:
		- *gated*: The output waveform is only generated while the trigger is asserted
		- *start*: The output waveform is enabled once the trigger event fires
		- *ncycle*: The output waveform starts at a trigger event and completes the given number of cycles, before turning off and re-arming
		- *sweep*: The trigger event starts the waveform generation at the *sweep_start_freq*, before automatically sweeping the
		frequency to *sweep_end_freq* over the course of *sweep_duration* seconds.

		:type ch : int
		:param ch: target channel.

		:type mode: string, {'gated', 'start', 'ncycle', 'sweep', 'off'}
		:param mode: Select the mode in which the trigger is operated.

		:type ncycles : int, [1, 1e6]
		:param ncycles : integer number of signal repetitions in ncycle mode.

		:type sweep_start_freq : float, [0.0,250.0e6], hertz
		:param sweep_start_freq : starting sweep frequency, set to current waveform frequency if not specified. Value range may vary for different waveforms.

		:type sweep_end_freq : float, [0.0,250.0e6], hertz
		:param sweep_end_freq : finishing sweep frequency. Value range may vary for different waveforms.

		:type sweep_duration : float, [0.0,1000.0], seconds
		:param sweep_duration : sweep duration in seconds.

		:type trigger_source: string {'external', 'in', 'out', 'internal'}
		:param: defines which source should be used as triggering signal.

		:type trigger_threshold: float, [-5, 5], volts
		:param trigger_threshold: The threshold value range dependes on the source and the attenution used. Values ranges might be less for different settings.

		:type internal_trig_period: float, [0,1e11], seconds
		:param internal_trig_period: period of the internal trigger clock, if used.

		:type internal_trig_high: float, [0,1e11], seconds
		:param internal_trig_high: High time of the internal trigger clock, if used. Must be less than the internal trigger period.
		"""

		_utils.check_parameter_valid('set', ch, [1,2],'output channel')
		_utils.check_parameter_valid('set', mode, ['gated','start','ncycle','sweep'],'trigger mode')
		_utils.check_parameter_valid('set', trigger_source, ['external','in', 'out','adc','dac','internal'],'trigger source')
		_utils.check_parameter_valid('range', ncycles, [0,1e6],'output channel','frequency')
		_utils.check_parameter_valid('range', sweep_duration, [0.0,1000.0],'sweep duration','seconds')
		_utils.check_parameter_valid('range', internal_trig_period, [100.0e-9,1000.0],'internal trigger period','seconds')
		_utils.check_parameter_valid('range', internal_trig_high, [10.0e-9,1000.0],'internal trigger high time','seconds')

		# Can't use modulation with trigger/sweep modes
		self.gen_modulate_off(ch)

		## Configure trigger source settings:
		_str_to_trigger_source = {
			'external' : _SG_TRIG_EXT,
			'adc' : _SG_TRIG_ADC,
			'in': _SG_TRIG_ADC,
			'out': _SG_TRIG_DAC,
			'dac' : _SG_TRIG_DAC,
			'internal' : _SG_TRIG_INTER
		}

		##### TRIGGER SOURCE:
		source = _utils.str_to_val(_str_to_trigger_source, trigger_source, 'trigger source')

		if source is _SG_TRIG_ADC:
			_utils.check_parameter_valid('range', trigger_threshold, [_SG_TRIGLVL_ADC_MIN, _SG_TRIGLVL_ADC_MAX], 'trigger threshold', 'Volts')
		elif source is _SG_TRIG_DAC:
			_utils.check_parameter_valid('range', trigger_threshold, [_SG_TRIGLVL_DAC_MIN, _SG_TRIGLVL_DAC_MAX], 'trigger threshold', 'Volts')

		## The internal trigger's duty cycle is only used in gated burst mode. Duty cycle is limited such that the duty period is not
		## less than 8 ns and not greater than the trigger period minus 8 ns.

		if internal_trig_high > internal_trig_period:
			raise ValueOutOfRangeException("Internal trigger high must be less than or equal to the internal trigger period.")

		if (internal_trig_period - internal_trig_high) <= 8.0e-9:
			internal_trig_high = internal_trig_period - 10.0e-9

		# internal_trig_increment = math.ceil((2**64-1)/float((internal_trig_period*125*10**6)))
		# internal_trig_dutytarget = round((2**64-1)*(float(internal_trig_high)/float(internal_trig_period))) if mode == 'gated' else 2**63

		if ch == 1:
			self._trigger1.trigtype = 0
			self._trigger1.edge = 0
			self.adc1_statuslight = True if source == _SG_TRIG_ADC else False
		elif ch == 2:
			self._trigger1.trigtype = 0
			self._trigger1.edge = 0
			self.adc2_statuslight = True if source == _SG_TRIG_ADC else False

		##### TRIGGER MODES:

		_str_to_trigger_mode = {
			'gated' : _SG_TRIG_MODE_GATE,
			'start' : _SG_TRIG_MODE_START,
			'ncycle' : _SG_TRIG_MODE_NCYCLE,
			'sweep'	: _SG_TRIG_MODE_SWEEP
		}
		mode = _utils.str_to_val(_str_to_trigger_mode, mode, 'trigger mode')

		if sweep_start_freq is None or mode != _SG_TRIG_MODE_SWEEP:
			channel_frequency = self.out1_frequency if ch == 1 else self.out2_frequency
		else:
			channel_frequency = sweep_start_freq

		waveform = self.out1_waveform if ch == 1 else self.out2_waveform

		#if waveform is a sinewave certain ranges do change
		if waveform == _SG_WAVE_SINE:
			_utils.check_parameter_valid('range', sweep_end_freq, [0.0,250.0e6],'sweep finishing frequency','frequency')
			_utils.check_parameter_valid('range', channel_frequency, [0.0,250.0e6],'sweep starting frequency','frequency')
		else:
			_utils.check_parameter_valid('range', sweep_end_freq, [0.0,100.0e6],'sweep finishing frequency','frequency')
			_utils.check_parameter_valid('range', channel_frequency, [0.0,100.0e6],'sweep starting frequency','frequency')

		# Ramp waveform cannot be used for any burst/sweep mode:
		is_ramp = self.ch1_is_ramp if ch == 1 else self.ch2_is_ramp
		if is_ramp == _SG_WAVE_TRIANGLE:
			raise ValueOutOfRangeException("Ramp waveforms cannot be used in burst/sweep modes.")

		if mode == _SG_TRIG_MODE_GATE:
			self._gated_mode(ch, waveform, source, trigger_threshold, internal_trig_period, internal_trig_high)
		elif mode == _SG_TRIG_MODE_START:
			self._start_mode(ch, source, trigger_threshold)
		elif mode == _SG_TRIG_MODE_NCYCLE:
			self._ncycle_mode(ch, channel_frequency, ncycles, trigger_threshold, source, internal_trig_period)
		elif mode == _SG_TRIG_MODE_SWEEP:
			self._sweep_mode(ch, waveform, source, sweep_end_freq, channel_frequency, sweep_duration, trigger_threshold)

	def _gated_mode(self, ch, waveform, source, trigger_threshold, internal_trig_period, internal_trig_high):
		# Pulse waveform edge must be minimum for gated burst mode and sweep mode:
		if waveform != 0:
			if ch == 1 and self.ch1_edgetime_nonzero == True:
				raise ValueOutOfRangeException("Pulse waveform rise and fall times must be set to zero for gated burst mode and sweep mode.")
			if ch == 2 and self.ch2_edgetime_nonzero == True:
				raise ValueOutOfRangeException("Pulse waveform rise and fall times must be set to zero for gated burst mode and sweep mode.")

		# Convert threshold to bits
		g1, g2 = self._adc_gains()
		d1, d2 = self._dac_gains()
		if source == _SG_TRIG_ADC:
			adc_scale = g1 if ch == 1 else g2
			print(adc_scale)
			threshold = (trigger_threshold / adc_scale) * (2**17-1) / 2 / (2**11-1)
		elif source == _SG_TRIG_DAC:
			dac_scale = d1 if ch == 1 else d2
			threshold = trigger_threshold * (2**17-1)
		elif source == _SG_TRIG_EXT:
			threshold = 0
		elif source == _SG_TRIG_INTER:
			threshold = -2**17 + (internal_trig_high / internal_trig_period) * (2**18-1)
			if ch == 1:
				self._sweepmod1.step = 1/internal_trig_period / _SG_FREQSCALE
				#TODO: set other parameters? Stop, duration, etc?
			else:
				self._sweepmod2.step = 1/internal_trig_period / _SG_FREQSCALE

		# TODO: replace with amp modulation call function when implemented:
		if ch == 1:			
			self.mod_source_ch1 = 3
			self.gate_source_ch1 = source
			self.amod_enable_ch1 = 1
			self.mod_depth_ch1 = 2**31
			self.gate_thresh_ch1 = threshold
			self._sweep1.waitfortrig = 0

		elif ch == 2:
			self.mod_source_ch1 = 3
			self.gate_source_ch1 = 0
			self.amod_enable_ch1 = 1
			self.mod_depth_ch1 = 2**31
			self.gate_thresh_ch2 = threshold
			self._sweep2.waitfortrig = 0

	def _start_mode(self, ch, source, trigger_threshold):
		# Internal trigger source cannot be used for burst start mode:
		if source == _SG_TRIG_INTER:
			raise ValueOutOfRangeException("The internal trigger source cannot be used in start burst mode.")

		g1, g2 = self._adc_gains()
		d1, d2 = self._dac_gains()	
		if source == _SG_TRIG_ADC:
			threshold = trigger_threshold/g1 if ch == 1 else trigger_threshold/g2
		elif source == _SG_TRIG_DAC:
			threshold = trigger_threshold/d1 if ch == 1 else trigger_threshold/d2
		elif source == _SG_TRIG_EXT:
			threshold = 0

		if ch == 1:
			self._trigger1.level = threshold
			self.trig_source_ch1 = source
			self._sweep1.waitfortrig = 1
			self._sweep1.duration = 0
		elif ch == 2:
			self._trigger2.level = threshold
			self.trig_source_ch1 = source
			self._sweep2.waitfortrig = 1
			self._sweep2.duration = 0

	def _ncycle_mode(self, ch, channel_frequency, ncycles, trigger_threshold, source, internal_trig_period):
		# Waveform frequencies are restricted to <= 10 MHz in Ncycle burst mode:
		if channel_frequency > 10.0e6:
			raise ValueOutOfRangeException("Waveform frequencies are restricted to 10 MHz or less in Ncycle burst mode.")

		g1, g2 = self._adc_gains()
		d1, d2 = self._dac_gains()	
		if source == _SG_TRIG_ADC:
			threshold = trigger_threshold/g1 if ch == 1 else trigger_threshold/g2
		elif source == _SG_TRIG_DAC:
			threshold = trigger_threshold/d1 if ch == 1 else trigger_threshold/d2
		elif source == _SG_TRIG_EXT:
			threshold = 0
		elif source == _SG_TRIG_INTER:
			threshold = 0
			if ch == 1:
				self._set_sweepgenerator(self._sweepmod1, waveform = 0, waitfortrig = 1, frequency = 1/internal_trig_period, offset = 0, logsweep = 0, duration = 0)
			elif ch == 2:
				self._set_sweepgenerator(self._sweepmod2, waveform = 0, waitfortrig = 1, frequency = 1/internal_trig_period, offset = 0, logsweep = 0, duration = 0)

		# ensure combination of signal frequency and Ncycles doesn't cause 64 bit register overflow:	
		signal_period = 0 if channel_frequency == 0.0 else channel_frequency**-1
		FPGA_cycles = math.ceil(125e6 * signal_period * ncycles)
		if FPGA_cycles > 2**63-1:
			raise ValueOutOfRangeException("NCycle Register Overflow")

		if ch == 1:
			self._trigger1.level = threshold
			self.trig_source_ch1 = source
			self._sweep1.waitfortrig = 1
			self._sweep1.duration = FPGA_cycles
		elif ch == 2:
			self._trigger2.level = threshold
			self.trig_source_ch2 = source
			self._sweep2.waitfortrig = 1
			self._sweep2.duration = FPGA_cycles

	def _sweep_mode(self, ch, waveform, source, sweep_end_freq, channel_frequency, sweep_duration, trigger_threshold):
		# Pulse waveform edge must be minimum for gated burst mode and sweep mode:
		# still a constraint?
		if waveform != 0:
			if ch == 1 and self.ch1_edgetime_nonzero == True:
				raise ValueOutOfRangeException("Pulse waveform rise and fall times must be set to zero for gated burst mode and sweep mode.")
			if ch == 2 and self.ch2_edgetime_nonzero == True:
				raise ValueOutOfRangeException("Pulse waveform rise and fall times must be set to zero for gated burst mode and sweep mode.")

		g1, g2 = self._adc_gains()
		d1, d2 = self._dac_gains()	
		if source == _SG_TRIG_ADC:
			threshold = trigger_threshold/g1 if ch == 1 else trigger_threshold/g2
		elif source == _SG_TRIG_DAC:
			threshold = trigger_threshold/d1 if ch == 1 else trigger_threshold/d2
		elif source == _SG_TRIG_EXT:
			threshold == 0

		# TODO: implement negative sweeps, will require hdl changes
		modulating_start_freq = 0.5 * (2**64 - 1) # frequency modulating sweep starts at +0 Hz. When converted to signed on the FPGA, 0 has value 0.5 * (2**64 -1)
		modulating_finish_freq = (2**64 - 1)
		deltafreq_persecond = (sweep_end_freq - channel_frequency)/sweep_duration
		sweep_duration_FPGAcycles = math.floor(sweep_duration * 125e6)
		modulating_step_freq = 2**64 / 1e18 * deltafreq_persecond


		# deltafreq_persecond = (sweep_end_freq - channel_frequency)/sweep_duration
		# phasestep = 2**64 / 1e18 * deltafreq_persecond

		if ch == 1:
			self._sweep1.waitfortrig = 0
			self._sweepmod1.waitfortrig = 1
			self._sweepmod1.start = modulating_start_freq
			self._sweepmod1.stop = modulating_finish_freq
			self._sweepmod1.step = modulating_step_freq	
			self._sweepmod1.duration = sweep_duration_FPGAcycles	
			self._sweepmod1.waveform = 0
			self._sweepmod1.holdlast = 0
			self.amod_enable_ch1 = 0
			self.pmod_enable_ch1 = 0
			self.fmod_enable_ch1 = 0
			self.sweep_enable_ch1 = 1
		else:
			self._sweep2.waitfortrig = 0
			self._sweepmod2.waitfortrig = 1
			self._sweepmod2.start = modulating_start_freq
			self._sweepmod2.stop = modulating_finish_freq
			self._sweepmod2.step = modulating_step_freq
			self._sweepmod2.duration = sweep_duration_FPGAcycles
			self._sweepmod2.waveform = 0
			self._sweepmod2.holdlast = 0
			self.amod_enable_ch2 = 0
			self.pmod_enable_ch2 = 0
			self.fmod_enable_ch2 = 0
			self.sweep_enable_ch2 = 1

		# if source == _SG_TRIG_INTER:
		# 	if ch == 1:
		# 		self._sweepmod1.waitfortrig = 0
		# 		self._sweepmod1.duration = 0
		# 	else:
		# 		self._sweepmod2.waitfortrig = 0
		# 		self._sweepmod2.duration = sweep_duration_FPGAcycles
		# else:
		# 	if ch == 1:
		# 		self._sweepmod1.waitfortrig = 1
		# 		self._sweepmod1.duration = 3*125e6
		# 	else:
		# 		self._sweepmod2.waitfortrig = 1
		# 		self._sweepmod2.duration = sweep_duration_FPGAcycles

	@needs_commit
	def gen_trigger_off(self, ch=None):
		"""
		Turn off trigger/sweep mode for the specified output channel.

		If *ch* is None (the default), both channels will be turned off,
		otherwise just the one specified by the argument.

		:type ch: int; {1,2} or None
		:param ch: Output channel to turn trigger/sweep mode off
		"""
		_utils.check_parameter_valid('set', ch, [1,2],'output channel', allow_none=True)

		if ch==1:
			self.trig_sweep_mode_ch1 = 0
		elif ch==2:
			self.trig_sweep_mode_ch2 = 0
		else:
			self.trig_sweep_mode_ch1 = 0
			self.trig_sweep_mode_ch2 = 0

	@needs_commit
	def gen_modulate_off(self, ch=None):
		"""
		Turn off modulation for the specified output channel.

		If *ch* is None (the default), both channels will be turned off,
		otherwise just the one specified by the argument.

		:type ch: int; {1,2} or None
		:param ch: Output channel to turn modulation off.
		"""
		# Disable modulation by clearing modulation type bits
		_utils.check_parameter_valid('set', ch, [1,2],'output channel', allow_none=True)

		if ch==1:
			self.out1_modulation = 0
		if ch==2:
			self.out2_modulation = 0

	@needs_commit
	def gen_modulate(self, ch, mtype, source, depth, frequency=0.0):
		"""
		Set up modulation on an output channel.

		:type ch: int; {1,2}
		:param ch: Channel to modulate

		:type mtype: string, {amplitude', 'frequency', 'phase'}
		:param mtype:  Modulation type. Respectively Off, Amplitude, Frequency and Phase modulation.

		:type source: string, {'internal', 'in', 'out'}
		:param source: Modulation source. Respectively Internal Sinewave, associated input channel or opposite output channel.

		:type depth: float 0-1, 0-125MHz or 0 - 360 deg
		:param depth: Modulation depth (depends on modulation type): Fractional modulation depth, Frequency Deviation/Volt or Phase shift

		:type frequency: float
		:param frequency: Frequency of internally-generated sine wave modulation. This parameter is ignored if the source is set to ADC or DAC.

		:raises ValueOutOfRangeException: if the channel number is invalid or modulation parameters can't be achieved
		"""
		_utils.check_parameter_valid('set', ch, [1,2],'output modulation channel')
		_utils.check_parameter_valid('range', frequency, [0,250e6],'internal modulation frequency')

		# Can't use trigger/sweep modes at the same time as modulation
		self.gen_trigger_off(ch)

		_str_to_modsource = {
			'in'		: _SG_MOD_ADC,
			'out'		: _SG_MOD_DAC,
			'internal'  : _SG_MOD_INTER,
			'gate'		: _SG_MOD_GATE
		}
		_str_to_modtype = {
			'amplitude' : _SG_MOD_AMPL,
			'frequency' : _SG_MOD_FREQ,
			'phase'	: _SG_MOD_PHASE
		}
		source = _utils.str_to_val(_str_to_modsource, source, 'modulation source')
		mtype = _utils.str_to_val(_str_to_modtype, mtype, 'modulation source')

		# Calculate the depth value depending on modulation source and type
		depth_parameter = 0.0
		if mtype == _SG_MOD_AMPL:
			_utils.check_parameter_valid('range', depth, [0.0,1.0], 'amplitude modulation depth', 'fraction')
			depth_parameter = depth
		elif mtype == _SG_MOD_FREQ:
			_utils.check_parameter_valid('range', depth, [0.0,_SG_MOD_FREQ_MAX], 'frequency modulation depth', 'Hz/V')
			depth_parameter = depth/(DAC_SMP_RATE/8.0)
		elif mtype == _SG_MOD_PHASE:
			_utils.check_parameter_valid('range', depth, [0.0, 360.0], 'phase modulation depth', 'degrees/V')
			depth_parameter = depth/360.0

		# Get the calibration coefficients of the front end and output
		dac1, dac2 = self._dac_gains()
		adc1, adc2 = self._adc_gains()

		if ch == 1:
			self.mod_source_ch1 = source
			self.amod_enable_ch1 = 1 if mtype == _SG_MOD_AMPL else 0
			self.fmod_enable_ch1 = 1 if mtype == _SG_MOD_FREQ else 0
			self.pmod_enable_ch1 = 1 if mtype == _SG_MOD_PHASE else 0
			if source == _SG_MOD_INTER:
				self._set_sweepgenerator(self._sweepmod1, waveform = 2, waitfortrig = 0, frequency = frequency, offset = 0, logsweep = 0, duration = 0)
			self.adc1_statuslight = True if source == _SG_MODSOURCE_ADC else False
		elif ch == 2:
			self.mod_source_ch2 = source
			self.amod_enable_ch2 = 1 if mtype == _SG_MOD_AMPL else 0
			self.fmod_enable_ch2 = 1 if mtype == _SG_MOD_FREQ else 0
			self.pmod_enable_ch2 = 1 if mtype == _SG_MOD_PHASE else 0
			if source == _SG_MOD_INTER:
				self._set_sweepgenerator(self._sweepmod2, waveform = 2, waitfortrig = 0, frequency = frequency, offset = 0, logsweep = 0, duration = 0)
			self.adc2_statuslight = True if source == _SG_MODSOURCE_ADC else False

		front_end = self._get_frontend(channel = 1) if ch == 1 else self._get_frontend(channel = 2)
		atten = 10.0 if front_end[1] else 1.0

		# Calibrate the depth value depending on the source
		if(source == _SG_MOD_INTER):
			depth_parameter *= 1.0 # No change in depth
		elif(source == _SG_MOD_DAC):
			# Opposite DAC is used
			depth_parameter = depth_parameter #* 30000 * (dac2 if ch == 1 else dac1)
		elif(source == _SG_MOD_ADC):
			# Associated ADC for current channel
			depth_parameter = depth_parameter * 3750 / atten * (adc1 if ch == 1 else adc2)

		if ch == 1:
			self.mod_depth_ch1 = (pow(2.0, 31.0) - 1) * depth_parameter
		elif ch == 2:
			self.mod_depth_ch2 = (pow(2.0, 31.0) - 1) * depth_parameter

	def commit(self):
		#self._update_dependent_regs()

		# Commit the register values to the device
		super(WaveformGenerator, self).commit()


	# Bring in the docstring from the superclass for our docco.
	commit.__doc__ = MokuInstrument.commit.__doc__

_siggen_reg_handlers = {
	'enable_ch1':		(REG_WG_CONTROL,	to_reg_unsigned(0,1),		from_reg_unsigned(0,1)),
	'trig_source_ch1':	(REG_WG_CONTROL,	to_reg_unsigned(1,2),		from_reg_unsigned(1,2)),
	'sweep_enable_ch1':	(REG_WG_CONTROL,	to_reg_unsigned(4,1),		from_reg_unsigned(4,1)),
	'mod_source_ch1':	(REG_WG_CONTROL,	to_reg_unsigned(6,2),		from_reg_unsigned(6,2)),
	'gate_source_ch1':	(REG_WG_CONTROL,	to_reg_unsigned(8,2),		from_reg_unsigned(8,2)),
	'amod_enable_ch1':	(REG_WG_CONTROL,	to_reg_unsigned(10,1),		from_reg_unsigned(10,1)),
	'fmod_enable_ch1':	(REG_WG_CONTROL,	to_reg_unsigned(11,1),		from_reg_unsigned(11,1)),
	'pmod_enable_ch1':	(REG_WG_CONTROL,	to_reg_unsigned(12,1),		from_reg_unsigned(12,1)),
	'waveform_type_ch1':(REG_WG_CONTROL,	to_reg_unsigned(13,2),		from_reg_unsigned(13,2)),
	'mod_depth_ch1':	(REG_WG_MODDEPTH_CH1, 	to_reg_unsigned(0,32),	from_reg_signed(0,32)),
	'gate_thresh_ch1':	(REG_WG_GATETHRESH_CH1, to_reg_signed(0,18),	from_reg_signed(0,18)),
	'amplitude_ch1':	(REG_WG_AMP_CH1,	to_reg_signed(0,18),		from_reg_signed(0,18)),
	'offset_ch1': 		(REG_WG_OFFSET_CH1,	to_reg_signed(0,16),		from_reg_signed(0,16)),

	'temp_phase':		(REG_WG_TEMPPHASE, to_reg_signed(0,32),			from_reg_signed(0,32)),

	't0_ch1':			(REG_WG_SQRT0_CH1,		to_reg_unsigned(0, 32, xform=lambda obj, o: o / _SG_TIMESCALE),
											from_reg_unsigned(0, 32, xform=lambda obj, o: o * _SG_TIMESCALE)),
	't1_ch1':			(REG_WG_SQRT1_CH1,		to_reg_unsigned(0, 32, xform=lambda obj, o: o / _SG_TIMESCALE),
											from_reg_unsigned(0, 32, xform=lambda obj, o: o * _SG_TIMESCALE)),
	't2_ch1':			(REG_WG_SQRT2_CH1,		to_reg_unsigned(0, 32, xform=lambda obj, o: o / _SG_TIMESCALE) ,
											from_reg_unsigned(0, 32, xform=lambda obj, o: o * _SG_TIMESCALE)),
	'fallrate_ch2':		((REG_WG_FALLRATEH_CH1, REG_WG_FALLRATEL_CH1),
											lambda obj, f, old: ((old[0] & 0x0000FFFF) | (_usgn(f/_SG_FREQSCALE, 48) >> 16) & 0xFFFF0000, _usgn(f/_SG_FREQSCALE, 48) & 0xFFFFFFFF),
											lambda obj, rval: _SG_FREQSCALE * ((rval[0] & 0xFFFF0000) << 16 | rval[1])),
	'riserate_ch2':		((REG_WG_RISERATEH_CH1, REG_WG_RISERATEL_CH1),
											to_reg_unsigned(0, 48, xform=lambda obj, r: r / _SG_FREQSCALE),
											from_reg_unsigned(0, 48, xform=lambda obj, r: r * _SG_FREQSCALE)),

	'enable_ch2':		(REG_WG_CONTROL,	to_reg_unsigned(15,1),		from_reg_unsigned(15,1)),
	'trig_source_ch2':	(REG_WG_CONTROL,	to_reg_unsigned(16,2),		from_reg_unsigned(16,2)),
	'sweep_enable_ch2':	(REG_WG_CONTROL,	to_reg_unsigned(19,1),		from_reg_unsigned(19,1)),
	'mod_source_ch2':	(REG_WG_CONTROL,	to_reg_unsigned(21,2),		from_reg_unsigned(21,2)),
	'gate_source_ch2':	(REG_WG_CONTROL,	to_reg_unsigned(23,2),		from_reg_unsigned(23,2)),
	'amod_enable_ch2':	(REG_WG_CONTROL,	to_reg_unsigned(25,1),		from_reg_unsigned(25,1)),
	'fmod_enable_ch2':	(REG_WG_CONTROL,	to_reg_unsigned(26,1),		from_reg_unsigned(26,1)),
	'pmod_enable_ch2':	(REG_WG_CONTROL,	to_reg_unsigned(27,1),		from_reg_unsigned(27,1)),
	'waveform_type_ch2':(REG_WG_CONTROL,	to_reg_unsigned(28,2),		from_reg_unsigned(28,2)),
	'mod_depth_ch2':	(REG_WG_MODDEPTH_CH2, 	to_reg_unsigned(0,32),	from_reg_unsigned(0,32)),
	'gate_thresh_ch2':	(REG_WG_GATETHRESH_CH2, to_reg_signed(0,16),	from_reg_signed(0,16)),
	'amplitude_ch2':	(REG_WG_AMP_CH2,	to_reg_signed(0,18),		from_reg_signed(0,18)),
	'offset_ch2': 		(REG_WG_OFFSET_CH2,	to_reg_signed(0,16),		from_reg_signed(0,16))

	# 'trig_type_ch1':	()
	# 'trig_edgedir_ch1'
	# 'trig_pwidth_type_ch1'
	# 'trig_level_ch1'
	# 'trig_hyst_ch1'
	# 'trig_duration_ch1'
	# 'trig_holdoff_ch1'
	# 'trig_ntrigger_ch1'
	# 'trig_ntriggermode_ch1'
	# 'trig_timer'
	# 'trig_autoholdoff_ch1'

	# 'swp_waveform_ch1':		(REG_WG_SWEEPCTRL_CH1,	to_reg_unsigned(0,2),	from_reg_unsigned(0,2)),
	# 'swp_logsweep_ch1':		(REG_WG_SWEEPCTRL_CH1,	to_reg_unsigned(5,1),	from_reg_unsigned(5,1)),
	# 'swp_startvalue_ch1':	((REG_WG_SWEEPSTRTH_CH1,REG_WG_SWEEPSTRTL_CH1),	to_reg_unsigned(0,64),	from_reg_unsigned(0,64)),
	# 'swp_stopvalue_ch1':	((REG_WG_SWEEPSTOPH_CH1,REG_WG_SWEEPSTOPL_CH1),	to_reg_unsigned(0,64),	from_reg_unsigned(0,64)),
	# 'swp_step_ch1':			((REG_WG_SWEEPSTEPH_CH1,REG_WG_SWEEPSTEPL_CH1),	to_reg_unsigned(0,64),	from_reg_unsigned(0,64)),
	# 'swp_duration_ch1':		((REG_WG_SWEEPDURH_CH1,REG_WG_SWEEPDURL_CH1),	to_reg_unsigned(0,64),	from_reg_unsigned(0,64))

}

_siggen_mod_reg_handlers = {}

# _siggen_mod_reg_handlers = {
# 	'out1_modulation':	(REG_SG_WAVEFORMS,	to_reg_unsigned(16, 8, allow_range=[_SG_MOD_NONE, _SG_MOD_AMPL | _SG_MOD_FREQ | _SG_MOD_PHASE]),
# 											from_reg_unsigned(16, 8)),

# 	'out2_modulation':	(REG_SG_WAVEFORMS,	to_reg_unsigned(24, 8, allow_range=[_SG_MOD_NONE, _SG_MOD_AMPL | _SG_MOD_FREQ | _SG_MOD_PHASE]),
# 											from_reg_unsigned(24, 8)),

# 	'mod1_frequency':	((REG_SG_MODF1_H, REG_SG_MODF1_L),
# 											lambda obj, f, old: ((old[0] & 0x0000FFFF) | (_usgn(f/_SG_FREQSCALE, 48) >> 16) & 0xFFFF0000, _usgn(f/_SG_FREQSCALE, 48) & 0xFFFFFFFF),
# 											lambda obj, rval: _SG_FREQSCALE * ((rval[0] & 0xFFFF0000) << 16 | rval[1])),

# 	'mod2_frequency':	((REG_SG_MODF2_H, REG_SG_MODF2_L),
# 											lambda obj, f, old: ((old[0] & 0x0000FFFF) | (_usgn(f/_SG_FREQSCALE, 48) >> 16) & 0xFFFF0000, _usgn(f/_SG_FREQSCALE, 48) & 0xFFFFFFFF),
# 											lambda obj, rval: _SG_FREQSCALE * ((rval[0] & 0xFFFF0000) << 16 | rval[1])),
# 	# The meaning of this amplitude field is complicated enough that the conversion to register value is done in the
# 	# main code above rather than inline
# 	'mod1_amplitude':	(REG_SG_MODA1,		to_reg_unsigned(0, 32),
# 											from_reg_unsigned(0, 32)),

# 	'mod2_amplitude':	(REG_SG_MODA2,		to_reg_unsigned(0, 32),
# 											from_reg_unsigned(0, 32)),

# 	'out1_modsource':	(REG_SG_MODSOURCE,	to_reg_unsigned(1, 2, allow_set=[_SG_MODSOURCE_INT, _SG_MODSOURCE_ADC, _SG_MODSOURCE_DAC]),
# 											from_reg_unsigned(1, 2)),

# 	'out2_modsource':	(REG_SG_MODSOURCE,	to_reg_unsigned(3, 2, allow_set=[_SG_MODSOURCE_INT, _SG_MODSOURCE_ADC, _SG_MODSOURCE_DAC]),
# 											from_reg_unsigned(3, 2))
# }

# _siggen_reg_handlers = {
# 	'out1_enable':		(REG_SG_WAVEFORMS,	to_reg_bool(0),		from_reg_bool(0)),
# 	'out2_enable':		(REG_SG_WAVEFORMS,	to_reg_bool(1),		from_reg_bool(1)),

# 	'out1_waveform':	(REG_SG_WAVEFORMS,	to_reg_unsigned(4, 3, allow_set=[_SG_WAVE_SINE, _SG_WAVE_SQUARE, _SG_WAVE_TRIANGLE, _SG_WAVE_DC, _SG_WAVE_PULSE]),
# 											from_reg_unsigned(4, 3)),

# 	'out2_waveform':	(REG_SG_WAVEFORMS,	to_reg_unsigned(8, 3, allow_set=[_SG_WAVE_SINE, _SG_WAVE_SQUARE, _SG_WAVE_TRIANGLE, _SG_WAVE_DC, _SG_WAVE_PULSE]),
# 											from_reg_unsigned(8, 3)),

# 	'out1_clipsine':	(REG_SG_WAVEFORMS,	to_reg_bool(7),		from_reg_bool(7)),
# 	'out2_clipsine':	(REG_SG_WAVEFORMS,	to_reg_bool(11),		from_reg_bool(11)),
# 	'out1_frequency':	((REG_SG_FREQ1_H, REG_SG_FREQ1_L),
# 											to_reg_unsigned(0, 48, xform=lambda obj, f:f / _SG_FREQSCALE),
# 											from_reg_unsigned(0, 48, xform=lambda obj, f: f * _SG_FREQSCALE)),

# 	'out2_frequency':	((REG_SG_FREQ2_H, REG_SG_FREQ2_L),
# 											to_reg_unsigned(0, 48, xform=lambda obj, f:f / _SG_FREQSCALE),
# 											from_reg_unsigned(0, 48, xform=lambda obj, f: f * _SG_FREQSCALE)),

# 	'out1_offset':		(REG_SG_MODF1_H,	to_reg_signed(0, 16, xform=lambda obj, o:o / obj._dac_gains()[0]),
# 											from_reg_signed(0, 16, xform=lambda obj, o: o * obj._dac_gains()[0])),

# 	'out2_offset':		(REG_SG_MODF2_H,	to_reg_signed(0, 16, xform=lambda obj, o:o / obj._dac_gains()[1]),
# 											from_reg_signed(0, 16, xform=lambda obj, o: o * obj._dac_gains()[1])),

# 	'out1_phase':		(REG_SG_PHASE1,		to_reg_unsigned(0, 32, xform=lambda obj, p: (p / _SG_PHASESCALE) % (2**32)),
# 											from_reg_unsigned(0, 32, xform=lambda obj, p:p * _SG_PHASESCALE)),

# 	'out2_phase':		(REG_SG_PHASE2,		to_reg_unsigned(0, 32, xform=lambda obj, p: (p / _SG_PHASESCALE) % (2**32)),
# 											from_reg_unsigned(0, 32, xform=lambda obj, p:p * _SG_PHASESCALE)),

# 	'out1_amplitude':	(REG_SG_AMP1,		to_reg_unsigned(0, 16, xform=lambda obj, a:a / obj._dac_gains()[0]),
# 											from_reg_unsigned(0, 16, xform=lambda obj, a:a * obj._dac_gains()[0])),

# 	'out2_amplitude':	(REG_SG_AMP2,		to_reg_unsigned(0, 16, xform=lambda obj, a:a / obj._dac_gains()[1]),
# 											from_reg_unsigned(0, 16, xform=lambda obj, a:a * obj._dac_gains()[1])),

# 	'out1_t0':			(REG_SG_T01,		to_reg_unsigned(0, 32, xform=lambda obj, o: o / _SG_TIMESCALE),
# 											from_reg_unsigned(0, 32, xform=lambda obj, o: o * _SG_TIMESCALE)),

# 	'out1_t1':			(REG_SG_T11,		to_reg_unsigned(0, 32, xform=lambda obj, o: o / _SG_TIMESCALE),
# 											from_reg_unsigned(0, 32, xform=lambda obj, o: o * _SG_TIMESCALE)),

# 	'out1_t2':			(REG_SG_T21,		to_reg_unsigned(0, 32, xform=lambda obj, o: o / _SG_TIMESCALE) ,
# 											from_reg_unsigned(0, 32, xform=lambda obj, o: o * _SG_TIMESCALE)),

# 	'out2_t0':			(REG_SG_T02,		to_reg_unsigned(0, 32, xform=lambda obj, o: o / _SG_TIMESCALE),
# 											from_reg_unsigned(0, 32, xform=lambda obj, o: o * _SG_TIMESCALE)),

# 	'out2_t1':			(REG_SG_T12,		to_reg_unsigned(0, 32, xform=lambda obj, o: o / _SG_TIMESCALE),
# 											from_reg_unsigned(0, 32, xform=lambda obj, o: o * _SG_TIMESCALE )),

# 	'out2_t2':			(REG_SG_T22,		to_reg_unsigned(0, 32, xform=lambda obj, o: o / _SG_TIMESCALE ),
# 											from_reg_unsigned(0, 32, xform=lambda obj, o: o * _SG_TIMESCALE )),

# 	'out1_riserate':	((REG_SG_RFRATE1_H, REG_SG_RISERATE1_L),
# 											to_reg_unsigned(0, 48, xform=lambda obj, r: r / _SG_FREQSCALE),
# 											from_reg_unsigned(0, 48, xform=lambda obj, r: r * _SG_FREQSCALE)),

# 	'out1_fallrate':	((REG_SG_RFRATE1_H, REG_SG_FALLRATE1_L),
# 											lambda obj, f, old: ((old[0] & 0x0000FFFF) | (_usgn(f/_SG_FREQSCALE, 48) >> 16) & 0xFFFF0000, _usgn(f/_SG_FREQSCALE, 48) & 0xFFFFFFFF),
# 											lambda obj, rval: _SG_FREQSCALE * ((rval[0] & 0xFFFF0000) << 16 | rval[1])),

# 	'out2_riserate':	((REG_SG_RFRATE2_H, REG_SG_RISERATE2_L),
# 											to_reg_unsigned(0, 48, xform=lambda obj, r: r / _SG_FREQSCALE),
# 											from_reg_unsigned(0, 48, xform=lambda obj, r: r * _SG_FREQSCALE)),

# 	'out2_fallrate':	((REG_SG_RFRATE2_H, REG_SG_FALLRATE2_L),
# 											lambda obj, f, old: ((old[0] & 0x0000FFFF) | (_usgn(f/_SG_FREQSCALE, 48) >> 16) & 0xFFFF0000, _usgn(f/_SG_FREQSCALE, 48) & 0xFFFFFFFF),
# 											lambda obj, rval: _SG_FREQSCALE * ((rval[0] & 0xFFFF0000) << 16 | rval[1])),

# 	'out1_amp_pc':		(REG_SG_PRECLIP,	to_reg_unsigned(0, 16, xform=lambda obj, a: a / obj._dac_gains()[0]),
# 											from_reg_unsigned(0, 16, xform=lambda obj, a: a * obj._dac_gains()[0])),

# 	'out2_amp_pc':		(REG_SG_PRECLIP,	to_reg_unsigned(16, 16, xform=lambda obj, a: a / obj._dac_gains()[1]),
# 											from_reg_unsigned(16, 16, xform=lambda obj, a: a * obj._dac_gains()[1])),
# 	'internal_trig_increment_ch1':	((REG_SG_TrigPeriodInternalCH0_H, REG_SG_TrigPeriodInternalCH0_L),
# 											to_reg_unsigned(0,64), from_reg_unsigned(0,64)),

# 	'internal_trig_increment_ch2':	((REG_SG_TrigPeriodInternalCH1_H, REG_SG_TrigPeriodInternalCH1_L),
# 											to_reg_unsigned(0,64), from_reg_unsigned(0,64)),

# 	'internal_trig_dutytarget_ch1': ((REG_SG_TrigDutyInternalCH0_H, REG_SG_TrigDutyInternalCH0_L),
# 											to_reg_unsigned(0,64), from_reg_unsigned(0,64)),

# 	'internal_trig_dutytarget_ch2': ((REG_SG_TrigDutyInternalCH1_H, REG_SG_TrigDutyInternalCH1_L),
# 											to_reg_unsigned(0,64), from_reg_unsigned(0,64)),

# 	'trig_ADC_threshold_ch1':		(REG_SG_ADCThreshold, 	to_reg_signed(0,12), from_reg_signed(0,12)),

# 	'trig_ADC_threshold_ch2':		(REG_SG_ADCThreshold, 	to_reg_signed(12,12), from_reg_signed(12,12)),

# 	'trig_DAC_threshold_ch1':		(REG_SG_DACThreshold, 	to_reg_signed(0,16), from_reg_signed(0,16)),

# 	'trig_DAC_threshold_ch2':		(REG_SG_DACThreshold, 	to_reg_signed(16,16), from_reg_signed(16,16)),

# 	'mode':	(REG_SG_TrigSweepMode, 	to_reg_unsigned(0,3), from_reg_unsigned(0,3)),

# 	'trig_sweep_mode_ch2':	(REG_SG_TrigSweepMode, 	to_reg_unsigned(3,3), from_reg_unsigned(3,3)),

# 	'trigger_select_ch1':	(REG_SG_TrigSweepMode, 	to_reg_unsigned(6,2), from_reg_unsigned(6,2)),

# 	'trigger_select_ch2':	(REG_SG_TrigSweepMode, 	to_reg_unsigned(8,2), from_reg_unsigned(8,2)),

# 	'sweep_length_ch1':	((REG_SG_SweepLengthCh0_H, REG_SG_SweepLengthCh0_L),
# 											to_reg_unsigned(0,64), from_reg_unsigned(0,64)),

# 	'sweep_length_ch2':	((REG_SG_SweepLengthCh1_H, REG_SG_SweepLengthCh1_L),
# 											to_reg_unsigned(0,64), from_reg_unsigned(0,64)),

# 	'sweep_init_freq_ch1':	((REG_SG_SweepInitFreqCh0_H, REG_SG_SweepInitFreqCh0_L),
# 											to_reg_unsigned(0,48), from_reg_unsigned(0,48)),

# 	'sweep_init_freq_ch2':	((REG_SG_SweepInitFreqCh1_H, REG_SG_SweepInitFreqCh1_L),
# 											to_reg_unsigned(0,48), from_reg_unsigned(0,48)),

# 	'sweep_increment_ch1':	((REG_SG_SweepIncrementCh0_H, REG_SG_SweepIncrementCh0_L),
# 											to_reg_signed(0,64), from_reg_signed(0,64)),

# 	'sweep_increment_ch2':	((REG_SG_SweepIncrementCh1_H, REG_SG_SweepIncrementCh1_L),
# 											to_reg_signed(0,64), from_reg_signed(0,64)),

# 	'ncycles_period_ch1':	((REG_SG_NCycles_TrigDutyCH0_H, REG_SG_NCycles_TrigDutyCH0_L),
# 											to_reg_unsigned(0,64), from_reg_unsigned(0,64)),

# 	'ncycles_period_ch2':	((REG_SG_NCycles_TrigDutyCH1_H, REG_SG_NCycles_TrigDutyCH1_L),
# 											to_reg_unsigned(0,64), from_reg_unsigned(0,64)),

# 	'adc1_statuslight':	(REG_SG_MODSOURCE,	to_reg_unsigned(5, 1),
# 											from_reg_unsigned(5, 1)),

# 	'adc2_statuslight':	(REG_SG_MODSOURCE,	to_reg_unsigned(6, 1),
# 											from_reg_unsigned(6, 1))
# }
