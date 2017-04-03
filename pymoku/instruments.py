import sys

from . import _instrument
from . import _oscilloscope
from . import _siggen
from . import _phasemeter
from . import _specan
from . import _lockinamp
from . import _frame_instrument


''' Preferred import point. Aggregates the separate instruments and helper classes
    to flatten the import heirarchy (e.g. pymoku.instruments.Oscilloscope rather
    than pymoku.instruments._oscilloscope.Oscilloscope)
'''
_this_module = sys.modules[__name__]

DataFrame = _frame_instrument.DataFrame
VoltsFrame = _oscilloscope.VoltsFrame
SpectrumFrame = _specan.SpectrumFrame

DataBuffer = _frame_instrument.DataBuffer

MokuInstrument = _instrument.MokuInstrument

Oscilloscope = _oscilloscope.Oscilloscope
SignalGenerator = _siggen.SignalGenerator
PhaseMeter = _phasemeter.PhaseMeter
SpecAn = _specan.SpecAn
LockInAmp = _lockinamp.LockInAmp

# Re-export all constants from Oscilloscope that start with OSC_
for attr, val in _oscilloscope.__dict__.items():
	if attr.startswith('OSC_'):
		setattr(_this_module, attr, val)

# Re-export all constants from generic Frame Instrument that start with DL_ (datalogger)
for attr, val in _frame_instrument.__dict__.items():
	if attr.startswith('DL_'):
		setattr(_this_module, attr, val)

# Re-export all constants from Signal Generator that start with SG_
for attr, val in _siggen.__dict__.items():
	if attr.startswith('SG_'):
		setattr(_this_module, attr, val)

# Re-export all constants from Phase Meter that start with PM_
for attr, val in _phasemeter.__dict__.items():
	if attr.startswith('PM_'):
		setattr(_this_module, attr, val)

# Re-export all constants from Spectrum Analyser that start with SA_
for attr, val in _specan.__dict__.items():
	if attr.startswith('SA_'):
		setattr(_this_module, attr, val)

# Re-export all constants from Lock-in Amplifier that start with LIA_
for attr, val in _lockinamp.__dict__.items():
	if attr.startswith('LIA_'):
		setattr(_this_module, attr, val)	


id_table = {
	1: Oscilloscope,
	2: SpecAn,
	3: PhaseMeter,
	4: SignalGenerator,
	5: None, # PID Controller
	6: None, # IIR Filter Box
	7: Oscilloscope, # Datalogger
	8: LockInAmp,
	9: None, # Bode Analyser
	10: None, # FIR Filter Box
	11: None, # PDH Locking
	12: None, # Software Defined Radio
	13: None, # Frequency Counter
	14: None # BoxCar Averager
}
