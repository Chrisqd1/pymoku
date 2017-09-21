
import math
import logging

from ._instrument import *
from ._instrument import _usgn, _sgn
from . import _utils

log = logging.getLogger(__name__)

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

_SG_FREQSCALE		= 1e9 / 2**48
_SG_PHASESCALE		= 360.0 / (2**32) # Wraps
_SG_RISESCALE		= 1e9 / 2**48
_SG_AMPSCALE		= 4.0 / (2**15 - 1)
_SG_DEPTHSCALE		= 1.0 / 2**15
_SG_MAX_RISE		= 1e9 - 1
_SG_TIMESCALE 		= 1.0 / (2**32 - 1) # Doesn't wrap

_SG_MOD_FREQ_MAX 	= 62.5e6 # Hz
_SG_SQUARE_CLIPSINE_THRESH = 25e3 # Hz

_SG_TRIG_EXT 		= 0
_SG_TRIG_ADC		= 1
_SG_TRIG_DAC		= 2
_SG_TRIG_INTER		= 3

_SG_TRIG_MODE_OFF 	= 0
_SG_TRIG_MODE_GATE	= 1
_SG_TRIG_MODE_START = 2
_SG_TRIG_MODE_NCYCLE= 3
_SG_TRIG_MODE_SWEEP = 4

