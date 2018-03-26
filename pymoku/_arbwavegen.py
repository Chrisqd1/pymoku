
import math
import logging
import re
import os

from ._instrument import *
from . import _frame_instrument
from . import _waveform_generator
from pymoku._oscilloscope import _CoreOscilloscope
from . import _utils
from ._trigger import Trigger
from ._sweep_generator import SweepGenerator

log = logging.getLogger(__name__)

REG_ARB_SETTINGS1 = 88
REG_ARB_LUT_LENGTH1 = 105
REG_ARB_AMPLITUDE1 = 106
REG_ARB_OFFSET1 = 107

REG_ARB_SETTINGS2 = 108
REG_ARB_LUT_LENGTH2 = 125
REG_ARB_AMPLITUDE2 = 126
REG_ARB_OFFSET2 = 127

_ARB_MODE_1000 = 0x0
_ARB_MODE_500 = 0x1
_ARB_MODE_250 = 0x2
_ARB_MODE_125 = 0x3

_ARB_AMPSCALE = 2.0**16 - 1
_ARB_VOLTSCALE = 2.0**15
_ARB_LUT_LENGTH = 8192
_ARB_LUT_LSB = 2.0**32
_ARB_LUT_INTERPLOATION_LENGTH = 2**32

_ARB_TRIG_SRC_CH1 = 0
_ARB_TRIG_SRC_CH2 = 1
_ARB_TRIG_SRC_EXT = 4

_ARB_TRIG_LVL_MIN = -5.0
_ARB_TRIG_LVL_MAX = 5.0

_ARB_TRIG_TYPE_SINGLE 	= 0
_ARB_TRIG_TYPE_CONT		= 2

_ARB_SMPL_RATE = 1.0e9

# In-built monitor constants
_ARB_INPUT_SMPS = ADC_SMP_RATE
_ARB_CHN_BUFLEN = 2**13

