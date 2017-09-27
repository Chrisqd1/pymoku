
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

REG_MMAP_ACCESS = 62 #TODO this should go somewhere more instrument generic

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

_ARB_AMPSCALE = 2.0**16
_ARB_VOLTSCALE = 2.0**15
_ARB_LUT_LENGTH = 8192
_ARB_LUT_LSB = 2.0**32

class ArbWaveGen(_CoreOscilloscope):
	def __init__(self):
		super(ArbWaveGen, self).__init__()
		self._register_accessors(_arb_reg_handlers)
		self.id = 15
		self.type = "arbwavegen"

	@needs_commit
	def set_defaults(self):
		super(ArbWaveGen, self).set_defaults()
		#Arb Waveforms supports 8K at 1000Msps
		self.mode1 = _ARB_MODE_1000
		self.lut_length1 = _ARB_LUT_LENGTH
		self.mode2 = _ARB_MODE_1000
		self.lut_length2 = _ARB_LUT_LENGTH

		# Timing of the output is controlled by  PhaseModulo and Phaseset
		self.phase_modulo1 = 2**30
		self.phase_modulo2 = 2**30
		self.phase_step1 = _ARB_LUT_LSB
		self.phase_step2 = _ARB_LUT_LSB

		#Valuse for dead time part of signal 
		#If signal wraps this gets added in the middle
		self.dead_value1 = 0x0000
		self.dead_value2 = 0x0000

		#Add some obivios setups like Ipad values
		self.interpolation1 = False
		self.interpolation2 = False
		self.enable1 = False
		self.enable2 = False
		self.amplitude1 = 1.0
		self.amplitude2 = 1.0

	@needs_commit
	def _set_mmap_access(self, access):
		self.mmap_access = access


	@needs_commit
	def write_lut(self, ch, data, srate=None):
		# Determine which sample rate is used and set according to channels

		if srate is not None:
			if ch == 1: self.mode1 = srate
			else:       self.mode2 = srate

		# based in the channel used select the correct mode
		mode = [self.mode1, self.mode2][ch-1]
		log.info("selected mode is:  %d", mode)
		
		assert len(data) <= 2**13 or mode in [_ARB_MODE_125, _ARB_MODE_250, _ARB_MODE_500]
		assert len(data) <= 2**14 or mode in [_ARB_MODE_125, _ARB_MODE_250]
		assert len(data) <= 2**15 or mode in [_ARB_MODE_125]
		assert len(data) <= 2**16


		# picks the stepsize and the steps based in the mode

		steps, stepsize = [(8, 8192), (4, 8192 * 2), (2, 8192 * 4), (1, 8192 * 8)][mode]

		with open('.lutdata.dat', 'r+b') as f:
			#first check and make the file the right size
			f.seek(0, os.SEEK_END)
			size = f.tell()
			f.write('\0'.encode(encoding='UTF-8') * (_ARB_LUT_LENGTH * 8 * 4 * 2 - size))
			f.flush()

			log.info("lut Table for values %s ", '\0'.encode(encoding='UTF-8'))
			
			#Leave the previous data file so we just rewite the new part,
			#as we have to upload both channels at once.
			if ch == 1:
				offset = 0
				log.info("lutlength1, phase_modulo1, phase_step1:  %f %f %f", self.lut_length1, self.phase_modulo1, self.phase_step1)
			else:
				offset = _ARB_LUT_LENGTH * 8 * 4
				log.info("lutlength1, phase_modulo1, phase_step1:  %f %f %f", self.lut_length1, self.phase_modulo1, self.phase_step1)

			for step in range(steps):
				f.seek(offset + (step * stepsize * 4)) 
				log.info("lut Table for values %s ", [struct.pack('<hh', int(round((2.0**15-1) * d)), 0) for d in data])
				f.write(b''.join([struct.pack('<hh', int(round((2.0**15-1) * d)), 0) for d in data]))

			f.flush()

		self.enable1 = False
		self.enable2 = False
		self._set_mmap_access(True)
		self._moku._send_file('j', '.lutdata.dat')
		self._set_mmap_access(False)
		self.enable1 = True
		self.enable2 = True
	
	@needs_commit
	def gen_waveform(self, ch, period, phase, amplitude, offset=0, interpolation=True, dead_time=0, fiftyr=True):
		""" Generate a Wave with the given parameters on the given channel.

		:type ch: int; {1,2}
		:param ch: Channel on which to generate the wave

		:type amplitude: float, [0.0,2.0] Vpp
		:param amplitude: Waveform peak-to-peak amplitude

		:type offset: float, [-1.0,1.0] Volts
		:param offset: DC offset applied to the waveform

		:type phase: float, [0-360] degrees
		:param phase: Phase offset of the wave

		:type interpolation: bool [True, False]
		:param interpolation: Uses linear interploation if true

		:type dead_time: float [0, 2e18] cyc
		:param dead_time: number of cycles which do not show a signal

		:type fifyr: bool [True, False]
		:param fifyr: use of 50 Ohm impedance

		:raises ValueError: if the channel number is invalid
		:raises ValueOutOfRangeException: if wave parameters are out of range

		"""
		_utils.check_parameter_valid('set', ch, [1,2],'output channel')
		_utils.check_parameter_valid('range', amplitude, [0.0, 2.0],'peak to peak amplitude','Volts')
		_utils.check_parameter_valid('bool', interpolation, desc='linear interpolation')
		_utils.check_parameter_vaild('range', dead_time, [0.0, 2e18], 'signal dead time', 'cycles')
		_utils.check_parameter_valid('bool', fiftyr, desc='50 Ohm termination')

		upper_voltage = offset + (amplitude/2.0)
		lower_voltage = offset - (amplitude/2.0)
		if (upper_voltage > 1.0) or (lower_voltage < -1.0):
			raise ValueOutOfRangeException("Waveform offset limited by amplitude (max output range 2.0Vpp).")

		if(ch == 1):
			print("Enable output 1 with settings")
			self.interpolation1 = interpolation
			#self.phase_modulo1 = self.lut_length1 * 2**32 if self.interpolation1 == True else self.phase_modulo1
			self.dead_value1 = dead_time
			self.amplitude1 = amplitude
			self.offset1 = offset
			#self.phase_step1 = 1 / period * self.mode1 * self.phase_modulo1
			self.phase_offset1 = 0 if dead_time == 0 else phase / 360.0 * self.phase_modulo1
			self.enable1 = True

		if(ch == 2):
			print("Enable output 2 with settings")
			self.interpolation2 = interpolation
			#self.phase_modulo2 = self.lut_length2 * 2**32 if self.interpolation2 == True else self.phase_modulo2
			self.dead_value2 = dead_time
			self.amplitude2 = amplitude
			self.offset2 = offset
			#self.phase_step2 = 1 / period * self.mode2 * self.phase_modulo2
			self.phase_offset2 = 0 if dead_time == 0 else phase / 360.0 * self.phase_modulo1
			self.enable2 = True


	def get_frequency(self, ch):
		""" returns the frequency for a given channel
		
		:type ch: int; {1,2}
		:param ch: Channel on which to generate the wave
		"""
		_utils.check_parameter_valid('set', ch, [1,2],'output channel')

		if ch == 1:
			return (self.phase_step1 * self.mode1) / self.phase_modulo1
		if ch == 2:
			return (self.phase_step2 * self.mode2) / self.phase_modulo2

	@needs_commit
	def gen_off(self, ch=None):
		""" Turn ArbWaveGen output(s) off.

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
			self.enable1 = False

		if ch is None or ch == 2:
			self.enable2 = False


_arb_reg_handlers = {
	'mmap_access':		(REG_MMAP_ACCESS,		to_reg_bool(0),			from_reg_bool(0)),
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
