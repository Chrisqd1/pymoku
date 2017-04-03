
import math
import logging

from ._instrument import *
from . import _instrument
from . import _frame_instrument
from . import _siggen
from ._utils import *

from struct import unpack

import sys
# Annoying that import * doesn't pick up function defs??
_sgn = _instrument._sgn
_usgn = _instrument._usgn
_upsgn = _instrument._upsgn

log = logging.getLogger(__name__)

REG_PM_INITF1_H = 65
REG_PM_INITF1_L = 64
REG_PM_INITF2_L = 68
REG_PM_INITF2_H = 69
REG_PM_CGAIN = 66
REG_PM_INTSHIFT = 66
REG_PM_CSHIFT = 66
REG_PM_OUTDEC = 67
REG_PM_OUTSHIFT = 67
REG_PM_BW1 = 124
REG_PM_BW2 = 125
REG_PM_AUTOA1 = 126
REG_PM_AUTOA2 = 127

REG_PM_SG_EN = 96
REG_PM_SG_FREQ1_L = 97
REG_PM_SG_FREQ1_H = 98
REG_PM_SG_FREQ2_L = 99
REG_PM_SG_FREQ2_H = 100
REG_PM_SG_AMP = 105

# Phasemeter specific instrument constants
_PM_ADC_SMPS = _instrument.ADC_SMP_RATE
_PM_DAC_SMPS = _instrument.DAC_SMP_RATE
_PM_BUFLEN = _instrument.CHN_BUFLEN
_PM_FREQSCALE = 2.0**48 / _PM_DAC_SMPS
_PM_FREQ_MIN = 2e6
_PM_FREQ_MAX = 200e6
_PM_UPDATE_RATE = 1e6

_PM_CYCLE_SCALE = 2.0 * 2.0**16 / 2.0**48 * _PM_ADC_SMPS / _PM_UPDATE_RATE
_PM_HERTZ_SCALE = 2.0 * _PM_ADC_SMPS / 2**48
_PM_VOLTS_SCALE = 2.0 / (_PM_ADC_SMPS * _PM_ADC_SMPS / _PM_UPDATE_RATE / _PM_UPDATE_RATE)

# Phasemeter signal generator constants
_PM_SG_AMPSCALE = 2**16 / 4.0
_PM_SG_FREQSCALE = _PM_FREQSCALE

# Pre-defined log rates which ensure samplerate will set to ~120Hz or ~30Hz
PM_LOGRATE_FAST = 123
PM_LOGRATE_SLOW = 31

class PhaseMeter_SignalGenerator(MokuInstrument):
	def __init__(self):
		super(PhaseMeter_SignalGenerator, self).__init__()
		self._register_accessors(_pm_siggen_reg_hdl)

		# Local/cached values
		self.pm_out1_enable = False
		self.pm_out2_enable = False
		self._pm_out1_amplitude = 0
		self._pm_out2_amplitude = 0

	def set_defaults(self):
		self.gen_sinewave(1,0,0)
		self.gen_sinewave(2,0,0)
		self.enable_output(1,False)
		self.enable_output(2,False)

		self.set_frontend(1, fiftyr=True, atten=False, ac=True)
		self.set_frontend(2, fiftyr=True, atten=False, ac=True)

	def gen_sinewave(self, ch, amplitude, frequency):
		"""
		:param ch: Channel number
		:param amplitude: Signal amplitude in volts
		:param frequency: Frequency in Hz
		"""
		if ch == 1:
			self._pm_out1_amplitude = amplitude
			self.pm_out1_frequency = frequency
			self.pm_out1_amplitude = self._pm_out1_amplitude if self.pm_out1_enable else 0
		if ch == 2:
			self._pm_out2_amplitude = amplitude
			self.pm_out2_frequency = frequency
			self.pm_out2_amplitude = self._pm_out2_amplitude if self.pm_out2_enable else 0

	def enable_output(self, ch, enable):
		"""
		:param ch: Channel to enable or disable
		:param enable: boolean state of channel
		"""
		# Recalculate amplitude if the channel is enabled
		if(ch==1):
			self.pm_out1_enable = enable
			self.pm_out1_amplitude = self._pm_out1_amplitude if enable else 0

		if(ch==2):
			self.pm_out2_enable = enable
			self.pm_out2_amplitude = self._pm_out2_amplitude if enable else 0

