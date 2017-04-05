
import math
import logging

from pymoku._instrument import *
from pymoku._oscilloscope import VoltsFrame
from . import _instrument
from . import _frame_instrument
from . import _siggen

log = logging.getLogger(__name__)


# LOCKINAMP REGISTERS
REG_LIA_OUTSEL		= 65
REG_LIA_TRIGMODE	= 66
REG_LIA_TRIGCTL		= 67
REG_LIA_TRIGLVL		= 68
REG_LIA_ACTL		= 69
REG_LIA_DECIMATION	= 70

REG_LIA_ENABLES		= 96
REG_LIA_PIDGAIN1	= 97
REG_LIA_PIDGAIN2	= 113
REG_LIA_INT_IGAIN1	= 98
REG_LIA_INT_IGAIN2	= 99
REG_LIA_INT_IFBGAIN1= 100
REG_LIA_INT_IFBGAIN2= 101
REG_LIA_INT_PGAIN1	= 102
REG_LIA_INT_PGAIN2	= 103
REG_LIA_DIFF_DGAIN1	= 104
REG_LIA_DIFF_DGAIN2	= 119
REG_LIA_DIFF_PGAIN1	= 120
REG_LIA_DIFF_PGAIN2	= 121
REG_LIA_DIFF_IGAIN1	= 122
REG_LIA_DIFF_IGAIN2	= 123
REG_LIA_DIFF_IFBGAIN1	= 124
REG_LIA_DIFF_IFBGAIN2	= 125
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

REG_LIA_INPUT_GAIN = 126
REG_LIA_SINEOUTOFF = 127

# REG_LIA_OUTSEL constants
LIA_SOURCE_ADC		= 0
LIA_SOURCE_DAC		= 1

# REG_LIA_TRIGMODE constants
LIA_TRIG_AUTO		= 0
LIA_TRIG_NORMAL		= 1
LIA_TRIG_SINGLE		= 2

# REG_LIA_TRIGLVL constants
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

# SIGNAL PRECISION MODES
LIA_HIGH_PRECISION	= 1
LIA_HIGH_RANGE		= 0

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

