
import math
import logging

from _instrument import *
from _oscilloscope import VoltsFrame
import _instrument
import _frame_instrument
import _siggen

# Annoying that import * doesn't pick up function defs??
_sgn = _instrument._sgn
_usgn = _instrument._usgn

log = logging.getLogger(__name__)

REG_LIA_OUTSEL		= 65
REG_LIA_TRIGMODE	= 66
REG_LIA_TRIGCTL		= 67
REG_LIA_TRIGLVL		= 68
REG_LIA_ACTL		= 69
REG_LIA_DECIMATION	= 70

REG_LIA_ENABLES		= 96
REG_LIA_PIDGAIN1	= 97
REG_LIA_PIDGAIN2	= 113
REG_LIA_INT_IGAIN	= 98
REG_LIA_INT_IFBGAIN	= 99
REG_LIA_INT_PGAIN	= 100
REG_LIA_DIFF_DGAIN	= 101
REG_LIA_DIFF_PGAIN	= 102
REG_LIA_DIFF_IGAIN	= 103
REG_LIA_DIFF_IFBGAIN	= 104
REG_LIA_FREQDEMOD_L	= 105
REG_LIA_FREQDEMOD_H	= 106
REG_LIA_PHASEDEMOD_L	= 107
REG_LIA_PHASEDEMOD_H	= 108
REG_LIA_DECBITSHIFT	= 109
REG_LIA_DECOUTPUTSELECT = 110
REG_LIA_MONSELECT0	= 111
REG_LIA_MONSELECT1	= 114
REG_LIA_SINEOUTAMP		= 112
REG_LIA_IN_OFFSET1 = 115
REG_LIA_OUT_OFFSET1 = 116
REG_LIA_IN_OFFSET2 = 117
REG_LIA_OUT_OFFSET2 = 118

# REG_OSC_OUTSEL constants
LIA_SOURCE_ADC		= 0
LIA_SOURCE_DAC		= 1

# REG_OSC_TRIGMODE constants
LIA_TRIG_AUTO		= 0
LIA_TRIG_NORMAL		= 1
LIA_TRIG_SINGLE		= 2

# REG_OSC_TRIGLVL constants
LIA_TRIG_CH1		= 0
LIA_TRIG_CH2		= 1
LIA_TRIG_DA1		= 2
LIA_TRIG_DA2		= 3

LIA_EDGE_RISING		= 0
LIA_EDGE_FALLING	= 1
LIA_EDGE_BOTH		= 2

LIA_ROLL			= _instrument.ROLL
LIA_SWEEP			= _instrument.SWEEP
LIA_FULL_FRAME		= _instrument.FULL_FRAME

_LIA_LB_ROUND		= 0
_LIA_LB_CLIP		= 1

_LIA_AIN_DDS		= 0
_LIA_AIN_DECI		= 1

_LIA_ADC_SMPS		= _instrument.ADC_SMP_RATE
_LIA_BUFLEN			= _instrument.CHN_BUFLEN
_LIA_SCREEN_WIDTH	= 1024
_LIA_FPS			= 10



### Every constant that starts with LIA_ will become an attribute of pymoku.instruments ###

LIA_MONITOR_I		= 0
LIA_MONITOR_Q		= 1
LIA_MONITOR_PID		= 2
LIA_MONITOR_INPUT	= 3

_LIA_CONTROL_FS 	= 125e6
_LIA_SINE_FS		= 1e9
_LIA_COEFF_WIDTH	= 16
_LIA_FREQSCALE		= float(1e9) / 2**48
_LIA_PHASESCALE		= 1.0 / 2**48
_LIA_AMPSCALE		= 4.0 / (2**16)