_pm_siggen_reg_hdl = {
	'pm_out1_frequency':	((REG_PM_SG_FREQ1_H, REG_PM_SG_FREQ1_L),
											to_reg_unsigned(0, 48, xform=lambda obj, f:f * _PM_SG_FREQSCALE ),
											from_reg_unsigned(0, 48, xform=lambda obj, f: f / _PM_FREQSCALE )),
	'pm_out2_frequency':	((REG_PM_SG_FREQ2_H, REG_PM_SG_FREQ2_L),
											to_reg_unsigned(0, 48, xform=lambda obj, f:f * _PM_SG_FREQSCALE ),
											from_reg_unsigned(0, 48, xform=lambda obj, f: f /_PM_FREQSCALE )),
	'pm_out1_amplitude':	(REG_PM_SG_AMP, to_reg_unsigned(0, 16, xform=lambda obj, a: a / obj.dac_gains()[0]),
											from_reg_unsigned(0,16, xform=lambda obj, a: a * obj.dac_gains()[0])),
	'pm_out2_amplitude':	(REG_PM_SG_AMP, to_reg_unsigned(16, 16, xform=lambda obj, a: a / obj.dac_gains()[1]),
											from_reg_unsigned(16,16, xform=lambda obj, a: a * obj.dac_gains()[1]))
}