_LIA_CONTROL_FS 	= 25e6
_LIA_SINE_FS		= 1e9
_LIA_COEFF_WIDTH	= 25
_LIA_FREQSCALE		= float(1e9) / 2**48
_LIA_PHASESCALE		= 1.0 / 2**48
_LIA_AMPSCALE		= 1.0 / (2**15 - 1)




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
	
		super(LockInAmp, self).__init__()
		self._register_accessors(_lia_reg_hdl)

		self.id = 8
		self.type = "lockinamp"
		self.calibration = None

		self.scales = {}
		self.decimation_rate = 1
		self._set_frame_class(VoltsFrame, scales=self.scales)

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

	commit.__doc__ = _frame_instrument.FrameBasedInstrument.commit.__doc__

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
		self.pid2_bypass = 1
		self.lo_reset = 0
		
		self.signal_mode = LIA_HIGH_RANGE
		self.set_filter_parameters(20, 1000, 1)

		self.set_pid_offset(0)

		self.pid1_int_p_gain = 0.0
		self.pid2_int_p_gain = 0.0
		self.pid1_diff_d_gain = 0.0
		self.pid2_diff_d_gain = 0.0
		self.pid1_diff_p_gain = 0.0
		self.pid2_diff_p_gain = 0.0
		self.pid1_diff_i_gain = 0.0
		self.pid2_diff_i_gain = 0.0
		self.pid1_diff_ifb_gain = 0.0
		self.pid2_diff_ifb_gain = 0.0
		self.frequency_demod = 40e6
		self.phase_demod = 0.5
		self.decimation_bitshift = 0#7
		self.decimation_output_select = 0
		self.monitor_select0 = 2
		self.monitor_select1 = 2
		self.trigger_level = 0

		self.input_gain = 1
		self.set_lo_output_amp(.5)
		self.set_lo_offset(0)

	def set_filter_parameters(self, Gain_dB, ReqCorner, Order):
		"""
		:param Gain_dB: Overall gain of the low-pass filter
		:param ReqCorner: Corner frequency of the low-pass filter
		:param Order: 1 or 2, first- or second-order filter used
		"""
		DSPCoeff = 1-(2*math.pi*ReqCorner)/_LIA_CONTROL_FS
		self.pid1_int_ifb_gain = DSPCoeff
		self.pid2_int_ifb_gain = DSPCoeff

		self.pid1_int_i_gain = 1.0 - DSPCoeff
		self.pid2_int_i_gain = 1.0 - DSPCoeff
		
		if Order == 1:
			self.pid2_bypass = 1
			self.slope = 1
		elif Order == 2:
			self.pid2_bypass = 0
			self.slope = 2
		else:
			self.pid1_bypass = 1
			self.pid2_bypass = 1

		self._set_gain(Gain_dB)


	def _set_gain(self, Gain_dB):

		ImpedenceGain = 1 if (self.relays_ch1 & 2) == 2 else 2
		AttenGain = 1 if (self.relays_ch1 & 4) == 4 else 10
		
		gain_factor = ImpedenceGain * AttenGain * (10**(Gain_dB / 20.0)) * self._get_dac_calibration()[0] / self._get_adc_calibration()[0]
		log.debug("AttenGain, %f, GainFactor, %f", AttenGain, gain_factor)

		if self.signal_mode == LIA_HIGH_PRECISION:
			if self.slope == 1:
				self.input_gain = gain_factor
				self.pid1_pidgain = self.pid2_pidgain = 1.0
			else :
				self.input_gain = self.pid1_pidgain =  math.sqrt(gain_factor)
				self.pid2_pidgain = 1.0
		elif self.signal_mode == LIA_HIGH_RANGE:
			if self.slope == 1:
				self.pid1_pidgain =  gain_factor
				self.input_gain = self.pid2_pidgain = 1.0
			else :
				self.pid1_pidgain = self.pid2_pidgain = math.sqrt(gain_factor)
				self.input_gain = 1.0
		else:
			if self.slope == 1:
				self.pid1_pidgain =  gain_factor
				self.input_gain = self.pid2_pidgain = 1.0
			else :
				self.pid1_pidgain = self.pid2_pidgain = math.sqrt(gain_factor)
				self.input_gain = 1.0
			self.signal_mode = LIA_HIGH_RANGE
			raise InvalidOperationException("Signal Mode not set : defaulted to HIGH RANGE MODE")

	def set_pid_offset(self, offset):
		"""
		:param offset: Offset in volts
		"""
		# TODO: Use the new instrument reference in the lambda function to do conversion
		if self.slope == 1:
			self.pid1_out_offset = offset * self._get_dac_calibration()[0]
			self.pid2_out_offset = 0
		elif self.slope == 2:
			self.pid1_out_offset = 0
			self.pid2_out_offset = offset * self._get_dac_calibratioin()[0]
		else :
			self.slope == 1
			self.pid1_out_offset = offset * self._get_dac_calibration()[0]
			self.pid2_out_offset = 0
			raise InvalidOperationException("PID slope not set : defaulted to slope = %s" % self.slope)

	def set_lo_output_amp(self,amplitude):
		"""
		:param amplitude: Amplitude of local oscillator signal
		"""
		# converts amplitude (V) into the bits required for the register.
		# TODO: Use the new instrument reference in the lambda function to do this
		self.sineout_amp = amplitude * self._get_dac_calibration()[1]

	def set_lo_offset(self, offset):
		"""
		:param offset: offset in volts of the local oscillator
		"""
		# converts the offset in volts to the bits required for the offset register
		# TODO: Use the new instrument reference in the lambda function to do this
		self.sineout_offset = offset * self._get_dac_calibration()[1] 
			 
	def _get_dac_calibration(self):
		# returns the volts to bits numbers for the DAC channels in the current state

		sect1 = "calibration.DG-1"
		sect2 = "calibration.DG-2"

		try:
			g1 = float(self.calibration[sect1])
			g2 = float(self.calibration[sect2])
		except (KeyError, TypeError):
			log.warning("Moku appears uncalibrated")
			g1 = g2 = 1

		log.debug("gain values for dac sections %s, %s = %f, %f", sect1, sect2, g1, g2)

		return (g1, g2)

	def _get_adc_calibration(self):
		# Returns the volts to bits numbers for each channel in the current state

		sect1 = "calibration.AG-%s-%s-%s-1" % ( "50" if self.relays_ch1 & RELAY_LOWZ else "1M",
								  "L" if self.relays_ch1 & RELAY_LOWG else "H",
								  "D" if self.relays_ch1 & RELAY_DC else "A")

		sect2 = "calibration.AG-%s-%s-%s-2" % ( "50" if self.relays_ch1 & RELAY_LOWZ else "1M",
								  "L" if self.relays_ch1 & RELAY_LOWG else "H",
								  "D" if self.relays_ch1 & RELAY_DC else "A")

		try:
			g1 = float(self.calibration[sect1])
			g2 = float(self.calibration[sect2])
		except (KeyError, TypeError):
			log.warning("Moku adc appears uncalibrated")
			g1 = g2 = 1
		log.debug("gain values for adc sections %s, %s = %f, %f", sect1, sect2, g1, g2)
		return (g1, g2)

	def attach_moku(self, moku):
		super(LockInAmp, self).attach_moku(moku)

		try:
			self.calibration = dict(self._moku._get_property_section("calibration"))
		except:
			log.warning("Can't read calibration values.")

	attach_moku.__doc__ = MokuInstrument.attach_moku.__doc__

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

	datalogger_start.__doc__ = _frame_instrument.FrameBasedInstrument.datalogger_start.__doc__

	def datalogger_start_single(self, use_sd, ch1, ch2, filetype):
		self._update_datalogger_params(ch1, ch2)
		super(LockInAmp, self).datalogger_start_single(use_sd=use_sd, ch1=ch1, ch2=ch2, filetype=filetype)

	datalogger_start_single.__doc__ = _frame_instrument.FrameBasedInstrument.datalogger_start_single.__doc__

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

	def set_trigger(self, source, edge, level, hysteresis=0, hf_reject=False, mode=LIA_TRIG_AUTO):
		""" Sets trigger source and parameters.

		:type source: OSC_TRIG_CH1, OSC_TRIG_CH2, OSC_TRIG_DA1, OSC_TRIG_DA2
		:param source: Trigger Source. May be either ADC Channel or either DAC Channel, allowing one to trigger off a synthesised waveform.

		:type edge: OSC_EDGE_RISING, OSC_EDGE_FALLING, OSC_EDGE_BOTH
		:param edge: Which edge to trigger on.

		:type level: float, volts
		:param level: Trigger level

		:type hysteresis: float, volts
		:param hysteresis: Hysteresis to apply around trigger point.
		"""
		self.trig_ch = source
		self.trig_edge = edge
		self.hysteresis = hysteresis
		self.hf_reject = hf_reject
		self.trig_mode = mode

	def attach_moku(self, moku):
		super(LockInAmp, self).attach_moku(moku)

		try:
			self.calibration = dict(self._moku._get_property_section("calibration"))
		except:
			log.warning("Can't read calibration values.")

