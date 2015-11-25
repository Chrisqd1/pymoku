
import threading, collections, time, struct, socket, logging

from functools import partial
from types import MethodType

from pymoku import NotDeployedException, ValueOutOfRangeException

REG_CTL 	= 0
REG_STAT	= 1
REG_ID1		= 2
REG_ID2		= 3
REG_RES1	= 4
REG_OUTLEN	= 5
REG_FILT	= 6
REG_FRATE	= 7
REG_SCALE	= 8
REG_OFFSET	= 9
REG_OFFSETA	= 10
REG_STRCTL0	= 11
REG_STRCTL1	= 12
REG_AINCTL	= 13
# 14 was Decimation before that moved in to instrument space
REG_PRETRIG	= 15
REG_CAL1, REG_CAL2, REG_CAL3, REG_CAL4, REG_CAL5, REG_CAL6, REG_CAL7, REG_CAL8 = range(16, 24)
REG_CAL9, REG_CAL10 = range(24, 26)
REG_STATE	= 63

### None of these constants will be exported to pymoku.instruments. If an instrument wants to
### give users access to these (e.g. relay settings) then the Instrument should define their
### own symbols equal to these guys

# REG_CTL Constants
COMMIT		= 0x80000000
INSTR_RST	= 0x00000001

# REG_OUTLEN Constants
ROLL		= (1 << 29)
SWEEP		= (1 << 30)
PAUSE		= (1 << 31)

# REG_FILT Constants
RDR_CUBIC	= 0
RDR_MINMAX	= 1
RDR_DECI	= 2
RDR_DDS		= 3

# REG_AINCTL Constants
RELAY_DC	= 1
RELAY_LOWZ	= 2
RELAY_LOWG	= 4

log = logging.getLogger(__name__)

"""
The following three functions provide some trickery, attaching getter and setter methods
to the instrument class, allowing a user to manipulate attributes directly and have their
values correctly packed in to, and extracted from, registers.

Each instrument, including this top instrument, defines a list of tuples that declare which
attributes live in which registers, and how to access them.  This list is then passed to
:any:`_attach_register_handlers` which builds the method objects and attaches them to the
class.

The tuple is of the form

(name, register, set-transform, get-transform)

name: The name the attribute will have
register: The register, or tuple of registers, the attribute will be packed to/from
set-transform: User (natural) units to register. Function gets passed the old value of the
	register so existing fields can be preserved. Usually written as a lambda in the list
	definition. If *register* is a tuple, the old register values are a tuple and this function
	must return a tuple of new register values in the same order. Should return None, or a tuple
	of Nones, if the input value is out of range.
get-transform: Register(s) to natural units. If *register* is a tuple, the sole argument to
	this function will also be a tuple.
"""

def _get_meth(reg, get_xform, self):
	# Return local if present. Support a single register or a tuple of registers
	try:
		c = [ self._localregs[r] or self._remoteregs[r] for r in reg ]
		if all(i is not None for i in c): return get_xform(c)
	except TypeError:
		c = self._localregs[reg] or self._remoteregs[reg]
		if c is not None: return get_xform(c)

def _set_meth(reg, set_xform, self, data):
	# Support a single register or a tuple of registers
	try:
		old = [ self._localregs[r] or self._remoteregs[r] or 0 for r in reg ]
	except TypeError:
		old = self._localregs[reg] or self._remoteregs[reg] or 0

	new = set_xform(data, old)
	if new is None:
		raise ValueOutOfRangeException()

	try:
		for r, n in zip(reg, new):
			self._localregs[r] = n
	except TypeError:
		self._localregs[reg] = new

def _attach_register_handlers(handler_list, cls):
	# This method could be simpler. Originally we wanted get/setter functions attached to
	# the Class itself. Now that we've rewritten the __{get,set}item__ functions for this
	# class and are storing in our own dict, we don't really need to pre-assemble the functions,
	# we could just call _{get,set}_meth with the right values right from the __{get,set}item__
	# functions.
	for name, reg, setter, getter in handler_list:
		if getter is not None:
			p = partial(_get_meth, reg, getter)
			p.__name__ = "get_" + name
			p.__doc__ = "Autogenerated Getter for %s" % name
			m = MethodType(p, None, cls)
			cls._accessor_dict["get_" + name] = m

		if setter is not None:
			p = partial(_set_meth, reg, setter)
			p.__name__ = "set_" + name
			p.__doc__ = "Autogenerated Setter for %s" % name
			m = MethodType(p, None, cls)
			cls._accessor_dict["set_" + name] = m

def _usgn(i, width):
	""" Return i as an unsigned of given width, raising exceptions for out of bounds """
	if 0 <= i <= 2**width:
		return int(i)

	raise ValueOutOfRangeException()

def _sgn(i, width):
	""" Return the unsigned that, when interpretted with given width, represents
	    the signed value i """
	if i < -2**width or 2**width - 1 < i:
		raise ValueOutOfRangeException()

	if i >= 0:
		return int(i)

	return int(2**width + i)

