from ._instrument import *

from . import _stream_instrument
from . import _siggen
import _utils

REG_DL_OUTSEL		= 65
REG_DL_ACTL			= 69
REG_DL_DECIMATION	= 70

# REG_DL_OUTSEL constants
_DL_SOURCE_ADC	= 0
_DL_SOURCE_DAC	= 1

_DL_LB_ROUND	= 0
_DL_LB_CLIP		= 1

_DL_AIN_DDS		= 0
_DL_AIN_DECI	= 1

_DL_ADC_SMPS		= ADC_SMP_RATE
_DL_BUFLEN			= CHN_BUFLEN
_DL_SCREEN_WIDTH	= 1024
_DL_ROLL			= ROLL

class DataLogger(_stream_instrument.StreamBasedInstrument, _siggen.BasicSignalGenerator):

	def __init__(self):
		super(DataLogger, self).__init__()
		self._register_accessors(_dl_reg_handlers)

		self.id = 7
		self.type = "datalogger"
		self.calibration = None
		self.scales = {}

		self.logname = "MokuDataLoggerData"
		self.binstr = "<s32"
		self.procstr = ["*C","*C"]
		self.hdrstr = ''
		self.fmtstr = ''
		self.timestep = 1

	def _deci_gain(self):
		if self.decimation_rate == 0:
			return 1

		if self.decimation_rate < 2**20:
			return self.decimation_rate
		else:
			return self.decimation_rate / 2**10

	@needs_commit
	def set_defaults(self):

		# Force X-Mode to be "roll" for streaming
		self.x_mode = _DL_ROLL

	@needs_commit
	def set_samplerate(self, samplerate):
		""" Manually set the sample rate of the instrument.

		This interface allows you to specify the rate at which data is sampled.

		:type samplerate: float; *0 < samplerate < 500Msmp/s*
		:param samplerate: Target samples per second. Will get rounded to the nearest allowable unit.

		"""
		decimation = _DL_ADC_SMPS / float(samplerate)
		self.decimation_rate = decimation
		self.timestep = 1.0/(_DL_ADC_SMPS/decimation)

	def get_samplerate(self):
		""" :return: The current instrument sample rate """
		if(self.decimation_rate == 0):
			log.warning("Decimation rate appears to be unset.")
			return _DL_ADC_SMPS
		return _DL_ADC_SMPS / float(self.decimation_rate)

	@needs_commit
	def set_precision_mode(self, state):
		""" Change aquisition mode between downsampling and decimation.
		Precision mode, a.k.a Decimation, samples at full rate and applies a low-pass filter to the data. This improves
		precision. Normal mode works by direct downsampling, throwing away points it doesn't need.

		:param state: Select Precision Mode
		:type state: bool
		"""
		self.ain_mode = _DL_AIN_DECI if state else _DL_AIN_DDS

	def is_precision_mode(self):
		return self.ain_mode is _DL_AIN_DECI

	@needs_commit
	def set_source(self, ch, source, lmode='round'):
		""" Sets the source of the channel data to either the analog input or internally looped-back digital output.

		This feature allows the user to capture the Signal Generator outputs.

		:type ch: int
		:param ch: Channel Number

		:type source: string, {'in','out'}
		:param source: Where the specified channel should source data from (either the input or internally looped back output)

		:type lmode: string, {'clip','round'}
		:param lmode: DAC Loopback mode (ignored 'in' sources)
		"""
		_str_to_lmode = {
			'round' : _DL_LB_ROUND,
			'clip' : _DL_LB_CLIP
		}
		_str_to_channel_data_source = {
			'in' : _DL_SOURCE_ADC,
			'out' : _DL_SOURCE_DAC
		}
		source = _utils.str_to_val(_str_to_channel_data_source, source, 'channel data source')
		lmode = _utils.str_to_val(_str_to_lmode, lmode, 'DAC loopback mode')
		if ch == 1:
			self.source_ch1 = source
			if source == _DL_SOURCE_DAC:
				self.loopback_mode_ch1 = lmode
		elif ch == 2:
			self.source_ch2 = source
			if source == _DL_SOURCE_DAC:
				self.loopback_mode_ch2 = lmode
		else:
			raise ValueOutOfRangeException("Incorrect channel number %d", ch)

	def _update_datalogger_params(self, ch1, ch2):
		samplerate = self.get_samplerate()

		if self.ain_mode == _DL_AIN_DECI:
			self.procstr[0] = "*C/{:f}".format(self._deci_gain())
			self.procstr[1] = "*C/{:f}".format(self._deci_gain())
		else:
			self.procstr[0] = "*C"
			self.procstr[1] = "*C"
		self.fmtstr = self._get_fmtstr(ch1,ch2)
		self.hdrstr = self._get_hdrstr(ch1,ch2)

	def _get_hdrstr(self, ch1, ch2):
		chs = [ch1, ch2]

		hdr = "% Moku:DataLogger\r\n"
		for i,c in enumerate(chs):
			if c:
				r = self.get_frontend(i+1)
				hdr += "% Ch {i} - {} coupling, {} Ohm impedance, {} V range\r\n".format("AC" if r[2] else "DC", "50" if r[0] else "1M", "10" if r[1] else "1", i=i+1 )
		hdr += "% Acquisition rate: {:.10e} Hz, {} mode\r\n".format(self.get_samplerate(), "Precision" if self.is_precision_mode() else "Normal")
		hdr += "% {} 10 MHz clock\r\n".format("External" if self._moku._get_actual_extclock() else "Internal")
		hdr += "% Acquired {}\r\n".format(_utils.formatted_timestamp())
		hdr += "% Time"
		for i,c in enumerate(chs):
			if c:
				hdr += ", Ch {i} voltage (V)".format(i=i+1)
		hdr += "\r\n"
		return hdr

	def _get_fmtstr(self, ch1, ch2):
		chs = [ch1, ch2]
		fmtstr = "{t:.10e}"
		for i,c in enumerate(chs):
			if c:
				fmtstr += ",{{ch{i}:.10e}}".format(i=i+1)
		fmtstr += "\r\n"
		return fmtstr

	def _deci_gain(self):
		if self.decimation_rate == 0:
			return 1

		if self.decimation_rate < 2**20:
			return self.decimation_rate
		else:
			return self.decimation_rate / 2**10

	def commit(self):
		self._update_datalogger_params(self.ch1, self.ch2)
		# Commit the register values to the device
		super(DataLogger, self).commit()

	
