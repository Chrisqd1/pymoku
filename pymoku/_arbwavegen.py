
import math
import logging
import re
import os

from ._instrument import *
CHN_BUFLEN = 2**13
from . import _frame_instrument
from . import _waveform_generator
from pymoku._oscilloscope import _CoreOscilloscope
from . import _utils

log = logging.getLogger(__name__)

REG_ARB_SETTINGS = 96
REG_ARB_PHASE_STEP1_L = 97
REG_ARB_PHASE_STEP1_H = 98
REG_ARB_PHASE_OFFSET1_L = 101
REG_ARB_PHASE_OFFSET1_H = 102
REG_ARB_AMPLITUDE1 = 105
REG_ARB_PHASE_MOD1_L = 107
REG_ARB_PHASE_MOD1_H = 108
REG_ARB_DEAD_VALUE1 = 111
REG_ARB_LUT_LENGTH1 = 113
REG_ARB_OFFSET1 = 115

REG_ARB_PHASE_STEP2_L = 99
REG_ARB_PHASE_STEP2_H = 100
REG_ARB_PHASE_OFFSET2_L = 103
REG_ARB_PHASE_OFFSET2_H = 104
REG_ARB_AMPLITUDE2 = 106
REG_ARB_PHASE_MOD2_L = 109
REG_ARB_PHASE_MOD2_H = 110
REG_ARB_DEAD_VALUE2 = 112
REG_ARB_LUT_LENGTH2 = 114
REG_ARB_OFFSET2 = 116

_ARB_MODE_1000 = 0x0
_ARB_MODE_500 = 0x1
_ARB_MODE_250 = 0x2
_ARB_MODE_125 = 0x3

_ARB_AMPSCALE = 2.0**16 - 1
_ARB_VOLTSCALE = 2.0**15
_ARB_LUT_LENGTH = 8192
_ARB_LUT_LSB = 2.0**32
_ARB_LUT_INTERPLOATION_LENGTH = 2**32

_ARB_MODE_RATE = [1.0e9, 500.0e6, 250.0e6, 125.0e6] #1GS, 500MS, 250MS, 125MS