_lia_reg_hdl = {
	'source_ch1':		(REG_LIA_OUTSEL,	to_reg_unsigned(0, 1, allow_set=[LIA_SOURCE_ADC, LIA_SOURCE_DAC]),
											from_reg_unsigned(0, 1)),

	'source_ch2':		(REG_LIA_OUTSEL,	to_reg_unsigned(1, 1, allow_set=[LIA_SOURCE_ADC, LIA_SOURCE_DAC]),
											from_reg_unsigned(1, 1)),

	'trig_mode':		(REG_LIA_TRIGMODE,	to_reg_unsigned(0, 2, allow_set=[LIA_TRIG_AUTO, LIA_TRIG_NORMAL, LIA_TRIG_SINGLE]),
											from_reg_unsigned(0, 2)),

	'trig_edge':		(REG_LIA_TRIGCTL,	to_reg_unsigned(0, 2, allow_set=[LIA_EDGE_RISING, LIA_EDGE_FALLING, LIA_EDGE_BOTH]),
											from_reg_unsigned(0, 2)),

	'trig_ch':			(REG_LIA_TRIGCTL,	to_reg_unsigned(4, 6, allow_set=[LIA_TRIG_CH1, LIA_TRIG_CH2, LIA_TRIG_DA1, LIA_TRIG_DA2]),
											from_reg_unsigned(4, 6)),

	'hf_reject':		(REG_LIA_TRIGCTL,	to_reg_bool(12),			from_reg_bool(12)),
	'hysteresis':		(REG_LIA_TRIGCTL,	to_reg_unsigned(16, 16),	from_reg_unsigned(16, 16)),
	'trigger_level':	(REG_LIA_TRIGLVL,	to_reg_signed(0, 32),		to_reg_signed(0, 32)),

	'loopback_mode_ch1':	(REG_LIA_ACTL,	to_reg_unsigned(0, 1, allow_set=[_LIA_LB_CLIP, _LIA_LB_ROUND]),
											from_reg_unsigned(0, 1)),
	'loopback_mode_ch2':	(REG_LIA_ACTL,	to_reg_unsigned(1, 1, allow_set=[_LIA_LB_CLIP, _LIA_LB_ROUND]),
											from_reg_unsigned(1, 1)),

	'ain_mode':			(REG_LIA_ACTL,		to_reg_unsigned(2, 16, allow_set=[_LIA_AIN_DDS, _LIA_AIN_DECI]),
											from_reg_unsigned(2, 16)),

	'decimation_rate':	(REG_LIA_DECIMATION,to_reg_unsigned(0, 32),	
											from_reg_unsigned(0, 32)),

	'pid1_en':		(REG_LIA_ENABLES,		to_reg_bool(0),
											from_reg_bool(0)),

	'pid2_en':		(REG_LIA_ENABLES,		to_reg_bool(1),
											from_reg_bool(1)),

	'pid1_int_i_en':	(REG_LIA_ENABLES,	to_reg_bool(2),
											from_reg_bool(2)),

	'pid2_int_i_en':	(REG_LIA_ENABLES,	to_reg_bool(3),
											from_reg_bool(3)),

	'pid1_int_p_en':	(REG_LIA_ENABLES,	to_reg_bool(4),
											from_reg_bool(4)),
	'pid2_int_p_en':	(REG_LIA_ENABLES,	to_reg_bool(5),
											from_reg_bool(5)),

	'pid1_diff_d_en':	(REG_LIA_ENABLES,	to_reg_bool(6),
											from_reg_bool(6)),

	'pid2_diff_d_en':	(REG_LIA_ENABLES,	to_reg_bool(7),
											from_reg_bool(7)),

	'pid1_diff_p_en':	(REG_LIA_ENABLES,	to_reg_bool(8),
											from_reg_bool(8)),

	'pid2_diff_p_en':	(REG_LIA_ENABLES,	to_reg_bool(9),
											from_reg_bool(9)),

	'pid1_diff_i_en':	(REG_LIA_ENABLES,	to_reg_bool(10),
											from_reg_bool(10)),

	'pid2_diff_i_en':	(REG_LIA_ENABLES,	to_reg_bool(11),
											from_reg_bool(11)),

	'pid1_bypass':	(REG_LIA_ENABLES,		to_reg_bool(12),
											from_reg_bool(12)),

	'pid2_bypass':	(REG_LIA_ENABLES,		to_reg_bool(13),
											from_reg_bool(13)),

	'lo_reset':		(REG_LIA_ENABLES,		to_reg_bool(14),
											from_reg_bool(14)),

	'pid1_int_dc_pole':	(REG_LIA_ENABLES,	to_reg_bool(15),
											from_reg_bool(15)),

	'pid2_int_dc_pole':	(REG_LIA_ENABLES,	to_reg_bool(16),
											from_reg_bool(16)),

	'pid1_in_offset':	(REG_LIA_IN_OFFSET1,to_reg_signed(0, 16),
											from_reg_signed(0, 16)),

	'pid2_in_offset':	(REG_LIA_IN_OFFSET2,to_reg_signed(0, 16),
											from_reg_signed(0, 16)),

	'pid1_out_offset':	(REG_LIA_OUT_OFFSET1,to_reg_signed(0, 16),
											from_reg_signed(0, 16)),	

	'pid2_out_offset':	(REG_LIA_OUT_OFFSET2,to_reg_signed(0, 16),
											from_reg_signed(0, 16)),

	'pid1_pidgain':		(REG_LIA_PIDGAIN1,	to_reg_signed(0, 32, xform=lambda x : x * 2**16),
											from_reg_signed(0, 32, xform=lambda x: x / 2**16)),

	'pid2_pidgain':		(REG_LIA_PIDGAIN2,	to_reg_signed(0, 32, xform=lambda x : x * 2**16),
											from_reg_signed(0, 32, xform=lambda x: x / 2**16)),

	'pid1_int_i_gain':	(REG_LIA_INT_IGAIN1,	to_reg_signed(0, 25, xform=lambda x: x*(2**24 -1)),
											from_reg_signed(0, 25, xform=lambda x: x / (2**24-1))),

	'pid2_int_i_gain':	(REG_LIA_INT_IGAIN2,	to_reg_signed(0, 25, xform=lambda x: x*(2**24 -1)),
											from_reg_signed(0, 25, xform=lambda x: x / (2**24-1))),

	'pid1_int_ifb_gain':	(REG_LIA_INT_IFBGAIN1,	to_reg_signed(0, 25, xform=lambda x: x*(2**24 -1)),
											from_reg_signed(0, 25, xform=lambda x: x / (2**24-1))),

	'pid2_int_ifb_gain':	(REG_LIA_INT_IFBGAIN2,	to_reg_signed(0, 25, xform=lambda x: x*(2**24 -1)),
											from_reg_signed(0, 25, xform=lambda x: x / (2**24-1))),

	'pid1_int_p_gain':	(REG_LIA_INT_PGAIN1,	to_reg_signed(0, 25, xform=lambda x: x*(2**24 -1)),
											from_reg_signed(0, 25, xform=lambda x: x / (2**24-1))),

	'pid2_int_p_gain':	(REG_LIA_INT_PGAIN2,	to_reg_signed(0, 25, xform=lambda x: x*(2**24 -1)),
											from_reg_signed(0, 25, xform=lambda x: x / (2**24-1))),

	'pid1_diff_d_gain':	(REG_LIA_DIFF_DGAIN1,	
											to_reg_signed(0, 25, xform=lambda x: x*(2**24 -1)),
											from_reg_signed(0, 25, xform=lambda x: x / (2**24-1))),

	'pid2_diff_d_gain':	(REG_LIA_DIFF_DGAIN2,	
											to_reg_signed(0, 25, xform=lambda x: x*(2**24 -1)),
											from_reg_signed(0, 25, xform=lambda x: x / (2**24-1))),

	'pid1_diff_p_gain':	(REG_LIA_DIFF_PGAIN1,	
											to_reg_signed(0, 25, xform=lambda x: x*(2**24 -1)),
											from_reg_signed(0, 25, xform=lambda x: x / (2**24-1))),

	'pid2_diff_p_gain':	(REG_LIA_DIFF_PGAIN2,	
											to_reg_signed(0, 25, xform=lambda x: x*(2**24 -1)),
											from_reg_signed(0, 25, xform=lambda x: x / (2**24-1))),

	'pid1_diff_i_gain':	(REG_LIA_DIFF_IGAIN1,	
											to_reg_signed(0, 25, xform=lambda x: x*(2**24 -1)),
											from_reg_signed(0, 25, xform=lambda x: x / (2**24-1))),

	'pid2_diff_i_gain':	(REG_LIA_DIFF_IGAIN2,	
											to_reg_signed(0, 25, xform=lambda x: x*(2**24 -1)),
											from_reg_signed(0, 25, xform=lambda x: x / (2**24-1))),

	'pid1_diff_ifb_gain':	(REG_LIA_DIFF_IFBGAIN1,	
											to_reg_signed(0, 25, xform=lambda x: x*(2**24 -1)),
											from_reg_signed(0, 25, xform=lambda x: x / (2**24-1))),

	'pid2_diff_ifb_gain':	(REG_LIA_DIFF_IFBGAIN2,	
											to_reg_signed(0, 25, xform=lambda x: x*(2**24 -1)),
											from_reg_signed(0, 25, xform=lambda x: x / (2**24-1))),

	'frequency_demod':	((REG_LIA_FREQDEMOD_H, REG_LIA_FREQDEMOD_L),	
											to_reg_unsigned(0, 48, xform=lambda x: x / _LIA_FREQSCALE),
											from_reg_unsigned(0, 48, xform=lambda x: x * _LIA_FREQSCALE)),

	'phase_demod':	((REG_LIA_PHASEDEMOD_H, REG_LIA_PHASEDEMOD_L),	
											to_reg_unsigned(0, 48, xform=lambda x: x / _LIA_PHASESCALE),
											from_reg_unsigned(0, 48, xform=lambda x: x * _LIA_PHASESCALE)),

	'decimation_bitshift':	(REG_LIA_DECBITSHIFT,	
											to_reg_unsigned(0, 4),
											from_reg_unsigned(0, 4)),

	'monitor_select0':	(REG_LIA_MONSELECT0,	
											to_reg_unsigned(0, 3),
											from_reg_unsigned(0, 3)),

	'monitor_select1':	(REG_LIA_MONSELECT1,	
											to_reg_unsigned(0, 3),
											from_reg_unsigned(0, 3)),

	'sineout_amp':	(REG_LIA_SINEOUTAMP,	
											to_reg_signed(0, 16, xform=lambda x: x / _LIA_AMPSCALE),
											from_reg_signed(0, 16, xform=lambda x: x * _LIA_AMPSCALE)),

	'sineout_offset':	(REG_LIA_SINEOUTOFF,	
											to_reg_signed(0, 16, xform=lambda x: x / _LIA_AMPSCALE),
											from_reg_signed(0, 16, xform=lambda x: x * _LIA_AMPSCALE)),
	'input_gain':	(REG_LIA_INPUT_GAIN,
											to_reg_signed(0,32, xform=lambda x: x * 2**16),
											from_reg_signed(0,32, xform=lambda x: x / 2**16)),
	}
# _instrument._attach_register_handlers(_lia_reg_hdl, LockInAmp)