class ArbitraryWaveGen(_CoreOscilloscope):
	"""
	.. automethod:: pymoku.instruments.WaveformGenerator.__init__
	"""

	def __init__(self):
		super(ArbitraryWaveGen, self).__init__()
		self._register_accessors(_arb_reg_handlers)
		self.id = 15
		self.type = "arbitrarywavegen"

		self._sweep1 = SweepGenerator(self, 96)
		self._sweep2 = SweepGenerator(self, 116)

		self._trigger1 = Trigger(self, 89)
		self._trigger2 = Trigger(self, 109)

		# Locally store the trigger level
		self.trig_level1 = 0 # Volts
		self.trig_level2 = 0 # Volts

		# Monitor configuration
		# TODO: Implement monitor functions? Is there a use-case?
		# TODO: Check this rate is correct for the AWG
		self._input_samplerate	= _ARB_INPUT_SMPS
		self._chn_buffer_len	= _ARB_CHN_BUFLEN

	@needs_commit
	def set_defaults(self):
		super(ArbitraryWaveGen, self).set_defaults()
		self.mode1 = _ARB_MODE_125
		self.lut_length1 = _ARB_LUT_LENGTH
		self.mode2 = _ARB_MODE_125
		self.lut_length2 = _ARB_LUT_LENGTH
		self._sweep1.stop = 2**42
		self._sweep2.stop = 2**42
		self._sweep1.step = _ARB_LUT_LSB
		self._sweep2.step = _ARB_LUT_LSB
		self.dead_value1 = 0x0000
		self.dead_value2 = 0x0000
		self.interpolation1 = False
		self.interpolation2 = False
		self.enable1 = False
		self.enable2 = False
		self.amplitude1 = 1.0
		self.amplitude2 = 1.0
		self.offset1 = 0.0
		self.offset2 = 0.0
		self._sweep1.waveform = SweepGenerator.WAVE_TYPE_SAWTOOTH
		self._sweep2.waveform = SweepGenerator.WAVE_TYPE_SAWTOOTH

		self.data = [[0], [0]]

	@needs_commit
	def _set_mode(self, ch, mode, length):
		#Changes the mode used to determine outut the waveform.

		_utils.check_parameter_valid('set', ch, [1,2],'output channel')
		_utils.check_parameter_valid('set', mode, [_ARB_MODE_1000, _ARB_MODE_500, _ARB_MODE_250, _ARB_MODE_125], desc='mode is not vaild')

		if mode is _ARB_MODE_1000:
			_utils.check_parameter_valid('range', length, [1,2**13], desc='length for lookup table')
		if mode is _ARB_MODE_500:
			_utils.check_parameter_valid('range', length, [1,2**14], desc='length for lookup table')
		if mode is _ARB_MODE_250:
			_utils.check_parameter_valid('range', length, [1,2**15], desc='length for lookup table')
		if mode is _ARB_MODE_125:
			_utils.check_parameter_valid('range', length, [1,2**16], desc='length for lookup table')

		if ch == 1:
			self.mode1 = mode
			self.lut_length1 = length-1
		elif ch ==2:
			self.mode2 = mode
			self.lut_length2 = length-1

	def write_lut(self, ch, data, mode=None):
		"""Writes the signal lookup table to memory in the Moku:Lab.

		You can also choose the output rate of the AWG, which influences the
		maximum length of the look-up table as follows:

		- 1000MSPS: 8192 points per channel
		- 500MSPS: 16384 points per channel
		- 250MSPS: 32768 points per channel
		- 125MSPS: 65534 points per channel

		If you don't specify a mode, the fastest output rate for the given data
		length will be automatically chosen. This is correct in almost all
		circumstances.

		If you specify a particular mode along with a data array too big for
		that mode, the behaviour is undefined.

		:type ch: int; {1,2}
		:param ch: Output channel to load the LUT to

		:type mode: string: '1000', '500', '250', '125'
		:param: defines the output sample rate of the AWG (in MSPS).

		:raises ValueError: if the channel is invalid
		:raises ValueOutOfRangeException: if wave parameters are out of range
		"""
		_utils.check_parameter_valid('set', ch, [1,2],'output channel')

		if mode is None:
			if len(data) <= 8192:
				mode = '1000'
			elif len(data) <= 16384:
				mode = '500'
			elif len(data) <= 32768:
				mode = '250'
			elif len(data) <= 65535:
				mode = '125'
			else:
				raise ValueOutOfRangeException("Maximum data length is 65535 samples")

		_str_to_mode = {
			'1000' : _ARB_MODE_1000,
			'500' : _ARB_MODE_500,
			'250'	: _ARB_MODE_250,
			'125'	: _ARB_MODE_125
		}

		mode = _utils.str_to_val(_str_to_mode, mode, "operating mode")

		self._set_mode(ch, mode, len(data))

		# picks the stepsize and the steps based in the mode
		steps, stepsize = [(8, 8192), (4, 8192 * 2), (2, 8192 * 4), (1, 8192 * 8)][mode]

		self.data[ch - 1] = data

		with open('.lutdata.dat', 'w+b') as f:
			#first check and make the file the right size
			f.seek(0, os.SEEK_END)
			size = f.tell()
			f.write(b'\0' * (_ARB_LUT_LENGTH * 8 * 4 * 2 - size))
			f.flush()

			#Leave the previous data file so we just rewite the new part,
			#as we have to upload both channels at once.
			for step in range(steps):
				f.seek(step * stepsize * 4)
				f.write(b''.join([struct.pack('<hh', math.ceil((2.0**15-1) * d),0) for d in self.data[0]]))

			for step in range(steps):
				f.seek((_ARB_LUT_LENGTH * 8 * 4) + (step * stepsize * 4))
				f.write(b''.join([struct.pack('<hh', math.ceil((2.0**15-1) * d),0) for d in self.data[1]]))

			f.flush()

		self._set_mmap_access(True)
		error = self._moku._send_file('j', '.lutdata.dat')
		self._set_mmap_access(False)
		os.remove('.lutdata.dat')

	@needs_commit
	def gen_waveform(self, ch, period, amplitude, phase=0, offset=0, interpolation=True, dead_time=0, dead_voltage = 0):
		""" Generate the Arbitrary Waveform with the given parameters on the given channel.

		The Look-up table for this channel should have been loaded beforehand using :any:`write_lut`.

		The Arbitrary Waveform Generator has the ability to insert a deadtime between cycles from the look-up
		table. This time is specified in cycles of the waveform. During this time, the output will be held
		at the given *dead_voltage*.  This allows the user to, for example, generate infrequent pulses without
		using space in the LUT to specify the time between, keeping the full LUT size to provide a high-resolution
		pulse shape.

		Where the period and look-up table contents are set such that there isn't exactly one LUT point per output
		sample, the AWG instrument can optionally provide a linear interpolation between LUT points.

		:type ch: int; {1,2}
		:param ch: Channel on which to generate the wave

		:type period: float, [4e-9, 1];
		:param period: period of the signal in seconds

		:type amplitude: float, [0.0,2.0] Vpp
		:param amplitude: Waveform peak-to-peak amplitude

		:type phase: float, [0-360] degrees
		:param phase: Phase offset of the wave

		:type offset: float, [-1.0,1.0] Volts
		:param offset: DC offset applied to the waveform

		:type interpolation: bool [True, False]
		:param interpolation: Enable linear interpolation of LUT entries

		:type dead_time: float [0, 2e18] cyc
		:param dead_time: number of cycles which show the dead voltage. Use 0 for no dead time

		:type dead_voltage: float [-2.0,2.0] V
		:param dead_voltage: signal level during dead time in Volts

		:raises ValueError: if the parameters  is invalid
		:raises ValueOutOfRangeException: if wave parameters are out of range
		:raises InvalidParameterException: if the parameters are the wrong types
		"""
		_utils.check_parameter_valid('set', ch, [1,2], desc='output channel')
		_utils.check_parameter_valid('range', period, [4e-9, 1], desc='periode of the signal')
		_utils.check_parameter_valid('range', amplitude, [0.0,2.0], desc='peak to peak amplitude', units='volts')
		_utils.check_parameter_valid('bool', interpolation, desc='linear interpolation')
		_utils.check_parameter_valid('range', dead_time, [0.0, 2e18], desc='signal dead time', units='cycles')
		_utils.check_parameter_valid('range', dead_voltage, [-2.0, 2.0], desc='dead value', units='volts')
		_utils.check_parameter_valid('range', phase, [0, 360], desc='phase offset', units='degrees')

		upper_voltage = offset + (amplitude/2.0)
		lower_voltage = offset - (amplitude/2.0)

		if (upper_voltage > 1.0) or (lower_voltage < -1.0):
			raise ValueOutOfRangeException("Waveform offset limited by amplitude (max output range 2.0Vpp).")

		if(ch == 1):
			freq = 1/period
			self.interpolation1 = interpolation
			phase_modulo = (self.lut_length1 + 1) * _ARB_LUT_INTERPLOATION_LENGTH
			self._sweep1.step = freq / _ARB_SMPL_RATE * phase_modulo
			phase_modulo = phase_modulo * dead_time if dead_time > 0 else phase_modulo
			self._sweep1.stop = phase_modulo
			self._sweep1.start = (phase / 360) * phase_modulo if dead_time == 0 else 0
			self.dead_value1 = dead_voltage
			self.amplitude1 = amplitude
			self.offset1 = offset
			self.enable1 = True

		if(ch == 2):
			freq = 1/period
			self.interpolation2 = interpolation
			phase_modulo = (self.lut_length2 + 1) * _ARB_LUT_INTERPLOATION_LENGTH
			self._sweep2.step = freq / _ARB_SMPL_RATE * phase_modulo
			phase_modulo = phase_modulo * dead_time if dead_time > 0 else phase_modulo
			self._sweep2.stop = phase_modulo
			self._sweep2.start = (phase / 360) * phase_modulo if dead_time > 0 else 0
			self.dead_value2 = dead_voltage
			self.amplitude2 = amplitude
			self.offset2 = offset
			self.enable2 = True

	@needs_commit
	def set_waveform_trigger(self, ch, source, edge, level, minwidth=None, maxwidth=None, hysteresis=False):
		""" Specify what constitutes a trigger event for the given output channel. This takes effect
			only when the channel has triggered output mode enabled (see :any:`set_waveform_trigger_mode').

		:type ch: int; {1,2}
		:param ch: Output channel to set triggering on

		:type source: string, {'in1','in2','ext'}
		:param source: Trigger source. May be either input channel, or the external 'Trig' back-panel connector 
			allowing triggering from an externally-generated digital [LV]TTL or CMOS signal.

		:type edge: string, {'rising','falling','both'}
		:param edge: Which edge to trigger on. In 'Pulse Width' mode this specifies whether the pulse is positive (rising)
				or negative (falling), with the 'both' option being invalid.

		:type level: float, [-5.0, 5.0] volts
		:param level: Trigger level. Ignored in 'ext' mode.

		:type minwidth: float, seconds
		:param minwidth: Minimum Pulse Width. 0 <= minwidth < (2^32/samplerate). Can't be used with maxwidth.

		:type maxwidth: float, seconds
		:param maxwidth: Maximum Pulse Width. 0 <= maxwidth < (2^32/samplerate). Can't be used with minwidth.

		:type hysteresis: bool
		:param hysteresis: Enable hysteresis around trigger point.

		"""
		_utils.check_parameter_valid('set', ch, [1,2], 'channel')
		_utils.check_parameter_valid('set', source, ['in1', 'in2', 'ext'], 'trigger source')
		_utils.check_parameter_valid('set', edge, ['rising', 'falling', 'both'])
		_utils.check_parameter_valid('range', level, [_ARB_TRIG_LVL_MIN, _ARB_TRIG_LVL_MAX], 'trigger level', 'Volts')

		if not (maxwidth is None or minwidth is None):
			raise InvalidConfigurationException("Can't set both 'minwidth' and 'maxwidth' for Pulse Width trigger mode. Choose one.")
		if (maxwidth or minwidth) and (edge is 'both'):
			raise InvalidConfigurationException("Can't set trigger edge type 'both' in Pulse Width trigger mode. Choose one of {'rising','falling'}.")
		
		# External trigger source is only available on Moku 20
		if (self._moku.get_hw_version() == 1.0) and source == 'ext':
			raise InvalidConfigurationException('External trigger source is not available on your hardware.')
		if source=='ext' and level:
			log.warning("Trigger level ignored when triggering from source 'ext'.")

		# TODO: Add timer source
		_str_to_source = {
			'in1' : _ARB_TRIG_SRC_CH1,
			'in2' : _ARB_TRIG_SRC_CH2,
			'ext' : _ARB_TRIG_SRC_EXT
		}
		_str_to_edge = {
			'rising' : Trigger.EDGE_RISING,
			'falling' : Trigger.EDGE_FALLING,
			'both'	: Trigger.EDGE_BOTH
		}
		source = _utils.str_to_val(_str_to_source, source, 'trigger source')
		edge = _utils.str_to_val(_str_to_edge, edge, 'edge type')

		if ch == 1:
			self.trig_source1 = source
			self.trig_level1 = level
		elif ch == 2:
			self.trig_source2 = source
			self.trig_level2 = level
		else:
			raise ValueOutOfRangeException("Incorrect channel number %d", ch)

		trig_channels = [self._trigger1, self._trigger2]

		# AKA: Normal trigger mode only (HG-2598)
		trig_channels[ch-1].timer = 0.0
		trig_channels[ch-1].auto_holdoff = 0

		trig_channels[ch-1].edge = edge
		trig_channels[ch-1].mode = mode
		trig_channels[ch-1].duration = minwidth or maxwidth or 0.0
		# TODO: Enable setting hysteresis level. For now we use the iPad LSB values for ON/OFF.
		trig_channels[ch-1].hysteresis = 25 if hysteresis else 0

		if maxwidth:
			trig_channels[ch-1].trigtype = Trigger.TYPE_PULSE
			trig_channels[ch-1].pulsetype = Trigger.PULSE_MAX
		elif minwidth:
			trig_channels[ch-1].trigtype = Trigger.TYPE_PULSE
			trig_channels[ch-1].pulsetype = Trigger.PULSE_MIN
		else:
			trig_channels[ch-1].trigtype = Trigger.TYPE_EDGE

	@needs_commit
	def set_waveform_trigger_mode(self, ch, trig_en = True, single = True, duration = 0.0, hold_last = False):
		""" Enables triggered output mode on the specified channel and configures 'how' to output the 
			set waveform on a trigger event.

		:type ch: int; {1,2}
		:param ch: Output channel to configure

		:type trig_en: bool;
		:param trig_en: Enables triggering mode on the specified output channel

		:type trig_type: string; {'single', 'continuous'}
		:param trig_type; Select the mode (how the waveform behaves) when a trigger arrives.

		:type duration: float; [0.0, 1e11] seconds
		:param duration: select the time that the triggered functionality is active - set 0 for continuous. Note the 
			duration resolution is 8ns. 

		:type hold_last: bool
		:param hold_last: set to hold the last value of the waveform for the duration of the triggered functionality

		:type start: float; [0.0, 360.0] phase
		:param start: determines when in the waveform cycle to start generating signal once a trigger event has occured.
			The waveform cycle includes and specified deadtime.
		"""
		# Convert the input parameter strings to bit-value mappings
		_utils.check_parameter_valid('set', ch, [1,2], 'channel')
		_utils.check_parameter_valid('bool', trig_en, 'trigger enable')
		_utils.check_parameter_valid('set', trig_type, ['single', 'continuous'])
		_utils.check_parameter_valid('range', duration, [0, 1e11], 'duration', 'seconds')
		_utils.check_parameter_valid('bool', hold_last, 'hold_last')
		_utils.check_parameter_valid('range', start, [0, 360], 'trigger output start phase', 'degrees')

		sweep_channels = [self._sweep1, self._sweep2]

		sweep_channels[ch-1].wait_for_trig = trig_en

		_str_to_waveform = {
			'single' : 		_ARB_TRIG_TYPE_SINGLE,
			'continuous' : 	_ARB_TRIG_TYPE_CONT
		}

		sweep_channels[ch-1].waveform = _utils.str_to_val(_str_to_waveform, trig_type, 'trig_type')
		sweep_channels[ch-1].hold_last = hold_last
		sweep_channels[ch-1].duration = int(round(duration * 1.0e9 / 8))

	def _update_dependent_regs(self, scales):
		super(ArbitraryWaveGen, self)._update_dependent_regs(scales)
		self._trigger1.level = int(round(self.trig_level1 / self._source_volts_per_bit(self.trig_source1, scales)))
		self._trigger2.level = int(round(self.trig_level2 / self._source_volts_per_bit(self.trig_source2, scales)))

	@needs_commit
	def sync_phase(self):
		""" Synchronizes the phase of the given channel to the other
		"""
		self.reset_phase(1)
		self.reset_phase(2)

	@needs_commit
	def reset_phase(self, ch):
		""" resets the channels phase accumulator to zero

		:type ch: int; {1,2}
		:param ch: Channel on which the reset is performed

		:raises ValueError: if the channel number is invalid
		"""
		_utils.check_parameter_valid('set', ch, [1,2],'output channel')

		if ch == 1:
			self.phase_rst1 = True
		elif ch ==2:
			self.phase_rst2 = True

	def get_frequency(self, ch):
		""" returns the frequency for a given channel

		:type ch: int; {1,2}
		:param ch: Channel from which the frequency is calculated

		:raises ValueError: if the channel number is invalid
		"""
		_utils.check_parameter_valid('set', ch, [1,2],'output channel')


		if ch == 1:
			return (self._sweep1.step / self._sweep1.stop) * _ARB_SMPL_RATE
		if ch == 2:
			return (self._sweep2.step / self._sweep2.stop) * _ARB_SMPL_RATE

	@needs_commit
	def gen_off(self, ch=None):
		""" Turn ArbitraryWaveGen output(s) off.

		The channel will be turned on when configuring the waveform type but can be turned off
		using this function. If *ch* is None (the default), both channels will be turned off,
		otherwise just the one specified by the argument.

		:type ch: int; {1,2} or None
		:param ch: Channel to turn off, or both.

		:raises ValueError: invalid channel number
		"""
		_utils.check_parameter_valid('set', ch, [1,2],'output channel', allow_none=True)

		if ch is None or ch == 1:
			self.enable1 = False

		if ch is None or ch == 2:
			self.enable2 = False


