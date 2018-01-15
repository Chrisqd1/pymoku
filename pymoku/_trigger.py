from ._instrument import *
from . import _utils

_CLK_FREQ = 125e6
_TIMER_ACCUM = 2.0**32

class Trigger(object):

	# with Control(0).Value(3 downto 0) select TriggerType <=
	# 	EDGE when "0000",
	# 	PULSE_WIDTH when others;

	# with Control(0).Value(8 downto 7) select PulseWidthType <=
	# 	MIN_WIDTH when "00",
	# 	MAX_WIDTH when others;

	_REG_CONFIG = 0
	_REG_LEVEL = 1
	_REG_HYSTERESIS = 2
	_REG_DURATION = 3
	_REG_HOLDOFF = 4
	_REG_NTRIGGER = 5
	_REG_TIMER = 6

	EDGE_RISING	= 0
	EDGE_FALLING = 1
	EDGE_BOTH = 2

	def __init__(self, instr, reg_base):
		self._instr = instr
		self.reg_base = reg_base

		# self.mode = mode
		# self.level = level # Save the desired trigger voltage

	@property
	def edge(self):
		r = self.reg_base + Trigger._REG_CONFIG
		return self._instr._accessor_get(r, from_reg_unsigned(4, 2))

	@edge.setter
	def edge(self, value):
		r = self.reg_base + Trigger._REG_CONFIG
		self._instr._accessor_set(r, to_reg_unsigned(4, 2, allow_set=[Trigger.EDGE_RISING, Trigger.EDGE_FALLING, Trigger.EDGE_BOTH]), value)

	@property
	def hysteresis(self):
		r = self.reg_base + Trigger._REG_HYSTERESIS
		return self._instr._accessor_get(r, from_reg_unsigned(0, 16))

	@hysteresis.setter
	def hysteresis(self, value):
		r = self.reg_base + Trigger._REG_HYSTERESIS
		self._instr._accessor_set(r, to_reg_unsigned(0, 16), value)

	@property
	def timer(self):
		r = self.reg_base + Trigger._REG_TIMER
		v = self._instr._accessor_get(r, from_reg_unsigned(0, 16))
		return (_CLK_FREQ * v) / _TIMER_ACCUM

	@timer.setter
	def timer(self, value):
		_utils.check_parameter_valid('range', value, allowed=[0.0, (_CLK_FREQ * (2.0**16 - 1)) / _TIMER_ACCUM], desc='timer', units='Hz')
		r = self.reg_base + Trigger._REG_TIMER
		v = int(round(value * (_TIMER_ACCUM / _CLK_FREQ)))
		self._instr._accessor_set(r, to_reg_unsigned(0, 16), v)

	@property
	def holdoff(self):
		r = self.reg_base + Trigger._REG_HOLDOFF
		return self._instr._accessor_get(r, from_reg_unsigned(0, 32), value)

	@holdoff.setter
	def holdoff(self, value):
		r = self.reg_base + Trigger._REG_HOLDOFF
		self._instr._accessor_set(r, to_reg_unsigned(0, 32), value)

	@property
	def auto_holdoff(self):
		r = self.reg_base + Trigger._REG_TIMER
		return self._instr._accessor_get(r, from_reg_unsigned(16, 8))

	@auto_holdoff.setter
	def auto_holdoff(self, value):
		r = self.reg_base + Trigger._REG_TIMER
		self._instr._accessor_set(r, to_reg_unsigned(16, 8), value)

	@property
	def ntrigger(self):
		r = self.reg_base + Trigger._REG_NTRIGGER
		return self._instr._accessor_get(r, from_reg_unsigned(0, 16))

	@ntrigger.setter
	def ntrigger(self, value):
		r = self.reg_base + Trigger._REG_NTRIGGER
		self._instr._accessor_set(r, to_reg_unsigned(0, 16), value)

	@property
	def ntrigger_mode(self):
		r = self.reg_base + Trigger._REG_NTRIGGER
		return self._instr._accessor_get(r, from_reg_bool(31))

	@ntrigger_mode.setter
	def ntrigger_mode(self, value):
		r = self.reg_base + Trigger._REG_NTRIGGER
		self._instr._accessor_set(r, to_reg_bool(31), value)

	@property
	def level(self):
		r = self.reg_base + Trigger._REG_LEVEL
		return self._instr._accessor_get(r, from_reg_unsigned(0, 32))

	@level.setter
	def level(self, value):
		print value
		_utils.check_parameter_valid('range', value, allowed=[-2**31, 2**31-1], desc='level')
		r = self.reg_base + Trigger._REG_LEVEL
		self._instr._accessor_set(r, to_reg_unsigned(0, 32), value)