class PhaseMeter(_frame_instrument.FrameBasedInstrument, PhaseMeter_SignalGenerator): #TODO Frame instrument may not be appropriate when we get streaming going.
	""" PhaseMeter instrument object. This should be instantiated and attached to a :any:`Moku` instance.

	.. automethod:: pymoku.instruments.PhaseMeter.__init__

	.. attribute:: framerate
		:annotation: = 10

		Frame Rate, range 1 - 30.

	.. attribute:: type
		:annotation: = "phasemeter"

		Name of this instrument.

	"""

	def __init__(self):
		"""Create a new PhaseMeter instrument, ready to be attached to a Moku."""
		super(PhaseMeter, self).__init__()
		self._register_accessors(_pm_reg_handlers)
		
		self.id = 3
		self.type = "phasemeter"
		self.logname = "MokuPhaseMeterData"

		self.binstr = "<p32,0xAAAAAAAA:u48:u48:s15:p1,0:s48:s32:s32"
		self.procstr = ["*{:.16e} : *{:.16e} : : *{:.16e} : *C*{:.16e} : *C*{:.16e} ".format(_PM_HERTZ_SCALE, _PM_HERTZ_SCALE,  _PM_CYCLE_SCALE, _PM_VOLTS_SCALE, _PM_VOLTS_SCALE),
						"*{:.16e} : *{:.16e} : : *{:.16e} : *C*{:.16e} : *C*{:.16e} ".format(_PM_HERTZ_SCALE, _PM_HERTZ_SCALE,  _PM_CYCLE_SCALE, _PM_VOLTS_SCALE, _PM_VOLTS_SCALE)]


	def _update_datalogger_params(self, ch1, ch2):
		self.timestep = 1.0/self.get_samplerate()

		# Call this function when any instrument configuration parameters are set
		self.hdrstr = self._get_hdrstr(ch1,ch2)
		self.fmtstr = self._get_fmtstr(ch1,ch2)

	def set_samplerate(self, samplerate):
		""" Manually set the sample rate of the Phasemeter. 

		The chosen samplerate will be rounded down to nearest allowable rate 
		based on R(Hz) = 1e6/(2^N) where N in range [13,16].

		Alternatively use samplerate = {PM_LOGRATE_SLOW, PM_LOGRATE_FAST} 
		to set ~30Hz or ~120Hz.

		:type samplerate: float
		:param samplerate: Desired sample rate
		"""
		new_samplerate = _PM_UPDATE_RATE/min(max(1,samplerate),200)
		shift = min(math.ceil(math.log(new_samplerate,2)),16)
		self.output_decimation = 2**shift
		self.output_shift = shift

		log.debug("Output decimation: %f, Shift: %f, Samplerate: %f" % (self.output_decimation, shift, _PM_UPDATE_RATE/self.output_decimation))

	def get_samplerate(self):
		"""
		Get the current output sample rate of the phase meter.
		"""
		return _PM_UPDATE_RATE / self.output_decimation

	def get_timestep(self):
		return self.timestep

	def set_initfreq(self, ch, f):
		""" Manually set the initial frequency of the designated channel

		:type ch: int; *{1,2}*
		:param ch: Channel number to set the initial frequency of.

		:type f: int; *2e6 < f < 200e6*
		:param f: Initial locking frequency of the designated channel

		"""
		if _PM_FREQ_MIN <= f <= _PM_FREQ_MAX:
			if ch == 1:
				self.init_freq_ch1 = int(f);
			elif ch == 2:
				self.init_freq_ch2 = int(f);
			else:
				raise ValueError("Invalid channel number")
		else:
			raise ValueError("Initial frequency is not within the valid range.")

	def get_initfreq(self, ch):
		"""
		Reads the seed frequency register of the phase tracking loop
		Valid if auto acquire has not been used

		:type ch: int; *{1,2}*
		:param ch: Channel number to read the initial frequency of.
		"""
		if ch == 1:
			return self.init_freq_ch1
		elif ch == 2:
			return self.init_freq_ch2
		else:
			raise ValueError("Invalid channel number.")

	def _set_controlgain(self, v):
		#TODO: Put limits on the range of 'v'
		self.control_gain = v

	def _get_controlgain(self):
		return self.control_gain

	def set_bandwidth(self, ch, bw):
		"""
		Set the bandwidth of an ADC channel

		:type ch: int; *{1,2}*
		:param ch: ADC channel number to set bandwidth of.

		:type bw: float; Hz
		:param n: Desired bandwidth (will be rounded up to to the nearest multiple 10kHz * 2^N with N = [-6,0])
		"""
		if bw <= 0:
			raise ValueError("Invalid bandwidth (must be positive).")
		n = min(max(math.ceil(math.log(bw/10e3,2)),-6),0)

		if ch == 1:
			self.bandwidth_ch1 = n
		elif ch == 2:
			self.bandwidth_ch2 = n

	def get_bandwidth(self, ch):
		return 10e3 * (2**(self.bandwidth_ch1 if ch == 1 else self.bandwidth_ch2))

	def auto_acquire(self, ch):
		"""
		Auto-acquire the initial frequency of the specified channel

		:type ch: int; *{1,2}*
		:param ch: Channel number
		"""
		if ch == 1:
			self.autoacquire_ch1 = True
		elif ch == 2:
			self.autoacquire_ch2 = True
		else:
			raise ValueError("Invalid channel")

	def _get_hdrstr(self, ch1, ch2):
		chs = [ch1, ch2]

		hdr =  "% Moku:Phasemeter \r\n"
		for i,c in enumerate(chs):
			if c:
				r = self.get_frontend(i+1)
				hdr += "% Ch {i} - {} coupling, {} Ohm impedance, {} V range\r\n".format("AC" if r[2] else "DC", "50" if r[0] else "1M", "10" if r[1] else "1", i=i+1 )

		hdr += "%"
		for i,c in enumerate(chs):
			if c:
				hdr += "{} Ch {i} bandwidth = {:.10e} (Hz)".format("," if ((ch1 and ch2) and i == 1) else "", self.get_bandwidth(i+1), i=i+1)
		hdr += "\r\n"

		hdr += "% Acquisition rate: {:.10e} Hz\r\n".format(self.get_samplerate())
		hdr += "% {} 10 MHz clock\r\n".format("External" if self._moku._get_actual_extclock() else "Internal")
		hdr += "% Acquired {}\r\n".format(formatted_timestamp())
		hdr += "% Time,"
		for i,c in enumerate(chs):
			if c:
				hdr += "{} Set frequency {i} (Hz), Frequency {i} (Hz), Phase {i} (cyc), I {i} (V), Q {i} (V)".format("," if ((ch1 and ch2) and i == 1) else "", i=i+1)

		hdr += "\r\n"

		return hdr

	def _get_fmtstr(self, ch1, ch2):
		fmtstr = "{t:.10e}"
		if ch1:
			fmtstr += ", {ch1[0]:.16e}, {ch1[1]:.16e}, {ch1[3]:.16e}, {ch1[4]:.10e}, {ch1[5]:.10e}"
		if ch2:
			fmtstr += ", {ch2[0]:.16e}, {ch2[1]:.16e}, {ch2[3]:.16e}, {ch2[4]:.10e}, {ch2[5]:.10e}"
		fmtstr += "\r\n"
		return fmtstr

	def set_defaults(self):
		super(PhaseMeter, self).set_defaults()

		# Because we have to deal with a "frame" type instrument
		self.x_mode = _instrument.ROLL
		self.framerate = 0

		# Set basic configurations
		self.set_samplerate(1e3)
		self.set_initfreq(1, 10e6)
		self.set_initfreq(2, 10e6)

		# Set PI controller gains
		self._set_controlgain(100)
		self.control_shift = 0
		self.integrator_shift = 0
		self.output_shift = math.log(self.output_decimation,2)

		# Configuring the relays for impedance, voltage range etc.
		self.set_frontend(1, fiftyr=True, atten=True, ac=True)
		self.set_frontend(2, fiftyr=True, atten=True, ac=True)

		self.en_in_ch1 = True
		self.en_in_ch2 = True

		# TODO: Headers assume registers have been committed with current values
	def datalogger_start(self, start=0, duration=10, use_sd=True, ch1=True, ch2=True, filetype='csv'):
		self._update_datalogger_params(ch1, ch2)
		super(PhaseMeter, self).datalogger_start(start=start, duration=duration, use_sd=use_sd, ch1=ch1, ch2=ch2, filetype=filetype)

	datalogger_start.__doc__ = _frame_instrument.FrameBasedInstrument.datalogger_start.__doc__

	def datalogger_start_single(self, use_sd=True, ch1=True, ch2=True, filetype='csv'):
		self._update_datalogger_params(ch1, ch2)
		super(PhaseMeter, self).datalogger_start_single(use_sd=use_sd, ch1=ch1, ch2=ch2, filetype=filetype)

	datalogger_start_single.__doc__ = _frame_instrument.FrameBasedInstrument.datalogger_start_single.__doc__

