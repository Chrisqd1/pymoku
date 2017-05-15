import sys

from . import _instrument
from . import _oscilloscope
from . import _siggen
from . import _phasemeter
from . import _specan
from . import _lockinamp
from . import _datalogger
from . import _bodeanalyser
from . import _arbwavegen
from . import _stream_instrument
from . import _frame_instrument
from . import _stream_handler

''' Preferred import point. Aggregates the separate instruments and helper classes
    to flatten the import heirarchy (e.g. pymoku.instruments.Oscilloscope rather
    than pymoku.instruments._oscilloscope.Oscilloscope)
'''

InstrumentData = _frame_instrument.InstrumentData
VoltsData = _oscilloscope.VoltsData
SpectrumData = _specan.SpectrumData

MokuInstrument = _instrument.MokuInstrument

Oscilloscope = _oscilloscope.Oscilloscope
SignalGenerator = _siggen.SignalGenerator
Phasemeter = _phasemeter.Phasemeter
SpectrumAnalyser = _specan.SpectrumAnalyser
LockInAmp = _lockinamp.LockInAmp
Datalogger = _datalogger.Datalogger
BodeAnalyser = _bodeanalyser.BodeAnalyser
ArbWaveGen = _arbwavegen.ArbWaveGen

id_table = {
	1: Oscilloscope,
	2: SpectrumAnalyser,
	3: Phasemeter,
	4: SignalGenerator,
	5: None, # PID Controller
	6: None, # IIR Filter Box
	7: Datalogger, # Datalogger
	8: LockInAmp,
	9: BodeAnalyser,
	10: None, # FIR Filter Box
	11: None, # PDH Locking
	12: None, # Software Defined Radio
	13: None, # Frequency Counter
	14: None, # BoxCar Averager
	15: ArbWaveGen
}