class ArbitraryWaveGen(_CoreOscilloscope):
	"""
	.. automethod:: pymoku.instruments.WaveformGenerator.__init__
	"""

	def __init__(self):
		super(ArbitraryWaveGen, self).__init__()
		self._register_accessors(_arb_reg_handlers)
		self.id = 15
		self.type = "arbitrarywavegen"

	@needs_commit
	def set_defaults(self):
		super(ArbitraryWaveGen, self).set_defaults()
		self.mode1 = _ARB_MODE_125
		self.lut_length1 = _ARB_LUT_LENGTH
		self.mode2 = _ARB_MODE_125
		self.lut_length2 = _ARB_LUT_LENGTH
		self.phase_modulo1 = 2**42
		self.phase_modulo2 = 2**42
		self.phase_step1 = _ARB_LUT_LSB
		self.phase_step2 = _ARB_LUT_LSB
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
			update_rate = _ARB_MODE_RATE[self.mode1]
			self.phase_step1 = freq / update_rate * phase_modulo
			phase_modulo = phase_modulo * dead_time if dead_time > 0 else phase_modulo
			self.phase_modulo1 = phase_modulo
			self.phase_offset1 = (phase / 360) * phase_modulo if dead_time == 0 else 0
			self.dead_value1 = dead_voltage
			self.amplitude1 = amplitude
			self.offset1 = offset
			self.enable1 = True

		if(ch == 2):
			freq = 1/period
			self.interpolation2 = interpolation
			phase_modulo = (self.lut_length2 + 1) * _ARB_LUT_INTERPLOATION_LENGTH
			update_rate = _ARB_MODE_RATE[self.mode2]
			self.phase_step2 = freq / update_rate * phase_modulo
			phase_modulo = phase_modulo * dead_time if dead_time > 0 else phase_modulo
			self.phase_modulo2 = phase_modulo
			self.phase_offset2 = (phase / 360) * phase_modulo if dead_time > 0 else 0
			self.dead_value2 = dead_voltage
			self.amplitude2 = amplitude
			self.offset2 = offset
			self.enable2 = True

	@needs_commit
	def sync_phase(self, ch):
		""" Synchronizes the phase of the given channel to the other

		:type ch: int; {1,2}
		:param ch: Channel that is synced to the other

		:raises ValueError: if the channel number is invalid
		"""
		_utils.check_parameter_valid('set', ch, [1,2],'output channel')

		if ch == 1:
			self.phase_sync1 = True
		elif ch ==2:
			self.phase_sync2 = True

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
			update_rate = _ARB_MODE_RATE[self.mode1]
			return (self.phase_step1 / self.phase_modulo1) * update_rate
		if ch == 2:
			update_rate = _ARB_MODE_RATE[self.mode2]
			return (self.phase_step2 / self.phase_modulo2) * update_rate

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
	'enable1':			(REG_ARB_SETTINGS,		to_reg_bool(16),		from_reg_bool(16)),
	'phase_rst1':		(REG_ARB_SETTINGS,		to_reg_bool(20),		from_reg_bool(20)),
	'phase_sync1':		(REG_ARB_SETTINGS,		to_reg_bool(22),		from_reg_bool(22)),
	'mode1':			(REG_ARB_SETTINGS,		to_reg_unsigned(0, 2, allow_set=[_ARB_MODE_125, _ARB_MODE_250, _ARB_MODE_500, _ARB_MODE_1000]),
												from_reg_unsigned(0, 2)),
	'interpolation1':	(REG_ARB_SETTINGS,		to_reg_bool(4),			from_reg_bool(4)),
	'lut_length1':		(REG_ARB_LUT_LENGTH1,	to_reg_unsigned(0, 16), from_reg_signed(0, 16)),
	'dead_value1':		(REG_ARB_DEAD_VALUE1,	to_reg_signed(0, 16), 	from_reg_signed(0, 16)),
	'amplitude1':		(REG_ARB_AMPLITUDE1,	to_reg_signed(0, 18, xform=lambda obj, r: r * _ARB_AMPSCALE),
	                                            from_reg_signed(0, 18, xform=lambda obj, r: r / _ARB_AMPSCALE)),
	'offset1':			(REG_ARB_OFFSET1,		to_reg_signed(0, 16, xform=lambda obj, r: r * _ARB_VOLTSCALE),
	                                            from_reg_signed(0, 16, xform=lambda obj, r: r / _ARB_VOLTSCALE)),
	'phase_modulo1':	((REG_ARB_PHASE_MOD1_H, REG_ARB_PHASE_MOD1_L),
												to_reg_unsigned(0, 64), from_reg_unsigned(0, 64)),
	'phase_offset1':	((REG_ARB_PHASE_OFFSET1_H, REG_ARB_PHASE_OFFSET1_L),
												to_reg_unsigned(0, 64), from_reg_unsigned(0, 64)),
	'phase_step1':		((REG_ARB_PHASE_STEP1_H, REG_ARB_PHASE_STEP1_L),
												to_reg_unsigned(0, 64), from_reg_unsigned(0, 64)),
	'enable2':			(REG_ARB_SETTINGS,		to_reg_bool(17),		from_reg_bool(17)),
	'phase_rst2':		(REG_ARB_SETTINGS,		to_reg_bool(21),		from_reg_bool(21)),
	'phase_sync2':		(REG_ARB_SETTINGS,		to_reg_bool(23),		from_reg_bool(23)),
	'mode2':			(REG_ARB_SETTINGS,		to_reg_unsigned(8, 2, allow_set=[_ARB_MODE_125, _ARB_MODE_250, _ARB_MODE_500, _ARB_MODE_1000]),
												from_reg_unsigned(8, 2)),
	'interpolation2':	(REG_ARB_SETTINGS,		to_reg_bool(12),			from_reg_bool(12)),
	'lut_length2':		(REG_ARB_LUT_LENGTH2,	to_reg_unsigned(0, 16), from_reg_signed(0, 16)),
	'dead_value2':		(REG_ARB_DEAD_VALUE2,	to_reg_signed(0, 16), 	from_reg_signed(0, 16)),
	'amplitude2':		(REG_ARB_AMPLITUDE2,	to_reg_signed(0, 18, xform=lambda obj, r: r * _ARB_AMPSCALE),
	                                            from_reg_signed(0, 18, xform=lambda obj, r: r / _ARB_AMPSCALE)),
	'offset2':			(REG_ARB_OFFSET2,		to_reg_signed(0, 16, xform=lambda obj, r: r * _ARB_VOLTSCALE),
	                                            from_reg_signed(0, 16, xform=lambda obj, r: r / _ARB_VOLTSCALE)),
	'phase_modulo2':	((REG_ARB_PHASE_MOD2_H, REG_ARB_PHASE_MOD2_L),
												to_reg_unsigned(0, 64), from_reg_unsigned(0, 64)),
	'phase_offset2':	((REG_ARB_PHASE_OFFSET2_H, REG_ARB_PHASE_OFFSET2_L),
												to_reg_unsigned(0, 64), from_reg_unsigned(0, 64)),
	'phase_step2':		((REG_ARB_PHASE_STEP2_H, REG_ARB_PHASE_STEP2_L),
												to_reg_unsigned(0, 64), from_reg_unsigned(0, 64))
}