_pm_reg_handlers = {
	'init_freq_ch1':		((REG_PM_INITF1_H, REG_PM_INITF1_L), 
											to_reg_unsigned(0,48, xform=lambda obj, f: f * _PM_FREQSCALE),
											from_reg_unsigned(0,48,xform=lambda obj, f: f / _PM_FREQSCALE)),
	'init_freq_ch2':		((REG_PM_INITF2_H, REG_PM_INITF2_L),
											to_reg_unsigned(0,48, xform=lambda obj, f: f * _PM_FREQSCALE),
											from_reg_unsigned(0,48,xform=lambda obj, f: f / _PM_FREQSCALE)),
	'control_gain':			(REG_PM_CGAIN,	to_reg_signed(0,16),
											from_reg_signed(0,16)),
	'control_shift':		(REG_PM_CGAIN,	to_reg_unsigned(20,4),
											from_reg_unsigned(20,4)),
	'integrator_shift':		(REG_PM_INTSHIFT, to_reg_unsigned(16,4),
											from_reg_unsigned(16,4)),
	'output_decimation':	(REG_PM_OUTDEC,	to_reg_unsigned(0,17),
											from_reg_unsigned(0,17)),
	'output_shift':			(REG_PM_OUTSHIFT, to_reg_unsigned(17,5),
											from_reg_unsigned(17,5)),
	'bandwidth_ch1':		(REG_PM_BW1, to_reg_signed(0,5, xform=lambda obj, b: b),
											from_reg_signed(0,5, xform=lambda obj, b: b)),
	'bandwidth_ch2':		(REG_PM_BW2, to_reg_signed(0,5, xform=lambda obj, b: b),
											from_reg_signed(0,5, xform=lambda obj, b: b)),
	'autoacquire_ch1':		(REG_PM_AUTOA1, to_reg_bool(0), from_reg_bool(0)),
	'autoacquire_ch2': 		(REG_PM_AUTOA2, to_reg_bool(0), from_reg_bool(0))
}