_dl_reg_handlers = {
	'source_ch1':		(REG_DL_OUTSEL,	to_reg_unsigned(0, 1, allow_set=[_DL_SOURCE_ADC, _DL_SOURCE_DAC]),
											from_reg_unsigned(0, 1)),

	'source_ch2':		(REG_DL_OUTSEL,	to_reg_unsigned(1, 1, allow_set=[_DL_SOURCE_ADC, _DL_SOURCE_DAC]),
											from_reg_unsigned(1, 1)),

	'loopback_mode_ch1':	(REG_DL_ACTL,	to_reg_unsigned(0, 1, allow_set=[_DL_LB_CLIP, _DL_LB_ROUND]),
											from_reg_unsigned(0, 1)),
	'loopback_mode_ch2':	(REG_DL_ACTL,	to_reg_unsigned(1, 1, allow_set=[_DL_LB_CLIP, _DL_LB_ROUND]),
											from_reg_unsigned(1, 1)),
	'ain_mode':			(REG_DL_ACTL,		to_reg_unsigned(16,2, allow_set=[_DL_AIN_DDS, _DL_AIN_DECI]),
											from_reg_unsigned(16,2)),
	'decimation_rate':	(REG_DL_DECIMATION,to_reg_unsigned(0, 32),	from_reg_unsigned(0, 32))
}
