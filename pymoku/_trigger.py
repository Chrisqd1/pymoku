from ._instrument import *

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
		return self._instr._accessor_get(self.reg_base + Trigger._REG_CONFIG, from_reg_unsigned(4, 2))

	@edge.setter
	def edge(self, value):
		self._instr._accessor_set(self.reg_base + Trigger._REG_CONFIG,
			                      to_reg_unsigned(4, 2, allow_set=[Trigger.EDGE_RISING, Trigger.EDGE_FALLING, Trigger.EDGE_BOTH]),
			                      value)

	@property
	def hysteresis(self):
		return self._instr._accessor_get(self.reg_base + Trigger._REG_HYSTERESIS, from_reg_unsigned(0, 16))

	@hysteresis.setter
	def hysteresis(self, value):
		self._instr._accessor_set(self.reg_base + Trigger._REG_HYSTERESIS, to_reg_unsigned(0, 16), value)