class MokuInstrument(object):
	"""Superclass for all Instruments that may be attached to a :any:`Moku` object.

	Should never be instantiated directly; instead, instantiate the subclass of the instrument
	you wish to run (e.g. :any:`Oscilloscope`, :any:`SignalGenerator`)"""
	_accessor_dict = {}

	def __init__(self):
		""" Should be overridden in implementations, initialising _localregs to an
		    appropriate sest of initial conditions. Overriding function should
		    call this superclass initialiser as their first action with the Moku
		    Instrument ID they drive as the only argument. """
		self._moku = None
		self._remoteregs = [None]*128
		self._localregs = [None]*128
		self._running = False
		self._stateid = 0

		self.id = 0
		self.type = "Dummy Instrument"

	def __getattr__(self, name):
		if name in MokuInstrument._accessor_dict:
			# Getting a function to get/set an accessor, bind to self
			return partial(MokuInstrument._accessor_dict[name], self)
		if "get_" + name in MokuInstrument._accessor_dict:
			# Getting the attribute, try to find the accessor
			return MokuInstrument._accessor_dict["get_" + name](self)
		else:
			raise AttributeError()

	def __setattr__(self, name, value):
		if "set_" + name in MokuInstrument._accessor_dict:
			return MokuInstrument._accessor_dict["set_" + name](self, value)
		else:
			return super(MokuInstrument, self).__setattr__(name, value)

	def set_defaults(self):
		""" Can be extended in implementations to set initial state """

	def attach_moku(self, moku):
		self._moku = moku

	def commit(self):
		"""
		Apply all modified settings. 
		
		.. note::

		    This **must** be called after any *set_* or *synth_* function has been called, or control
		    attributes have been directly set. This allows you to, for example, set multiple attributes
		    controlling rendering or signal generation in separate calls but have them all take effect at once.
		"""
		if self._moku is None: raise NotDeployedException()
		self._stateid = (self._stateid + 1) % 256 # Some statid docco says 8-bits, some 16.
		self.state_id = self._stateid
		self.state_id_alt = self._stateid

		regs = [ (i, d) for i, d in enumerate(self._localregs) if d is not None ]
		# TODO: Save this register set against stateid to be retrieved later
		log.debug("Committing reg set %s", str(regs))
		self._moku._write_regs(regs)
		self._remoteregs = [ l if l is not None else r for l, r in zip(self._localregs, self._remoteregs)]
		self._localregs = [None] * 128

	def sync_registers(self):
		if self._moku is None: raise NotDeployedException()
		self._remoteregs = zip(*self._moku._read_regs(range(128)))[1]

	def dump_remote_regs(self):
		return self._moku._read_regs(range(128))

	def set_running(self, state):
		self._running = state
		reg = (INSTR_RST if not state else 0)
		self._localregs[REG_CTL] = reg
		self.commit()


_instr_reg_hdl = [
	# Name, Register, set-transform (user to register), get-transform (register to user); either None is W/R-only
	('instr_id',		REG_ID1, None, lambda rval: rval & 0xFF),
	('instr_buildno',	REG_ID1, None, lambda rval: rval >> 16),
	('hwver',			REG_ID2, None, lambda rval: rval >> 24),
	('hwserial',		REG_ID2, None, lambda rval: rval & 0xFFF),
	('frame_length',	REG_OUTLEN, lambda l, old: (old & ~0x3FF) | _usgn(l, 12),
									lambda rval: rval & 0x3FF),
	('x_mode',			REG_OUTLEN, lambda m, old: ((old & ~0xE0000000) | m) if m in [ROLL, SWEEP, PAUSE] else None,
									lambda rval: rval & 0xE0000000),
	('render_mode',		REG_FILT,	lambda f, old: f if f in [RDR_CUBIC, RDR_MINMAX, RDR_DECI, RDR_DDS ] else None,
									lambda rval: rval),
	('framerate',		REG_FRATE,	lambda f, old: _usgn(f * 256.0 / 477.0, 8),
									lambda rval: rval * 256.0 / 477.0),
	# TODO: Assumes cubic
	('render_deci',		REG_SCALE,	lambda x, old: _usgn(256 / int(x) - 1, 8),
									lambda x: 256 / (1 + (x & 0xFFFF))),
	('render_deci_alt',	REG_SCALE,	lambda x, old: _usgn((256 / x) - 1, 8) << 16,
									lambda x: 256 / (1 + (int(x) >> 16))),
	('offset',			REG_OFFSET,	lambda x, old: _usgn(x, 32), lambda x: x),
	('offset_alt',		REG_OFFSETA,lambda x, old: _usgn(x, 32), lambda x: x),
	# TODO Stream Control
	('relays_ch1',		REG_AINCTL,	lambda r, old: (old & ~0x07) | _usgn(r, 3),
									lambda rval: rval & 0x07),
	('relays_ch2',		REG_AINCTL,	lambda r, old: (old & ~0x38) | _usgn(r, 3) << 3,
									lambda rval: (rval & 0x38) >> 3),
	('pretrigger',		REG_PRETRIG,lambda p, old: int(p), lambda rval: rval),
	# TODO Expose cal if required?
	('state_id',		REG_STATE,	lambda s, old: (old & ~0xFF) | _usgn(s, 8), lambda rval: rval & 0xFF),
	('state_id_alt',	REG_STATE,	lambda s, old: (old & ~0xFF0000) | _usgn(s, 8) << 16, lambda rval: rval >> 16),
]
_attach_register_handlers(_instr_reg_hdl, MokuInstrument)
