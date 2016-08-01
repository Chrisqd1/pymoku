import sys

import _instrument
import _oscilloscope
import _siggen
import _phasemeter
import _specan
import _lockinamp
import _frame_instrument


''' Preferred import point. Aggregates the separate instruments and helper classes
    to flatten the import heirarchy (e.g. pymoku.instruments.Oscilloscope rather
    than pymoku.instruments._oscilloscope.Oscilloscope)
'''
_this_module = sys.modules[__name__]

DataFrame = _frame_instrument.DataFrame
VoltsFrame = _oscilloscope.VoltsFrame

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

id_table = {
	0: None,
	1: Oscilloscope,
	3: PhaseMeter,
	4: SignalGenerator,
	8: LockInAmp,
}