_arb_reg_handlers = {
	'enable1':			(REG_ARB_SETTINGS1,		to_reg_bool(0),			from_reg_bool(0)),
	'phase_rst1':		(REG_ARB_SETTINGS1,		to_reg_bool(1),			from_reg_bool(1)),
	'mode1':			(REG_ARB_SETTINGS1,		to_reg_unsigned(2, 2, allow_set=[_ARB_MODE_125, _ARB_MODE_250, _ARB_MODE_500, _ARB_MODE_1000]),
												from_reg_unsigned(2, 2)),
	'interpolation1':	(REG_ARB_SETTINGS1,		to_reg_bool(4),			from_reg_bool(4)),
	'trig_source1':		(REG_ARB_SETTINGS1,		to_reg_unsigned(5, 5, allow_set=[_ARB_TRIG_SRC_CH1, _ARB_TRIG_SRC_CH2, _ARB_TRIG_SRC_EXT]),
												from_reg_unsigned(5, 5)),
	'lut_length1':		(REG_ARB_LUT_LENGTH1,	to_reg_unsigned(0, 16), from_reg_signed(0, 16)),
	'dead_value1':		(REG_ARB_LUT_LENGTH1,	to_reg_signed(16, 16), 	from_reg_signed(16, 16)),
	'amplitude1':		(REG_ARB_AMPLITUDE1,	to_reg_signed(0, 18, xform=lambda obj, r: r * _ARB_AMPSCALE),
	                                            from_reg_signed(0, 18, xform=lambda obj, r: r / _ARB_AMPSCALE)),
	'offset1':			(REG_ARB_OFFSET1,		to_reg_signed(0, 16, xform=lambda obj, r: r * _ARB_VOLTSCALE),
	                                            from_reg_signed(0, 16, xform=lambda obj, r: r / _ARB_VOLTSCALE)),
	'enable2':			(REG_ARB_SETTINGS2,		to_reg_bool(0),			from_reg_bool(0)),
	'phase_rst2':		(REG_ARB_SETTINGS2,		to_reg_bool(1),			from_reg_bool(1)),
	'mode2':			(REG_ARB_SETTINGS2,		to_reg_unsigned(2, 2, allow_set=[_ARB_MODE_125, _ARB_MODE_250, _ARB_MODE_500, _ARB_MODE_1000]),
												from_reg_unsigned(2, 2)),
	'interpolation2':	(REG_ARB_SETTINGS2,		to_reg_bool(4),			from_reg_bool(4)),
	'trig_source2':		(REG_ARB_SETTINGS2,		to_reg_unsigned(5, 5, allow_set=[_ARB_TRIG_SRC_CH1, _ARB_TRIG_SRC_CH2, _ARB_TRIG_SRC_EXT]),
												from_reg_unsigned(5, 5)),
	'lut_length2':		(REG_ARB_LUT_LENGTH2,	to_reg_unsigned(0, 16), from_reg_signed(0, 16)),
	'dead_value2':		(REG_ARB_LUT_LENGTH2,	to_reg_signed(16, 16), 	from_reg_signed(16, 16)),
	'amplitude2':		(REG_ARB_AMPLITUDE2,	to_reg_signed(0, 18, xform=lambda obj, r: r * _ARB_AMPSCALE),
	                                            from_reg_signed(0, 18, xform=lambda obj, r: r / _ARB_AMPSCALE)),
	'offset2':			(REG_ARB_OFFSET2,		to_reg_signed(0, 16, xform=lambda obj, r: r * _ARB_VOLTSCALE),
	                                            from_reg_signed(0, 16, xform=lambda obj, r: r / _ARB_VOLTSCALE))
}