class LockInAmp(_frame_instrument.FrameBasedInstrument):
	""" Oscilloscope instrument object. This should be instantiated and attached to a :any:`Moku` instance.

	.. automethod:: pymoku.instruments.Oscilloscope.__init__

	.. attribute:: hwver

		Hardware Version

	.. attribute:: hwserial

		Hardware Serial Number

	.. attribute:: framerate
		:annotation: = 10

		Frame Rate, range 1 - 30.

	.. attribute:: type
		:annotation: = "oscilloscope"

		Name of this instrument.

	"""
	def __init__(self):
		"""Create a new Lock-In-Amplifier instrument, ready to be attached to a Moku."""
		self.scales = {}

		super(LockInAmp, self).__init__(VoltsFrame, scales=self.scales)
		self.id = 8
		self.type = "lockinamp"
		self.calibration = None

		self.decimation_rate = 1
	def _calculate_scales(self):
		# Returns the bits-to-volts numbers for each channel in the current state

		sect1 = "calibration.AG-%s-%s-%s-1" % ( "50" if self.relays_ch1 & RELAY_LOWZ else "1M",
								  "L" if self.relays_ch1 & RELAY_LOWG else "H",
								  "D" if self.relays_ch1 & RELAY_DC else "A")

		sect2 = "calibration.AG-%s-%s-%s-1" % ( "50" if self.relays_ch2 & RELAY_LOWZ else "1M",
								  "L" if self.relays_ch2 & RELAY_LOWG else "H",
								  "D" if self.relays_ch2 & RELAY_DC else "A")
		try:
			g1 = 1 / float(self.calibration[sect1])
			g2 = 1 / float(self.calibration[sect2])
		except (KeyError, TypeError):
			log.warning("Moku appears uncalibrated")
			g1 = g2 = 1

		log.debug("gain values for sections %s, %s = %f, %f; deci %f", sect1, sect2, g1, g2, self._deci_gain())

		if self.ain_mode == _LIA_AIN_DECI:
			g1 /= self._deci_gain()
			g2 /= self._deci_gain()

		return (g1, g2)	

	def commit(self):
		super(LockInAmp, self).commit()
		self.scales[self._stateid] = self._calculate_scales()

	def set_defaults(self):
		""" Reset the lockinamp to sane defaults. """
		super(LockInAmp, self).set_defaults()
		#TODO this should reset ALL registers
		self.calibration = None

		self.set_xmode(LIA_FULL_FRAME)
		self.set_timebase(-0.25, 0.25)
		self.set_precision_mode(False)
		self.set_frontend(1, True, True, True)
		self.framerate = _LIA_FPS
		self.frame_length = _LIA_SCREEN_WIDTH
		self.trig_mode = LIA_TRIG_AUTO
		self.set_trigger(LIA_TRIG_CH1, LIA_EDGE_RISING, 0)

		self.pid1_en = 1
		self.pid2_en = 1
		self.pid1_int_i_en = 1
		self.pid2_int_i_en = 1
		self.pid1_int_dc_pole = 0
		self.pid2_int_dc_pole = 0
		self.pid1_int_p_en = 0
		self.pid2_int_p_en = 0
		self.pid1_diff_d_en = 0
		self.pid2_diff_d_en = 0
		self.pid1_diff_i_en = 0
		self.pid2_diff_i_en = 0
		self.pid1_bypass = 0
		self.pid2_bypass = 0
		self.lo_reset = 0

		self.pid1_int_ifb_gain = 1.0 - 2*math.pi*1e6/125e6
		self.pid2_int_ifb_gain = 1.0 - 2*math.pi*1e6/125e6

		self.pid1_pidgain = 2**16
		self.pid2_pidgain = 2**16
		self.pid1_int_i_gain = 20000.0 / (2**15 - 1)# 2**1/(2**15-1)
		self.pid2_int_i_gain = 20000.0 / (2**15 - 1) #1000.0/(2**15-1)
		self.pid1_int_p_gain = 0
		self.pid2_int_p_gain = 0
		self.pid1_diff_d_gain = 0
		self.pid2_diff_d_gain = 0
		self.pid1_diff_p_gain = 0
		self.pid2_diff_p_gain = 0
		self.pid1_diff_i_gain = 0
		self.pid2_diff_i_gain = 0
		self.pid1_diff_ifb_gain = 0
		self.pid2_diff_ifb_gain = 0
		self.frequency_demod = 10e6
		self.phase_demod = 0
		self.decimation_bitshift = 0#7
		self.decimation_output_select = 1
		self.monitor_select0 = 1
		self.monitor_select1 = 1
		self.trigger_level = 0
		self.sineout_amp = 1
		self.pid1_in_offset  = 0
		self.pid1_out_offset = 0
		self.pid2_in_offset = 0
		self.pid2_out_offset = 0

	def set_filter_parameters(self, ReqCorner, FilterGain, Order):
		DSPCoeff = (1-ReqCorner/self._LIA_CONTROL_FS)*(2**_LIA_COEFF_WIDTH-1)

		self.pid1_int_ifb_gain = DSPCoeff
		self.pid2_int_ifb_gain = DSPCoeff
		
		if Order == 1:
			self.pid2_bypass = 1
		elif Order == 2:
			self.pid2_bypass = 0
		else:
			self.pid1_bypass = 1
			self.pid2_bypass = 1 

	# def convert_corner(self, ReqCorner):
	# 	DSPCoeff = (1-ReqCorner/self._LIA_CONTROL_FS)*(2**_LIA_COEFF_WIDTH-1)
	# 	return DSPCoeff

	# def convert_frequency(self, ReqFrequency):
	# 	DSPFreq = 2**48*ReqFrequency/self._LIA_SINE_FS
	# 	return DSPFreq

	# def convert_gain(self, ReqGain):
	# 	DSPGain = ReqGain/(2**(self._LIA_COEFF_WIDTH-1)-1)
	# 	return DSPGain
	def _optimal_decimation(self, t1, t2):
		# Based on mercury_ipad/LISettings::OSCalculateOptimalADCDecimation
		ts = abs(t1 - t2)
		return math.ceil(_LIA_ADC_SMPS * ts / _LIA_BUFLEN)

	def _buffer_offset(self, t1, t2, decimation):
		# Based on mercury_ipad/LISettings::OSCalculateOptimalBufferOffset
		# TODO: Roll mode

		buffer_smps = _LIA_ADC_SMPS / decimation
		offset_secs = t1
		offset = round(min(max(math.ceil(offset_secs * buffer_smps / 4.0), -2**28), 2**12))

		return offset

	def _render_downsample(self, t1, t2, decimation):
		# Based on mercury_ipad/LISettings::OSCalculateRenderDownsamplingForDecimation
		buffer_smps = _LIA_ADC_SMPS / decimation
		screen_smps = min(_LIA_SCREEN_WIDTH / abs(t1 - t2), _LIA_ADC_SMPS)

		return round(min(max(buffer_smps / screen_smps, 1.0), 16.0))

	def _render_offset(self, t1, t2, decimation, buffer_offset, render_decimation):
		# Based on mercury_ipad/LISettings::OSCalculateFrameOffsetForDecimation
		buffer_smps = _LIA_ADC_SMPS / decimation
		trig_in_buf = 4 * buffer_offset # TODO: Roll Mode
		time_buff_start = -trig_in_buf / buffer_smps
		time_buff_end = time_buff_start + (_LIA_BUFLEN - 1) / buffer_smps
		time_screen_centre = abs(t1 - t2) / 2
		screen_span = render_decimation / buffer_smps * _LIA_SCREEN_WIDTH

		# Allows for scrolling past the end of the trace
		time_left = max(min(time_screen_centre - screen_span / 2, time_buff_end - screen_span), time_buff_start)

		return math.ceil(-time_left * buffer_smps)

		# For now, only support viewing the whole captured buffer
		#return buffer_offset * 4

	def _deci_gain(self):
		if self.decimation_rate == 0:
			return 1

		if self.decimation_rate < 2**20:
			return self.decimation_rate
		else:
			return self.decimation_rate / 2**10

	def _update_datalogger_params(self, ch1, ch2):
		samplerate = _LIA_ADC_SMPS / self.decimation_rate
		self.timestep = 1 / samplerate

		if self.ain_mode == _LIA_AIN_DECI:
			self.procstr[0] = "*C/{:f}".format(self._deci_gain())
			self.procstr[1] = "*C/{:f}".format(self._deci_gain())
		else:
			self.procstr[0] = "*C"
			self.procstr[1] = "*C"
		self.fmtstr = self.get_fmtstr(ch1,ch2)
		self.hdrstr = self.get_hdrstr(ch1,ch2)

	def datalogger_start(self, start, duration, use_sd, ch1, ch2, filetype):
		self._update_datalogger_params(ch1, ch2)
		super(LockInAmp, self).datalogger_start(start=start, duration=duration, use_sd=use_sd, ch1=ch1, ch2=ch2, filetype=filetype)

	def datalogger_start_single(self, use_sd, ch1, ch2, filetype):
		self._update_datalogger_params(ch1, ch2)
		super(LockInAmp, self).datalogger_start_single(use_sd=use_sd, ch1=ch1, ch2=ch2, filetype=filetype)

	def _set_render(self, t1, t2, decimation):
		self.render_mode = RDR_CUBIC #TODO: Support other
		self.pretrigger = self._buffer_offset(t1, t2, self.decimation_rate)
		self.render_deci = self._render_downsample(t1, t2, self.decimation_rate)
		self.offset = self._render_offset(t1, t2, self.decimation_rate, self.pretrigger, self.render_deci)

		# Set alternates to regular, means we get distorted frames until we get a new trigger
		self.render_deci_alt = self.render_deci
		self.offset_alt = self.offset

		log.debug("Render params: Deci %f PT: %f, RDeci: %f, Off: %f", self.decimation_rate, self.pretrigger, self.render_deci, self.offset)

	def set_timebase(self, t1, t2):
		""" Set the left- and right-hand span for the time axis.
		Units are seconds relative to the trigger point.

		:type t1: float
		:param t1:
			Time, in seconds, from the trigger point to the left of screen. This may be negative (trigger on-screen)
			or positive (trigger off the left of screen).

		:type t2: float
		:param t2: As *t1* but to the right of screen.
		"""
		self.decimation_rate = self._optimal_decimation(t1, t2)
		self._set_render(t1, t2, self.decimation_rate)

	def set_samplerate(self, samplerate):
		""" Manually set the sample rate of the instrument.

		The sample rate is automatically calcluated and set in :any:`set_timebase`; setting it through this
		interface if you've previously set the scales through that will have unexpected results.

		This interface is most useful for datalogging and similar aquisition where one will not be looking
		at data frames.

		:type samplerate: float; *0 < samplerate < 500MSPS*
		:param samplerate: Target samples per second. Will get rounded to the nearest allowable unit.
		"""
		self.decimation_rate = _LIA_ADC_SMPS / samplerate

	def get_samplerate(self):
		return _LIA_ADC_SMPS / self.decimation_rate

	def set_xmode(self, xmode):
		"""
		Set rendering mode for the horizontal axis.

		:type xmode: *OSC_ROLL*, *OSC_SWEEP*, *OSC_FULL_FRAME*
		:param xmode:
			Respectively; Roll Mode (scrolling), Sweep Mode (normal oscilloscope trace sweeping across the screen)
			or Full Frame (Like sweep, but waits for the frame to be completed).
		"""
		self.x_mode = xmode

	def set_precision_mode(self, state):
		""" Change aquisition mode between downsampling and decimation.
		Precision mode, a.k.a Decimation, samples at full rate and applies a low-pass filter to the data. This improves
		precision. Normal mode works by direct downsampling, throwing away points it doesn't need.

		:param state: Select Precision Mode
		:type state: bool """

	def set_trigger(self, source, edge, level, hysteresis=0, hf_reject=False, mode=LIA_TRIG_AUTO):
		""" Sets trigger source and parameters.

		:type source: OSC_TRIG_CH1, OSC_TRIG_CH2, OSC_TRIG_DA1, OSC_TRIG_DA2
		:param source: Trigger Source. May be either ADC Channel or either DAC Channel, allowing one to trigger off a synthesised waveform.

		:type edge: OSC_EDGE_RISING, OSC_EDGE_FALLING, OSC_EDGE_BOTH
		:param edge: Which edge to trigger on.

		:type level: float, volts
		:param level: Trigger level

		:type hysteresis: float, volts
		:param hysteresis: Hysteresis to apply around trigger point."""
		self.trig_ch = source
		self.trig_edge = edge
		self.hysteresis = hysteresis
		self.hf_reject = hf_reject
		self.trig_mode = mode


