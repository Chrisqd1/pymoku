import sys

from . import _instrument
from . import _oscilloscope
from . import _siggen
from . import _phasemeter
from . import _specan
from . import _lockinamp
from . import _datalogger
from . import _stream_instrument
from . import _frame_instrument
from . import _stream_handler

''' Preferred import point. Aggregates the separate instruments and helper classes
    to flatten the import heirarchy (e.g. pymoku.instruments.Oscilloscope rather
    than pymoku.instruments._oscilloscope.Oscilloscope)
'''

InstrumentData = _frame_instrument.InstrumentData
VoltsData = _oscilloscope.VoltsData
SpectrumFrame = _specan.SpectrumFrame

MokuInstrument = _instrument.MokuInstrument

Oscilloscope = _oscilloscope.Oscilloscope
SignalGenerator = _siggen.SignalGenerator
PhaseMeter = _phasemeter.PhaseMeter
SpecAn = _specan.SpecAn
LockInAmp = _lockinamp.LockInAmp
DataLogger = _datalogger.DataLogger

id_table = {
	1: Oscilloscope,
	2: SpecAn,
	3: PhaseMeter,
	4: SignalGenerator,
	5: None, # PID Controller
	6: None, # IIR Filter Box
	7: DataLogger, # Datalogger
	8: LockInAmp,
	9: None, # Bode Analyser
	10: None, # FIR Filter Box
	11: None, # PDH Locking
	12: None, # Software Defined Radio
	13: None, # Frequency Counter
	14: None # BoxCar Averager
}