class BasicWaveformGenerator(MokuInstrument):
	"""

	.. automethod:: pymoku.instruments.WaveformGenerator.__init__

	.. attribute:: type
		:annotation: = "signal_generator"

		Name of this instrument.

	"""
	def __init__(self):
		""" Create a new WaveformGenerator instance, ready to be attached to a Moku."""
		super(BasicWaveformGenerator, self).__init__()
		self._register_accessors(_siggen_reg_handlers)

		self.id = 4
		self.type = "signal_generator"

	@needs_commit
	def set_defaults(self):
		""" Set sane defaults.
		Defaults are outputs off, amplitudes and frequencies zero.
		"""
		super(BasicWaveformGenerator, self).set_defaults()
		self.out1_enable = True
		self.out2_enable = True
		self.out1_amplitude = 0
		self.out2_amplitude = 0
		self.out1_frequency = 0
		self.out2_frequency = 0

		# Disable inputs on hardware that supports it
		self.en_in_ch1 = True
		self.en_in_ch2 = True
		self.TrigSweepMode_Ch0 = _SG_TRIG_MODE_OFF
		self.TrigSweepMode_Ch1 = _SG_TRIG_MODE_OFF

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
			self.out1_enable = True
			self.out1_amplitude = amplitude
			self.out1_frequency = frequency
			self.out1_offset = offset
			self.out1_phase =  phase
		elif ch == 2:
			self.out2_waveform = _SG_WAVE_SINE
			self.out2_enable = True
			self.out2_amplitude = amplitude
			self.out2_frequency = frequency
			self.out2_offset = offset
			self.out2_phase = phase

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

		if ch == 1:
			self.out1_waveform = _SG_WAVE_SQUARE
			self.out1_enable = True
			self.out1_amplitude = amplitude
			self.out1_frequency = frequency
			self.out1_offset = offset
			self.out1_clipsine = False # TODO: Should switch to clip depending on freq or user

			# This is overdefined, but saves the FPGA doing a tricky division
			self.out1_t0 = risetime
			self.out1_t1 = duty
			self.out1_t2 = duty + falltime
			self.out1_riserate = frequency / risetime if risetime else _SG_MAX_RISE
			self.out1_fallrate = frequency / falltime if falltime else _SG_MAX_RISE
			self.out1_phase =  phase
		elif ch == 2:
			self.out2_waveform = _SG_WAVE_SQUARE
			self.out2_enable = True
			self.out2_amplitude = amplitude
			self.out2_frequency = frequency
			self.out2_offset = offset
			self.out2_clipsine = False
			self.out2_t0 = risetime
			self.out2_t1 = duty
			self.out2_t2 = duty + falltime
			self.out2_riserate = frequency / risetime if risetime else _SG_MAX_RISE
			self.out2_fallrate = frequency / falltime if falltime else _SG_MAX_RISE
			self.out2_phase = phase

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

	@needs_commit	
	def set_trigger_threshold(self, ch, dac=0.0, adc=0.0):
		""" Configure the ADC and DAC trigger thresholds.

		:type ch: int; {1,2}
		:param ch: Channel to set.
		
		:type dac : int
		:param dac: dac source to configure threshold. -2**15 <= thresh <= 2**15-1 ..... -1V <= thresh <= 1V

		:type adc : int
		:param adc: adc source to configure threshold. -2**11 <= thresh <= 2**11-1 ..... -10V <= thresh <= 10V
		"""
		_utils.check_parameter_valid('set', ch, [1,2],'output channel', allow_none=True)
		_utils.check_parameter_valid('range', dac, [-1.0,1.0],'dac trigger threshold','volts')
		_utils.check_parameter_valid('range', adc, [-10.0,10.0],'adc trigger threshold','volts') ##### CHANGE TO VOLTS AND FIND MAX/MIN FOR ADC AND DAC

		#get ADC calibration coefficients:
		a1, a2 = self._adc_gains()

		if ch == 1:
			self.TrigADCThreshold_Ch0 = adc / a1
			self.TrigDACThreshold_Ch0 = dac * 2**15-1
		if ch == 2:
			self.TrigADCThreshold_Ch1 = adc / a2
			self.TrigDACThreshold_Ch1 = dac * 2**15-1


	def set_trigger_source(self, ch, TriggerSource = 0, InternalTrigPeriod = 1.0, InternalTrigDuty = 0.4):
		""" Configure trigger source for target channel.

		:type ch : int
		:param ch: target channel

		:type TiggerSource: string, {'external','adc','dac','internal'}
		:param source: Trigger Source. Value corresponds to one of four available trigger sources.

		:type InternalTrigPeriod : float, seconds
		:param InternalTrigPeriod : period in seconds of the internal trigger

		:type InternalTrigDuty : float, seconds
		:param InternalTrigDuty : value in seconds of the trigger duty period. Duty cycle is defined as InternalTrigDuty/InternalTrigPeriod	

		"""
		_utils.check_parameter_valid('set', ch, [1,2],'output channel')
		_utils.check_parameter_valid('range', InternalTrigPeriod, [0,1e11],'internal trigger period','seconds')
		_utils.check_parameter_valid('range', InternalTrigDuty, [0.0,1.0],'output channel','fraction')

		_str_to_trigger_source = {
			'external' : _SG_TRIG_EXT,
			'adc' : _SG_TRIG_ADC,
			'dac' : _SG_TRIG_DAC,
			'internal' : _SG_TRIG_INTER
		}

		source = _utils.str_to_val(_str_to_trigger_source, TriggerSource, 'trigger source')

		PeriodFPGACycles = math.ceil(125e6 * InternalTrigPeriod)
		DutyFPGACycles = math.ceil(125e6 * InternalTrigDuty)
		
		if ch == 1:
			self.TriggerSelect_Ch0 = source
			if source == _SG_TRIG_INTER:
				self.InternalTrigPeriod_Ch0 = PeriodFPGACycles	
				self.NCycles_TrigDuty_Ch0 = DutyFPGACycles
		elif ch == 2:
			self.TriggerSelect_Ch1 = source
			if source == _SG_TRIG_INTER:
				self.InternalTrigPeriod_Ch1 = PeriodFPGACycles	
				self.NCycles_TrigDuty_Ch1 = DutyFPGACycles

	def set_trigger_mode(self, ch, mode, SignalFreq=0.0, NCycles = 1, SweepInitFreq = 1.0, SweepFinalFreq = 5.0, SweepDuration = 1.0, Waveform = 'sine'):
		""" Configure gated trigger mode on target channel

		:type ch : int
		:param ch: target channel

		:type mode: string , {'gateway', 'startmode', 'ncycle', 'sweep'}
		:param mode: Select the mode in which the trigger is operated

		:type SignalFreq : float, hertz
		:param SignalFreq : signal frequency, used to find signal period and to determine requisite number of FPGA cycles

		:type NCycles : int
		:param NCycles : integer number of signal periods 

		:type SweepInitFreq : float, hertz
		:param SweepInitFreq : starting sweep frequency

		:type SweepFinalFreq : float, hertz
		:param SweepFinalFreq : finishing sweep frequency

		:type SweepDuration : float, seconds
		:param SweepDuration : sweep duration in seconds

		"""
		_utils.check_parameter_valid('set', ch, [1,2],'output channel')
		_utils.check_parameter_valid('range', SignalFreq, [0,10e6],'signal frequency','frequency')
		_utils.check_parameter_valid('range', NCycles, [0,1e18],'output channel','frequency')
		_utils.check_parameter_valid('set', ch, [1,2],'output channel')
		_utils.check_parameter_valid('set', Waveform, ['sine', 'square', 'pulse', 'ramp'],'waveform type')
		_utils.check_parameter_valid('range', SweepDuration, [0.0,1000.0],'sweep duration','seconds')

		if Waveform == 'sine':
			_utils.check_parameter_valid('range', SweepInitFreq, [0.0,250.0e6],'sweep starting frequency','frequency')
			_utils.check_parameter_valid('range', SweepFinalFreq, [0.0,250.0e6],'sweep finishing frequency','frequency')
		else:
			_utils.check_parameter_valid('range', SweepInitFreq, [0.0,100.0e6],'sweep starting frequency','frequency')
			_utils.check_parameter_valid('range', SweepFinalFreq, [0.0,100.0e6],'sweep finishing frequency','frequency')

		_str_to_trigger_mode = {
			'gateway' : _SG_TRIG_MODE_GATE,
			'startmode' : _SG_TRIG_MODE_START,
			'ncycle' : _SG_TRIG_MODE_NCYCLE,
			'sweep'	: _SG_TRIG_MODE_SWEEP,
			'off':	_SG_TRIG_MODE_OFF
		}

		mode = _utils.str_to_val(_str_to_trigger_mode, mode, 'trigger mode')

		# ensure combination of signal frequency and Ncycles doesn't cause 64 bit register overflow:
		if mode is _SG_TRIG_MODE_NCYCLE:
			SignalPeriod = 0 if SignalFreq == 0.0 else SignalFreq**-1 
			FPGACycles = math.ceil(125e6 * SignalPeriod * NCycles)
			if FPGACycles > 2**63-1:
				raise ValueOutOfRangeException("NCycle Register Overflow")

		if mode is _SG_TRIG_MODE_SWEEP:
			PhaseIncrement = round((2**31 * 2**48 / (125*10**15)) * (SweepFinalFreq - SweepInitFreq)/SweepDuration)
			SweepLength_FPGACycles = math.ceil(125e6 * SweepDuration)
			InitFreq = SweepInitFreq * (2**48/10**9)
		
		if ch == 1:
			self.TrigSweepMode_Ch0 = mode
			if mode is _SG_TRIG_MODE_NCYCLE:
				self.NCycles_TrigDuty_Ch0 = FPGACycles
			if mode is _SG_TRIG_MODE_SWEEP:
				self.SweepLength_Ch0 = SweepLength_FPGACycles
				self.SweepInitFreq_Ch0 = InitFreq
				self.SweepIncrement_Ch0 = PhaseIncrement
		elif ch == 2:
			self.TrigSweepMode_Ch1 = mode
			if mode is _SG_TRIG_MODE_NCYCLE:
				self.NCycles_TrigDuty_Ch1 = FPGACycles
			if mode is _SG_TRIG_MODE_SWEEP:
				self.SweepLength_Ch1 = SweepLength_FPGACycles
				self.SweepInitFreq_Ch1 = InitFreq
				self.SweepIncrement_Ch1 = PhaseIncrement

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

		_str_to_modsource = {
			'internal' : _SG_MODSOURCE_INT,
			'in'		: _SG_MODSOURCE_ADC,
			'out'		: _SG_MODSOURCE_DAC
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
			self.out1_modulation = mtype
			self.out1_modsource = source
			self.mod1_frequency = frequency
		elif ch == 2:
			self.out2_modulation = mtype
			self.out2_modsource = source
			self.mod2_frequency = frequency

		# Calibrate the depth value depending on the source
		if(source == _SG_MODSOURCE_INT):
			depth_parameter *= 1.0 # No change in depth
		elif(source == _SG_MODSOURCE_DAC):
			# Opposite DAC is used
			depth_parameter = depth_parameter * pow(2.0,15.0) * (dac2 if ch == 1 else dac1)
		elif(source == _SG_MODSOURCE_ADC):
			# Associated ADC for current channel
			depth_parameter =  depth_parameter * pow(2.0,9.0) * (adc1 if ch == 1 else adc2)

		if ch == 1:
			self.mod1_amplitude = (pow(2.0, 32.0) - 1) * depth_parameter / 4.0
		elif ch == 2:
			self.mod2_amplitude = (pow(2.0, 32.0) - 1) * depth_parameter / 4.0

_siggen_mod_reg_handlers = {
	'out1_modulation':	(REG_SG_WAVEFORMS,	to_reg_unsigned(16, 8, allow_range=[_SG_MOD_NONE, _SG_MOD_AMPL | _SG_MOD_FREQ | _SG_MOD_PHASE]),
											from_reg_unsigned(16, 8)),

	'out2_modulation':	(REG_SG_WAVEFORMS,	to_reg_unsigned(24, 8, allow_range=[_SG_MOD_NONE, _SG_MOD_AMPL | _SG_MOD_FREQ | _SG_MOD_PHASE]),
											from_reg_unsigned(24, 8)),

	'mod1_frequency':	((REG_SG_MODF1_H, REG_SG_MODF1_L),
											lambda obj, f, old: ((old[0] & 0x0000FFFF) | (_usgn(f/_SG_FREQSCALE, 48) >> 16) & 0xFFFF0000, _usgn(f/_SG_FREQSCALE, 48) & 0xFFFFFFFF),
											lambda obj, rval: _SG_FREQSCALE * ((rval[0] & 0xFFFF0000) << 16 | rval[1])),

	'mod2_frequency':	((REG_SG_MODF2_H, REG_SG_MODF2_L),
											lambda obj, f, old: ((old[0] & 0x0000FFFF) | (_usgn(f/_SG_FREQSCALE, 48) >> 16) & 0xFFFF0000, _usgn(f/_SG_FREQSCALE, 48) & 0xFFFFFFFF),
											lambda obj, rval: _SG_FREQSCALE * ((rval[0] & 0xFFFF0000) << 16 | rval[1])),
	# The meaning of this amplitude field is complicated enough that the conversion to register value is done in the
	# main code above rather than inline
	'mod1_amplitude':	(REG_SG_MODA1,		to_reg_unsigned(0, 32),
											from_reg_unsigned(0, 32)),

	'mod2_amplitude':	(REG_SG_MODA2,		to_reg_unsigned(0, 32),
											from_reg_unsigned(0, 32)),

	'out1_modsource':	(REG_SG_MODSOURCE,	to_reg_unsigned(1, 2, allow_set=[_SG_MODSOURCE_INT, _SG_MODSOURCE_ADC, _SG_MODSOURCE_DAC]),
											from_reg_unsigned(1, 2)),

	'out2_modsource':	(REG_SG_MODSOURCE,	to_reg_unsigned(3, 2, allow_set=[_SG_MODSOURCE_INT, _SG_MODSOURCE_ADC, _SG_MODSOURCE_DAC]),
											from_reg_unsigned(3, 2))
}

_siggen_reg_handlers = {
	'out1_enable':		(REG_SG_WAVEFORMS,	to_reg_bool(0),		from_reg_bool(0)),
	'out2_enable':		(REG_SG_WAVEFORMS,	to_reg_bool(1),		from_reg_bool(1)),

	'out1_waveform':	(REG_SG_WAVEFORMS,	to_reg_unsigned(4, 3, allow_set=[_SG_WAVE_SINE, _SG_WAVE_SQUARE, _SG_WAVE_TRIANGLE, _SG_WAVE_DC, _SG_WAVE_PULSE]),
											from_reg_unsigned(4, 3)),

	'out2_waveform':	(REG_SG_WAVEFORMS,	to_reg_unsigned(8, 3, allow_set=[_SG_WAVE_SINE, _SG_WAVE_SQUARE, _SG_WAVE_TRIANGLE, _SG_WAVE_DC, _SG_WAVE_PULSE]),
											from_reg_unsigned(8, 3)),

	'out1_clipsine':	(REG_SG_WAVEFORMS,	to_reg_bool(7),		from_reg_bool(7)),
	'out2_clipsine':	(REG_SG_WAVEFORMS,	to_reg_bool(11),		from_reg_bool(11)),
	'out1_frequency':	((REG_SG_FREQ1_H, REG_SG_FREQ1_L),
											to_reg_unsigned(0, 48, xform=lambda obj, f:f / _SG_FREQSCALE),
											from_reg_unsigned(0, 48, xform=lambda obj, f: f * _SG_FREQSCALE)),

	'out2_frequency':	((REG_SG_FREQ2_H, REG_SG_FREQ2_L),
											to_reg_unsigned(0, 48, xform=lambda obj, f:f / _SG_FREQSCALE),
											from_reg_unsigned(0, 48, xform=lambda obj, f: f * _SG_FREQSCALE)),

	'out1_offset':		(REG_SG_MODF1_H,	to_reg_signed(0, 16, xform=lambda obj, o:o / obj._dac_gains()[0]),
											from_reg_signed(0, 16, xform=lambda obj, o: o * obj._dac_gains()[0])),

	'out2_offset':		(REG_SG_MODF2_H,	to_reg_signed(0, 16, xform=lambda obj, o:o / obj._dac_gains()[1]),
											from_reg_signed(0, 16, xform=lambda obj, o: o * obj._dac_gains()[1])),

	'out1_phase':		(REG_SG_PHASE1,		to_reg_unsigned(0, 32, xform=lambda obj, p: (p / _SG_PHASESCALE) % (2**32)),
											from_reg_unsigned(0, 32, xform=lambda obj, p:p * _SG_PHASESCALE)),

	'out2_phase':		(REG_SG_PHASE2,		to_reg_unsigned(0, 32, xform=lambda obj, p: (p / _SG_PHASESCALE) % (2**32)),
											from_reg_unsigned(0, 32, xform=lambda obj, p:p * _SG_PHASESCALE)),

	'out1_amplitude':	(REG_SG_AMP1,		to_reg_unsigned(0, 16, xform=lambda obj, a:a / obj._dac_gains()[0]),
											from_reg_unsigned(0, 16, xform=lambda obj, a:a * obj._dac_gains()[0])),

	'out2_amplitude':	(REG_SG_AMP2,		to_reg_unsigned(0, 16, xform=lambda obj, a:a / obj._dac_gains()[1]),
											from_reg_unsigned(0, 16, xform=lambda obj, a:a * obj._dac_gains()[1])),

	'out1_t0':			(REG_SG_T01,		to_reg_unsigned(0, 32, xform=lambda obj, o: o / _SG_TIMESCALE),
											from_reg_unsigned(0, 32, xform=lambda obj, o: o * _SG_TIMESCALE)),

	'out1_t1':			(REG_SG_T11,		to_reg_unsigned(0, 32, xform=lambda obj, o: o / _SG_TIMESCALE),
											from_reg_unsigned(0, 32, xform=lambda obj, o: o * _SG_TIMESCALE)),

	'out1_t2':			(REG_SG_T21,		to_reg_unsigned(0, 32, xform=lambda obj, o: o / _SG_TIMESCALE) ,
											from_reg_unsigned(0, 32, xform=lambda obj, o: o * _SG_TIMESCALE)),

	'out2_t0':			(REG_SG_T02,		to_reg_unsigned(0, 32, xform=lambda obj, o: o / _SG_TIMESCALE),
											from_reg_unsigned(0, 32, xform=lambda obj, o: o * _SG_TIMESCALE)),

	'out2_t1':			(REG_SG_T12,		to_reg_unsigned(0, 32, xform=lambda obj, o: o / _SG_TIMESCALE),
											from_reg_unsigned(0, 32, xform=lambda obj, o: o * _SG_TIMESCALE )),

	'out2_t2':			(REG_SG_T22,		to_reg_unsigned(0, 32, xform=lambda obj, o: o / _SG_TIMESCALE ),
											from_reg_unsigned(0, 32, xform=lambda obj, o: o * _SG_TIMESCALE )),

	'out1_riserate':	((REG_SG_RFRATE1_H, REG_SG_RISERATE1_L),
											to_reg_unsigned(0, 48, xform=lambda obj, r: r / _SG_FREQSCALE),
											from_reg_unsigned(0, 48, xform=lambda obj, r: r * _SG_FREQSCALE)),

	'out1_fallrate':	((REG_SG_RFRATE1_H, REG_SG_FALLRATE1_L),
											lambda obj, f, old: ((old[0] & 0x0000FFFF) | (_usgn(f/_SG_FREQSCALE, 48) >> 16) & 0xFFFF0000, _usgn(f/_SG_FREQSCALE, 48) & 0xFFFFFFFF),
											lambda obj, rval: _SG_FREQSCALE * ((rval[0] & 0xFFFF0000) << 16 | rval[1])),

	'out2_riserate':	((REG_SG_RFRATE2_H, REG_SG_RISERATE2_L),
											to_reg_unsigned(0, 48, xform=lambda obj, r: r / _SG_FREQSCALE),
											from_reg_unsigned(0, 48, xform=lambda obj, r: r * _SG_FREQSCALE)),

	'out2_fallrate':	((REG_SG_RFRATE2_H, REG_SG_FALLRATE2_L),
											lambda obj, f, old: ((old[0] & 0x0000FFFF) | (_usgn(f/_SG_FREQSCALE, 48) >> 16) & 0xFFFF0000, _usgn(f/_SG_FREQSCALE, 48) & 0xFFFFFFFF),
											lambda obj, rval: _SG_FREQSCALE * ((rval[0] & 0xFFFF0000) << 16 | rval[1])),

	'out1_amp_pc':		(REG_SG_PRECLIP,	to_reg_unsigned(0, 16, xform=lambda obj, a: a / obj._dac_gains()[0]),
											from_reg_unsigned(0, 16, xform=lambda obj, a: a * obj._dac_gains()[0])),

	'out2_amp_pc':		(REG_SG_PRECLIP,	to_reg_unsigned(16, 16, xform=lambda obj, a: a / obj._dac_gains()[1]),
											from_reg_unsigned(16, 16, xform=lambda obj, a: a * obj._dac_gains()[1])),
	'InternalTrigPeriod_Ch0':	((REG_SG_TrigPeriodInternalCH0_H, REG_SG_TrigPeriodInternalCH0_L),
											to_reg_unsigned(0,64), from_reg_unsigned(0,64)),

	'InternalTrigPeriod_Ch1':	((REG_SG_TrigPeriodInternalCH1_H, REG_SG_TrigPeriodInternalCH1_L),
											to_reg_unsigned(0,64), from_reg_unsigned(0,64)),

	'TrigADCThreshold_Ch0':		(REG_SG_ADCThreshold, 	to_reg_signed(0,12), from_reg_signed(0,12)),

	'TrigADCThreshold_Ch1':		(REG_SG_ADCThreshold, 	to_reg_signed(12,12), from_reg_signed(12,12)),

	'TrigDACThreshold_Ch0':		(REG_SG_DACThreshold, 	to_reg_signed(0,16), from_reg_signed(0,16)),

	'TrigDACThreshold_Ch1':		(REG_SG_DACThreshold, 	to_reg_signed(16,16), from_reg_signed(16,16)),

	'TrigSweepMode_Ch0':	(REG_SG_TrigSweepMode, 	to_reg_unsigned(0,3), from_reg_unsigned(0,3)),

	'TrigSweepMode_Ch1':	(REG_SG_TrigSweepMode, 	to_reg_unsigned(3,3), from_reg_unsigned(3,3)),

	'TriggerSelect_Ch0':	(REG_SG_TrigSweepMode, 	to_reg_unsigned(6,2), from_reg_unsigned(6,2)),

	'TriggerSelect_Ch1':	(REG_SG_TrigSweepMode, 	to_reg_unsigned(8,2), from_reg_unsigned(8,2)),

	'PhaseContinuous':  (REG_SG_TrigSweepMode, 	to_reg_unsigned(10,1), from_reg_unsigned(10,1)),

	'SweepLength_Ch0':	((REG_SG_SweepLengthCh0_H, REG_SG_SweepLengthCh0_L),
											to_reg_unsigned(0,64), from_reg_unsigned(0,64)),

	'SweepLength_Ch1':	((REG_SG_SweepLengthCh1_H, REG_SG_SweepLengthCh1_L),
											to_reg_unsigned(0,64), from_reg_unsigned(0,64)),

	'SweepInitFreq_Ch0':	((REG_SG_SweepInitFreqCh0_H, REG_SG_SweepInitFreqCh0_L),
											to_reg_unsigned(0,48), from_reg_unsigned(0,48)),

	'SweepInitFreq_Ch1':	((REG_SG_SweepInitFreqCh1_H, REG_SG_SweepInitFreqCh1_L),
											to_reg_unsigned(0,48), from_reg_unsigned(0,48)),

	'SweepIncrement_Ch0':	((REG_SG_SweepIncrementCh0_H, REG_SG_SweepIncrementCh0_L),
											to_reg_signed(0,64), from_reg_signed(0,64)),

	'SweepIncrement_Ch1':	((REG_SG_SweepIncrementCh1_H, REG_SG_SweepIncrementCh1_L),
											to_reg_signed(0,64), from_reg_signed(0,64)),

	'NCycles_TrigDuty_Ch0':	((REG_SG_NCycles_TrigDutyCH0_H, REG_SG_NCycles_TrigDutyCH0_L),
											to_reg_unsigned(0,64), from_reg_unsigned(0,64)),

	'NCycles_TrigDuty_Ch1':	((REG_SG_NCycles_TrigDutyCH1_H, REG_SG_NCycles_TrigDutyCH1_L),
											to_reg_unsigned(0,64), from_reg_unsigned(0,64))
}
