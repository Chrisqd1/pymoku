import sys

from . import _instrument
from . import _oscilloscope
from . import _siggen
from . import _phasemeter
from . import _specan
from . import _frame_instrument

''' Preferred import point. Aggregates the separate instruments and helper classes
    to flatten the import heirarchy (e.g. pymoku.instruments.Oscilloscope rather
    than pymoku.instruments._oscilloscope.Oscilloscope)
'''
_this_module = sys.modules[__name__]

DataFrame = _frame_instrument.DataFrame
VoltsFrame = _oscilloscope.VoltsFrame
SpectrumFrame = _specan.SpectrumFrame

MokuInstrument = _instrument.MokuInstrument

Oscilloscope = _oscilloscope.Oscilloscope
SignalGenerator = _siggen.SignalGenerator
PhaseMeter = _phasemeter.PhaseMeter
SpecAn = _specan.SpecAn

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


id_table = {
	1: Oscilloscope,
	3: PhaseMeter,
	4: SignalGenerator,
}