_lia_reg_hdl = [
	('source_ch1',		REG_LIA_OUTSEL,		lambda s, old: (old & ~1) | s if s in [LIA_SOURCE_ADC, LIA_SOURCE_DAC] else None,
											lambda rval: rval & 1),
	('source_ch2',		REG_LIA_OUTSEL,		lambda s, old: (old & ~2) | s << 1 if s in [LIA_SOURCE_ADC, LIA_SOURCE_DAC] else None,
											lambda rval: rval & 2 >> 1),
	('trig_mode',		REG_LIA_TRIGMODE,	lambda s, old: (old & ~3) | s if s in [LIA_TRIG_AUTO, LIA_TRIG_NORMAL, LIA_TRIG_SINGLE] else None,
											lambda rval: rval & 3),
	('trig_edge',		REG_LIA_TRIGCTL,	lambda s, old: (old & ~3) | s if s in [LIA_EDGE_RISING, LIA_EDGE_FALLING, LIA_EDGE_BOTH] else None,
											lambda rval: rval & 3),
	('trig_ch',			REG_LIA_TRIGCTL,	lambda s, old: (old & ~0x7F0) | s << 4 if s in
												[LIA_TRIG_CH1, LIA_TRIG_CH2, LIA_TRIG_DA1, LIA_TRIG_DA2] else None,
											lambda rval: rval & 0x7F0 >> 4),
	('hf_reject',		REG_LIA_TRIGCTL,	lambda s, old: (old & ~0x1000) | s << 12 if int(s) in [0, 1] else None,
											lambda rval: rval & 0x1000 >> 12),
	('hysteresis',		REG_LIA_TRIGCTL,	lambda s, old: (old & ~0xFFFF0000) | s << 16 if 0 <= s < 2**16 else None,
											lambda rval: rval & 0xFFFF0000 >> 16),
	('trigger_level',	REG_LIA_TRIGLVL,	lambda s, old: _sgn(s, 32),
											lambda rval: rval),
	('loopback_mode',	REG_LIA_ACTL,		lambda m, old: (old & ~0x01) | m if m in [_LIA_LB_CLIP, _LIA_LB_ROUND] else None,
											lambda rval: rval & 0x01),
	('ain_mode',		REG_LIA_ACTL,		lambda m, old: (old & ~0x30000) | (m << 16) if m in [_LIA_AIN_DDS, _LIA_AIN_DECI] else None,
											lambda rval: (rval & 0x30000) >> 16),
	('decimation_rate',	REG_LIA_DECIMATION,	lambda r, old: _usgn(r, 32), lambda rval: rval),
	('pid1_en',		REG_LIA_ENABLES,		lambda s, old: (old & ~1) | int(s),
											lambda rval: rval & 1),
	('pid2_en',		REG_LIA_ENABLES,		lambda s, old: (old & ~2) | int(s) << 1,
											lambda rval: rval & 2 >> 1),
	('pid1_int_i_en',	REG_LIA_ENABLES,	lambda s, old: (old & ~2**2) | int(s) << 2,
											lambda rval: rval & 2 >> 2),
	('pid2_int_i_en',	REG_LIA_ENABLES,	lambda s, old: (old & ~2**3) | int(s) << 3,
											lambda rval: rval & 2 >> 3),
	('pid1_int_p_en',	REG_LIA_ENABLES,	lambda s, old: (old & ~2**4) | int(s) << 4,
											lambda rval: rval & 2 >> 4),
	('pid2_int_p_en',	REG_LIA_ENABLES,	lambda s, old: (old & ~2**5) | int(s) << 5,
											lambda rval: rval & 2 >> 5),
	('pid1_diff_d_en',	REG_LIA_ENABLES,	lambda s, old: (old & ~2**6) | int(s) << 6,
											lambda rval: rval & 2 >> 6),
	('pid2_diff_d_en',	REG_LIA_ENABLES,	lambda s, old: (old & ~2**7) | int(s) << 7,
											lambda rval: rval & 2 >> 7),
	('pid1_diff_p_en',	REG_LIA_ENABLES,	lambda s, old: (old & ~2**8) | int(s) << 8,
											lambda rval: rval & 2 >> 8),
	('pid2_diff_p_en',	REG_LIA_ENABLES,	lambda s, old: (old & ~2**9) | int(s) << 9,
											lambda rval: rval & 2 >> 9),
	('pid1_diff_i_en',	REG_LIA_ENABLES,	lambda s, old: (old & ~2**10) | int(s) << 10,
											lambda rval: rval & 2 >> 10),
	('pid2_diff_i_en',	REG_LIA_ENABLES,	lambda s, old: (old & ~2**11) | int(s) << 11,
											lambda rval: rval & 2 >> 11),
	('pid1_bypass',	REG_LIA_ENABLES,		lambda s, old: (old & ~2**12) | int(s) << 12,
											lambda rval: rval & 2 >> 12),
	('pid2_bypass',	REG_LIA_ENABLES,		lambda s, old: (old & ~2**13) | int(s) << 13,
											lambda rval: rval & 2 >> 13),
	('lo_reset',	REG_LIA_ENABLES,		lambda s, old: (old & ~2**14) | int(s) << 14,
											lambda rval: rval & 2 >> 14),
	('pid1_int_dc_pole',	REG_LIA_ENABLES,lambda s, old: (old & ~2**15) | int(s) << 15,
											lambda rval: rval & 2 >> 15),
	('pid2_int_dc_pole',	REG_LIA_ENABLES,lambda s, old: (old & ~2**16) | int(s) << 16,
											lambda rval: rval & 2 >> 16),
	('pid1_in_offset',	REG_LIA_IN_OFFSET1,	lambda s, old: (old & ~0x00FFFFFF) | _sgn(s,25),
											lambda rval: (rval & 0x00FFFFFF)),
	('pid1_out_offset',	REG_LIA_OUT_OFFSET1,lambda s, old: (old & ~0x00FFFFFF) | _sgn(s,25),
											lambda rval: (rval & 0x00FFFFFF)),
	('pid2_in_offset',	REG_LIA_IN_OFFSET2,	lambda s, old: (old & ~0x00FFFFFF) | _sgn(s,25),
											lambda rval: (rval & 0x00FFFFFF)),
	('pid2_out_offset',	REG_LIA_OUT_OFFSET2,lambda s, old: (old & ~0x00FFFFFF) | _sgn(s,25),
											lambda rval: (rval & 0x00FFFFFF)),																							
	('pid1_pidgain',	REG_LIA_PIDGAIN1,	lambda s, old: (old & ~0xFFFFFFFF) | _sgn(s,32), 
											lambda rval: (rval & 0xFFFFFFFF)/(2**15 -1)),
	('pid2_pidgain',	REG_LIA_PIDGAIN2,	lambda s, old: (old & ~0xFFFFFFFF) | _sgn(s,32) , 
											lambda rval: (rval & 0xFFFFFFF)/(2**15 -1)),
	('pid1_int_i_gain',	REG_LIA_INT_IGAIN,	lambda s, old: (old & ~0x0000FFFF) | _sgn(s * (2**15 - 1), 16), 
											lambda rval: (rval & 0x0000FFFF)*(2**15 -1)),
	('pid2_int_i_gain',	REG_LIA_INT_IGAIN,	lambda s, old: (old & ~0xFFFF0000) | _sgn(s * (2**15 - 1), 16) << 16, 
											lambda rval: (rval & 0xFFFF0000)*(2**15 -1)),
	('pid1_int_ifb_gain',	REG_LIA_INT_IFBGAIN,
											lambda s, old: (old & ~0x0000FFFF) | _usgn(s * (2**16), 16), 
											lambda rval: (rval & 0x0000FFFF)*(2**15 -1)),
	('pid2_int_ifb_gain',	REG_LIA_INT_IFBGAIN,
											lambda s, old: (old & ~0xFFFF0000) | _usgn(s * (2**16) ,16) << 16, 
											lambda rval: (rval & 0xFFFF0000)*(2**15 -1)),
	('pid1_int_p_gain',	REG_LIA_INT_PGAIN,
											lambda s, old: (old & ~0x0000FFFF) | _sgn(s * (2**15 - 1), 16), 
											lambda rval: (rval & 0x0000FFFF)*(2**15 -1)),
	('pid2_int_p_gain',	REG_LIA_INT_PGAIN,
											lambda s, old: (old & ~0xFFFF0000) | _sgn(s * (2**15 - 1), 16) << 16, 
											lambda rval: (rval & 0xFFFF0000)*(2**15 -1)),
	('pid1_diff_d_gain',	REG_LIA_DIFF_DGAIN,
											lambda s, old: (old & ~0x0000FFFF) | _sgn(s * (2**15 - 1), 16), 
											lambda rval: (rval & 0x0000FFFF)*(2**15 -1)),
	('pid2_diff_d_gain',	REG_LIA_DIFF_DGAIN,
											lambda s, old: (old & ~0xFFFF0000) | _sgn(s * (2**15 - 1), 16) << 16, 
											lambda rval: (rval & 0xFFFF0000) * (2**15 - 1)),
	('pid1_diff_p_gain',	REG_LIA_DIFF_PGAIN,
											lambda s, old: (old & ~0x0000FFFF) | _sgn(s * (2**15 - 1), 16), 
											lambda rval: (rval & 0x0000FFFF)*(2**15 -1)),
	('pid2_diff_p_gain',	REG_LIA_DIFF_PGAIN,
											lambda s, old: (old & ~0xFFFF0000) | _sgn(s * (2**15 - 1), 16) << 16, 
											lambda rval: (rval & 0xFFFF0000)*(2**15 -1)),
	('pid1_diff_i_gain',	REG_LIA_DIFF_IGAIN,
											lambda s, old: (old & ~0x0000FFFF) | _sgn(s * (2**15 - 1), 16), 
											lambda rval: (rval & 0x0000FFFF)*(2**15 -1)),
	('pid2_diff_i_gain',	REG_LIA_DIFF_IGAIN,
											lambda s, old: (old & ~0xFFFF0000) | _sgn(s * (2**15 - 1), 16) << 16, 
											lambda rval: (rval & 0xFFFF0000) * (2**15 -1)),
	('pid1_diff_ifb_gain',	REG_LIA_DIFF_IFBGAIN,
											lambda s, old: (old & ~0x0000FFFF) | _sgn(s * (2**15 - 1), 16), 
											lambda rval: (rval & 0x0000FFFF) * (2**15 -1)),
	('pid2_diff_ifb_gain',	REG_LIA_DIFF_IFBGAIN,
											lambda s, old: (old & ~0xFFFF0000) | _sgn(s * (2**15 - 1), 16) << 16, 
											lambda rval: (rval & 0xFFFF0000) * (2**15 -1)),
	('frequency_demod', 	(REG_LIA_FREQDEMOD_H, REG_LIA_FREQDEMOD_L),
											lambda s, old: ((old[0] & ~0x0000FFFF) | _usgn(s / _LIA_FREQSCALE, 48) >> 32 , _usgn(s / _LIA_FREQSCALE, 48) & 0xFFFFFFFF),
											lambda rval: _LIA_FREQSCALE * ((rval[0] & 0x0000FFFF) << 32 | rval[1])),
	('phase_demod', 		(REG_LIA_PHASEDEMOD_H, REG_LIA_PHASEDEMOD_L),
											lambda s, old: ((old[0] & ~0x0000FFFF) | _usgn(s / _LIA_PHASESCALE, 48) >> 32 , _usgn(s / _LIA_PHASESCALE, 48) & 0xFFFFFFFF),
											lambda rval: _LIA_PHASESCALE * ((rval[0] & 0x0000FFFF) << 32 | rval[1])),
	('decimation_bitshift',	REG_LIA_DECBITSHIFT,
											lambda s, old: (old & ~0x0000000F) | int(s), 
											lambda rval: rval & 0x0000000F),
	('decimation_output_select', REG_LIA_DECOUTPUTSELECT,
											lambda s, old: (old & ~0x0000000F) | int(s),
											lambda rval: rval & 0x0000000F),
	('monitor_select0', 		REG_LIA_MONSELECT0,
											lambda s, old: (old & ~3) | int(s),
											lambda rval: rval & 3),
	('monitor_select1', 		REG_LIA_MONSELECT1,
											lambda s, old: (old & ~3) | int(s),
											lambda rval: rval & 3),
	('sineout_amp',			REG_LIA_SINEOUTAMP,
											lambda s, old: (old & ~0x0000FFFF) | _usgn(s / _LIA_AMPSCALE,16),
											lambda rval: (rval & 0x0000FFFF) * _LIA_AMPSCALE),
	]
_instrument._attach_register_handlers(_lia_reg_hdl, LockInAmp)
