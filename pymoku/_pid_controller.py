
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


# LOCKINAMP REGISTERS
REG_PID_OUTSEL		= 65
REG_PID_TRIGMODE	= 66
REG_PID_TRIGCTL		= 67
REG_PID_TRIGLVL		= 68
REG_PID_ACTL		= 69
REG_PID_DECIMATION	= 70

REG_PID_ENABLES					= 96
# CHANNEL 0 REGISTERS
REG_PID_CH0_PIDGAIN1			= 97
REG_PID_CH0_PIDGAIN2			= 98
REG_PID_CH0_INT_IGAIN1			= 99
REG_PID_CH0_INT_IGAIN2_LSB		= 99
REG_PID_CH0_INT_IGAIN2_MSB		= 100
REG_PID_CH0_INT_IFBGAIN1_LSB	= 100
REG_PID_CH0_INT_IFBGAIN1_MSB	= 101
REG_PID_CH0_INT_IFBGAIN2		= 101
REG_PID_CH0_INT_PGAIN1			= 102
REG_PID_CH0_INT_PGAIN2_LSB		= 102
REG_PID_CH0_INT_PGAIN2_MSB		= 103
REG_PID_CH0_DIFF_DGAIN1_LSB		= 103
REG_PID_CH0_DIFF_DGAIN1_MSB		= 104
REG_PID_CH0_DIFF_DGAIN2			= 104
REG_PID_CH0_DIFF_PGAIN1			= 105
REG_PID_CH0_DIFF_PGAIN2_LSB		= 105
REG_PID_CH0_DIFF_PGAIN2_MSB		= 106
REG_PID_CH0_DIFF_IGAIN1_LSB		= 106
REG_PID_CH0_DIFF_IGAIN2_MSB		= 107
REG_PID_CH0_DIFF_IFBGAIN1		= 108
REG_PID_CH0_DIFF_IFBGAIN2		= 109
REG_PID_CH0_CH0GAIN_LSB			= 108
REG_PID_CH0_CH0GAIN_MSB			= 109
REG_PID_CH0_CH1GAIN				= 127
REG_PID_CH0_OFFSET1				= 110
REG_PID_CH0_OFFSET2				= 111
# CHANNEL 1 registers
REG_PID_CH1_PIDGAIN1			= 112
REG_PID_CH1_PIDGAIN2			= 113
REG_PID_CH1_INT_IGAIN1			= 114
REG_PID_CH1_INT_IGAIN2_LSB		= 114
REG_PID_CH1_INT_IGAIN2_MSB		= 115
REG_PID_CH1_INT_IFBGAIN1_LSB	= 115
REG_PID_CH1_INT_IFBGAIN1_MSB	= 116
REG_PID_CH1_INT_IFBGAIN2		= 117
REG_PID_CH1_INT_PGAIN1			= 117
REG_PID_CH1_INT_PGAIN2_LSB		= 118
REG_PID_CH1_INT_PGAIN2_MSB		= 118
REG_PID_CH1_DIFF_DGAIN1_LSB		= 119
REG_PID_CH1_DIFF_DGAIN1_MSB		= 119
REG_PID_CH1_DIFF_DGAIN2			= 120
REG_PID_CH1_DIFF_PGAIN1			= 120
REG_PID_CH1_DIFF_PGAIN2_LSB		= 121
REG_PID_CH1_DIFF_PGAIN2_MSB		= 121
REG_PID_CH1_DIFF_IGAIN1_LSB		= 122
REG_PID_CH1_DIFF_IGAIN2_MSB		= 122
REG_PID_CH1_DIFF_IFBGAIN1		= 123
REG_PID_CH1_DIFF_IFBGAIN2		= 124
REG_PID_CH1_CH0GAIN_LSB			= 123
REG_PID_CH1_CH0GAIN_MSB			= 124
REG_PID_CH1_OFFSET1				= 125
REG_PID_CH1_OFFSET2				= 126
REG_PID_CH1_CH1GAIN				= 127
  
REG_PID_MONSELECT0				= 96
REG_PID_MONSELECT1				= 96
# REG_PID_OUTSEL constants
PID_SOURCE_ADC		= 0
PID_SOURCE_DAC		= 1

# REG_PID_TRIGMODE constants
PID_TRIG_AUTO		= 0
PID_TRIG_NORMAL		= 1
PID_TRIG_SINGLE		= 2

# REG_PID_TRIGLVL constants
PID_TRIG_CH1		= 0
PID_TRIG_CH2		= 1
PID_TRIG_DA1		= 2
PID_TRIG_DA2		= 3

PID_EDGE_RISING		= 0
PID_EDGE_FALLING	= 1
PID_EDGE_BOTH		= 2

PID_ROLL			= _instrument.ROLL
PID_SWEEP			= _instrument.SWEEP
PID_FULL_FRAME		= _instrument.FULL_FRAME

# SIGNAL PRECISION MODES
PID_HIGH_PRECISION	= 1
PID_HIGH_RANGE		= 0

_PID_LB_ROUND		= 0
_PID_LB_CLIP		= 1

_PID_AIN_DDS		= 0
_PID_AIN_DECI		= 1

_PID_ADC_SMPS		= _instrument.ADC_SMP_RATE
_PID_BUFLEN			= _instrument.CHN_BUFLEN
_PID_SCREEN_WIDTH	= 1024
_PID_FPS			= 10



### Every constant that starts with PID_ will become an attribute of pymoku.instruments ###

PID_MONITOR_I		= 0
PID_MONITOR_Q		= 1
PID_MONITOR_PID		= 2
PID_MONITOR_INPUT	= 3

_PID_CONTROL_FS 	= 25e6
_PID_SINE_FS		= 1e9
_PID_COEFF_WIDTH	= 25
_PID_FREQSCALE		= float(1e9) / 2**48
_PID_PHASESCALE		= 1.0 / 2**48
_PID_AMPSCALE		= 1.0 / (2**15 - 1)




class PIDController(_frame_instrument.FrameBasedInstrument):
	""" PIDController instrument object. This should be instantiated and attached to a :any:`Moku` instance.

	.. automethod:: pymoku.instruments.PIDController.__init__

	.. attribute:: hwver

		Hardware Version

	.. attribute:: hwserial

		Hardware Serial Number

	.. attribute:: framerate
		:annotation: = 10

		Frame Rate, range 1 - 30.

	.. attribute:: type
		:annotation: = "PIDController"

		Name of this instrument.

	"""
	def __init__(self):
		"""Create a new Lock-In-Amplifier instrument, ready to be attached to a Moku."""
	

		super(PIDController, self).__init__()
		self._register_accessors(_PID_reg_hdl)

		self.id = 5
		self.calibration = None

		self.scales = {}
		self.decimation_rate = 1
		self.set_frame_class(VoltsFrame, scales=self.scales)

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

		if self.ain_mode == _PID_AIN_DECI:
			g1 /= self._deci_gain()
			g2 /= self._deci_gain()

		return (g1, g2)	

	def commit(self):
		super(PIDController, self).commit()
		self.scales[self._stateid] = self._calculate_scales()

	def set_defaults(self):
		""" Reset the lockinamp to sane defaults. """
		super(PIDController, self).set_defaults()
		#TODO this should reset ALL registers
		self.calibration = None

		self.set_xmode(PID_FULL_FRAME)
		self.set_timebase(-0.25, 0.25)
		self.set_precision_mode(False)
		self.set_frontend(0, False, True, False)
		self.set_frontend(1, False, True, False)
		self.framerate = _PID_FPS
		self.frame_length = _PID_SCREEN_WIDTH
		self.trig_mode = PID_TRIG_AUTO
		self.set_trigger(PID_TRIG_CH1, PID_EDGE_RISING, 0)

		self.Ch0_Ch0_gain = 1.0
		self.Ch0_Ch1_gain = 0.0

		self.Ch1_Ch0_gain = 100.0
		self.Ch1_Ch1_gain = 0.0

		self.pid1_int_dc_pole = 0
		self.pid2_int_dc_pole = 0

		self.Ch0_pid1_bypass = 0
		self.Ch0_pid2_bypass = 1
		self.Ch1_pid1_bypass = 0
		self.Ch1_pid2_bypass = 1

		self.Ch0_pid1_pidgain = 1.0
		self.Ch0_pid2_pidgain = 1.0
		self.Ch0_pid1_int_i_gain = 0.00001
		self.Ch0_pid2_int_i_gain = 0.00
		self.Ch0_pid1_int_ifb_gain = 0.99999
		self.Ch0_pid2_int_ifb_gain = 0.0
		self.Ch0_pid1_int_p_gain = 0.0
		self.Ch0_pid2_int_p_gain = 0.0
		self.Ch0_pid1_diff_d_gain = 1.0
		self.Ch0_pid2_diff_d_gain = 0.0
		self.Ch0_pid1_diff_p_gain = 0.0
		self.Ch0_pid2_diff_p_gain = 0.0
		self.Ch0_pid1_diff_i_gain = 0.0
		self.Ch0_pid2_diff_i_gain = 0.0
		self.Ch0_pid1_diff_ifb_gain = 0.999
		self.Ch0_pid2_diff_ifb_gain = 0.0
		self.Ch0_slope = 1

		self.Ch1_pid1_pidgain = 1.0
		self.Ch1_pid2_pidgain = 1.0
		self.Ch1_pid1_int_i_gain = 1.0
		self.Ch1_pid2_int_i_gain = 0
		self.Ch1_pid1_int_ifb_gain = 1.0
		self.Ch1_pid2_int_ifb_gain = 1.0
		self.Ch1_pid1_int_p_gain = 0.0
		self.Ch1_pid2_int_p_gain = 0.0
		self.Ch1_pid1_diff_d_gain = 0.0
		self.Ch1_pid2_diff_d_gain = 0.0
		self.Ch1_pid1_diff_p_gain = 1.0
		self.Ch1_pid2_diff_p_gain = 1.0
		self.Ch1_pid1_diff_i_gain = 0.0
		self.Ch1_pid2_diff_i_gain = 0.0
		self.Ch1_pid1_diff_ifb_gain = 0.99
		self.Ch1_pid2_diff_ifb_gain = 0.99
		self.Ch1_slope = 1

		self.Ch0_pid1_out_offset = 0
		self.Ch1_pid1_out_offset = 0
		#self.set_integrator_parameters(0, 0, 100, 1)
		# self.set_pid_offset(0,0)
		# self.set_pid_offset(0,1)
		# self.monitor_select0 = 2
		# self.monitor_select1 = 2
		# self.trigger_level = 0
		
	
		# self.pid1_in_offset  = 0
		# self.pid1_out_offset = 0
		# self.pid2_in_offset = 0
		# self.pid2_out_offset = 0



	def set_integrator_parameters(self, Channel, integrator_gain_dB, max_gain_dB, Order):
		
		max_gain = 10**(max_gain_dB / 20.0)
		gain = 10**(integrator_gain_dB / 20.0)
		DSPCoeff = 1 - gain/max_gain

		if Channel == 0 :
			self.Ch0_pid1_int_ifb_gain = DSPCoeff
			self.Ch0_pid2_int_ifb_gain = DSPCoeff

			self.Ch0_pid1_int_i_gain = 1.0 - DSPCoeff
			self.Ch0_pid2_int_i_gain = 1.0 - DSPCoeff
		
			if Order == 1:
				self.Ch0_pid2_bypass = 1
				self.Ch0_slope = 1
			elif Order == 2:
				self.Ch0_pid2_bypass = 0
				self.Ch0_slope = 2
			else:
				self.Ch0_pid1_bypass = 1
				self.Ch0_pid2_bypass = 1
		elif Channel == 1 :
			self.Ch1_pid1_int_ifb_gain = DSPCoeff
			self.Ch1_pid2_int_ifb_gain = DSPCoeff

			self.Ch1_pid1_int_i_gain = 1.0 - DSPCoeff
			self.Ch1_pid2_int_i_gain = 1.0 - DSPCoeff
		
			if Order == 1:
				self.Ch1_pid2_bypass = 1
				self.Ch1_slope = 1
			elif Order == 2:
				self.Ch1_pid2_bypass = 0
				self.Ch1_slope = 2
			else:
				self.Ch1_pid1_bypass = 1
				self.Ch1_pid2_bypass = 1
		else :
			raise InvalidOperationException("Channel not set : defaulted to Channel 0")
			self.Ch0_pid1_int_ifb_gain = DSPCoeff
			self.Ch0_pid2_int_ifb_gain = DSPCoeff

			self.Ch0_pid1_int_i_gain = 1.0 - DSPCoeff
			self.Ch0_pid2_int_i_gain = 1.0 - DSPCoeff
		
			if Order == 1:
				self.Ch0_pid2_bypass = 1
				self.Ch0_slope = 1
			elif Order == 2:
				self.Ch0_pid2_bypass = 0
				self.Ch0_slope = 2
			else:
				self.Ch0_pid1_bypass = 1
				self.Ch0_pid2_bypass = 1

	# def set_differentiator_parameteters(self, Channel, integrator_gain_dB, max_gain_dB, Order):

	def _set_gain(self, Gain_dB):

		ImpedenceGain = 1 if (self.relays_ch1 & 2) == 2 else 2
		AttenGain = 1 if (self.relays_ch1 & 4) == 4 else 10
		
		gain_factor = ImpedenceGain * AttenGain * (10**(Gain_dB / 20.0)) * self._get_dac_calibration()[0] / self._get_adc_calibration()[0]
		log.debug("AttenGain, %f, GainFactor, %f", AttenGain, gain_factor)

		if self.signal_mode == PID_HIGH_PRECISION:
			if self.slope == 1:
				self.input_gain = gain_factor
				self.pid1_pidgain = self.pid2_pidgain = 1.0
			else :
				self.input_gain = self.pid1_pidgain =  math.sqrt(gain_factor)
				self.pid2_pidgain = 1.0
		elif self.signal_mode == PID_HIGH_RANGE:
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
			self.signal_mode = PID_HIGH_RANGE
			raise InvalidOperationException("Signal Mode not set : defaulted to HIGH RANGE MODE")

	def set_pid_offset(self, offset, Channel):
		if Channel == 0 :
			if self.Ch0_slope == 1:
				self.pid1_out_offset = offset * self._get_dac_calibration()[0]
				self.pid2_out_offset = 0
			elif self.Ch0_slope == 2:
				self.pid1_out_offset = 0
				self.pid2_out_offset = offset * self._get_dac_calibratioin()[0]
			else :
				self.Ch0_slope == 1
				self.pid1_out_offset = offset * self._get_dac_calibration()[0]
				self.pid2_out_offset = 0
				raise InvalidOperationException("PID slope not set : defaulted to slope = %s" % self.slope)
		elif Channel == 1:
			if self.Ch1_slope == 1:
				self.pid1_out_offset = offset * self._get_dac_calibration()[0]
				self.pid2_out_offset = 0
			elif self.Ch1_slope == 2:
				self.pid1_out_offset = 0
				self.pid2_out_offset = offset * self._get_dac_calibratioin()[0]
			else :
				self.Ch1_slope == 1
				self.pid1_out_offset = offset * self._get_dac_calibration()[0]
				self.pid2_out_offset = 0
				raise InvalidOperationException("PID slope not set : defaulted to slope = %s" % self.slope)

	def set_lo_output_amp(self,amplitude):
		# converts amplitude (V) into the bits required for the register
		self.sineout_amp = amplitude * self._get_dac_calibration()[1]

	def set_lo_offset(self, offset):
		# converts the offset in volts to the bits required for the offset register
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
		return math.ceil(_PID_ADC_SMPS * ts / _PID_BUFLEN)

	def _buffer_offset(self, t1, t2, decimation):
		# Based on mercury_ipad/LISettings::OSCalculateOptimalBufferOffset
		# TODO: Roll mode

		buffer_smps = _PID_ADC_SMPS / decimation
		offset_secs = t1
		offset = round(min(max(math.ceil(offset_secs * buffer_smps / 4.0), -2**28), 2**12))

		return offset

	def _render_downsample(self, t1, t2, decimation):
		# Based on mercury_ipad/LISettings::OSCalculateRenderDownsamplingForDecimation
		buffer_smps = _PID_ADC_SMPS / decimation
		screen_smps = min(_PID_SCREEN_WIDTH / abs(t1 - t2), _PID_ADC_SMPS)

		return round(min(max(buffer_smps / screen_smps, 1.0), 16.0))

	def _render_offset(self, t1, t2, decimation, buffer_offset, render_decimation):
		# Based on mercury_ipad/LISettings::OSCalculateFrameOffsetForDecimation
		buffer_smps = _PID_ADC_SMPS / decimation
		trig_in_buf = 4 * buffer_offset # TODO: Roll Mode
		time_buff_start = -trig_in_buf / buffer_smps
		time_buff_end = time_buff_start + (_PID_BUFLEN - 1) / buffer_smps
		time_screen_centre = abs(t1 - t2) / 2
		screen_span = render_decimation / buffer_smps * _PID_SCREEN_WIDTH

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
		samplerate = _PID_ADC_SMPS / self.decimation_rate
		self.timestep = 1 / samplerate

		if self.ain_mode == _PID_AIN_DECI:
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
		self.decimation_rate = _PID_ADC_SMPS / samplerate

	def get_samplerate(self):
		return _PID_ADC_SMPS / self.decimation_rate

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

	def set_trigger(self, source, edge, level, hysteresis=0, hf_reject=False, mode=PID_TRIG_AUTO):
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

	def attach_moku(self, moku):
		super(PIDController, self).attach_moku(moku)

		try:
			self.calibration = dict(self._moku._get_property_section("calibration"))
		except:
			log.warning("Can't read calibration values.")

_PID_reg_hdl = {
	'source_ch1':		(REG_PID_OUTSEL,	to_reg_unsigned(0, 1, allow_set=[PID_SOURCE_ADC, PID_SOURCE_DAC]),
											from_reg_unsigned(0, 1)),

	'source_ch2':		(REG_PID_OUTSEL,	to_reg_unsigned(1, 1, allow_set=[PID_SOURCE_ADC, PID_SOURCE_DAC]),
											from_reg_unsigned(1, 1)),

	'trig_mode':		(REG_PID_TRIGMODE,	to_reg_unsigned(0, 2, allow_set=[PID_TRIG_AUTO, PID_TRIG_NORMAL, PID_TRIG_SINGLE]),
											from_reg_unsigned(0, 2)),

	'trig_edge':		(REG_PID_TRIGCTL,	to_reg_unsigned(0, 2, allow_set=[PID_EDGE_RISING, PID_EDGE_FALLING, PID_EDGE_BOTH]),
											from_reg_unsigned(0, 2)),

	'trig_ch':			(REG_PID_TRIGCTL,	to_reg_unsigned(4, 6, allow_set=[PID_TRIG_CH1, PID_TRIG_CH2, PID_TRIG_DA1, PID_TRIG_DA2]),
											from_reg_unsigned(4, 6)),

	'hf_reject':		(REG_PID_TRIGCTL,	to_reg_bool(12),			from_reg_bool(12)),
	'hysteresis':		(REG_PID_TRIGCTL,	to_reg_unsigned(16, 16),	from_reg_unsigned(16, 16)),
	'trigger_level':	(REG_PID_TRIGLVL,	to_reg_signed(0, 32),		to_reg_signed(0, 32)),

	'loopback_mode_ch1':	(REG_PID_ACTL,	to_reg_unsigned(0, 1, allow_set=[_PID_LB_CLIP, _PID_LB_ROUND]),
											from_reg_unsigned(0, 1)),
	'loopback_mode_ch2':	(REG_PID_ACTL,	to_reg_unsigned(1, 1, allow_set=[_PID_LB_CLIP, _PID_LB_ROUND]),
											from_reg_unsigned(1, 1)),

	'ain_mode':			(REG_PID_ACTL,		to_reg_unsigned(2, 16, allow_set=[_PID_AIN_DDS, _PID_AIN_DECI]),
											from_reg_unsigned(2, 16)),

	'decimation_rate':	(REG_PID_DECIMATION,to_reg_unsigned(0, 32),	
											from_reg_unsigned(0, 32)),

	'Ch0_pid1_bypass':	(REG_PID_ENABLES,	to_reg_bool(0),
											from_reg_bool(0)),

	'Ch0_pid2_bypass':	(REG_PID_ENABLES,	to_reg_bool(1),
											from_reg_bool(1)),

	'Ch0_Ch0_gain' :	((REG_PID_CH0_CH0GAIN_MSB, REG_PID_CH0_CH0GAIN_LSB), 
											to_reg_signed(24,16, xform=lambda x : x * (2**7-1)),
											from_reg_signed(24,16, xform=lambda x : x / (2**7 -1))),

	'Ch0_Ch1_gain' :	(REG_PID_CH0_CH1GAIN, 
											to_reg_signed(0,16, xform=lambda x : x * (2**7-1)),
											from_reg_signed(0,16, xform=lambda x : x / (2**7 -1))),

	'Ch0_pid1_int_dc_pole':	(REG_PID_ENABLES,	to_reg_bool(2),
											from_reg_bool(2)),

	'Ch0_pid2_int_dc_pole':	(REG_PID_ENABLES,	to_reg_bool(3),
											from_reg_bool(3)),

	'Ch0_pid1_in_offset':	(REG_PID_CH0_OFFSET1,to_reg_signed(0, 16),
											from_reg_signed(0, 16)),

	'Ch0_pid2_in_offset':	(REG_PID_CH0_OFFSET2,to_reg_signed(0, 16),
											from_reg_signed(0, 16)),

	'Ch0_pid1_out_offset':	(REG_PID_CH0_OFFSET1,to_reg_signed(16, 16),
											from_reg_signed(16, 16)),	

	'Ch0_pid2_out_offset':	(REG_PID_CH0_OFFSET2,to_reg_signed(16, 16),
											from_reg_signed(16, 16)),

	'Ch0_pid1_pidgain':		(REG_PID_CH0_PIDGAIN1,	to_reg_signed(0, 32, xform=lambda x : x * 2**16),
											from_reg_signed(0, 32, xform=lambda x: x / 2**16)),

	'Ch0_pid2_pidgain':		(REG_PID_CH0_PIDGAIN2,	to_reg_signed(0, 32, xform=lambda x : x * 2**16),
											from_reg_signed(0, 32, xform=lambda x: x / 2**16)),

	'Ch0_pid1_int_i_gain':	(REG_PID_CH0_INT_IGAIN1,	to_reg_unsigned(0, 24, xform=lambda x: x*(2**24 -1)),
											from_reg_unsigned(0, 24, xform=lambda x: x / (2**24-1))),

	'Ch0_pid2_int_i_gain':	((REG_PID_CH0_INT_IGAIN2_MSB, REG_PID_CH0_INT_IGAIN2_LSB),	to_reg_unsigned(24, 24, xform=lambda x: (x*(2**24 -1))),
											from_reg_unsigned(24, 24, xform=lambda x: x / (2**24-1))),

	'Ch0_pid1_int_ifb_gain':	((REG_PID_CH0_INT_IFBGAIN1_MSB, REG_PID_CH0_INT_IFBGAIN1_LSB),	to_reg_unsigned(16, 24, xform=lambda x: (x*(2**24 -1))),
											from_reg_unsigned(16, 24, xform=lambda x: x / (2**24-1))),

	'Ch0_pid2_int_ifb_gain':	(REG_PID_CH0_INT_IFBGAIN2,	to_reg_unsigned(8, 24, xform=lambda x: x*(2**24 -1)),
											from_reg_unsigned(8, 24, xform=lambda x: x / (2**24-1))),

	'Ch0_pid1_int_p_gain':	(REG_PID_CH0_INT_PGAIN1,	to_reg_unsigned(0, 24, xform=lambda x: (x*(2**24 -1))),
											from_reg_unsigned(0, 24, xform=lambda x: x / (2**24-1))),

	'Ch0_pid2_int_p_gain':	((REG_PID_CH0_INT_PGAIN2_MSB, REG_PID_CH0_INT_PGAIN2_LSB),	to_reg_unsigned(24, 24, xform=lambda x: x*(2**24 -1)),
											from_reg_unsigned(24, 24, xform=lambda x: x / (2**24-1))),

	'Ch0_pid1_diff_d_gain':	((REG_PID_CH0_DIFF_DGAIN1_MSB, REG_PID_CH0_DIFF_DGAIN1_LSB),	
											to_reg_unsigned(16, 24, xform=lambda x: (x*(2**24 -1))),
											from_reg_unsigned(16, 24, xform=lambda x: x / (2**24-1))),

	'Ch0_pid2_diff_d_gain':	(REG_PID_CH0_DIFF_DGAIN2,	
											to_reg_unsigned(8, 24, xform=lambda x: x*(2**24 -1)),
											from_reg_unsigned(8, 24, xform=lambda x: x / (2**24-1))),

	'Ch0_pid1_diff_p_gain':	(REG_PID_CH0_DIFF_PGAIN1,	
											to_reg_unsigned(0, 24, xform=lambda x: x*(2**24 -1)),
											from_reg_unsigned(0, 24, xform=lambda x: x / (2**24-1))),

	'Ch0_pid2_diff_p_gain':	((REG_PID_CH0_DIFF_PGAIN2_MSB, REG_PID_CH0_DIFF_PGAIN2_LSB),	
											to_reg_unsigned(24, 24, xform=lambda x: (x*(2**24 -1))),
											from_reg_unsigned(24, 24, xform=lambda x: x / (2**24-1))),

	'Ch0_pid1_diff_i_gain':	((REG_PID_CH0_DIFF_IGAIN2_MSB, REG_PID_CH0_DIFF_IGAIN1_LSB),	
											to_reg_unsigned(16, 24, xform=lambda x: (x*(2**24 -1))),
											from_reg_unsigned(16, 24, xform=lambda x: x / (2**24-1))),

	'Ch0_pid1_diff_ifb_gain':	(REG_PID_CH0_DIFF_IFBGAIN1,	
											to_reg_unsigned(0, 24, xform=lambda x: x*(2**24 -1)),
											from_reg_unsigned(0, 24, xform=lambda x: x / (2**24-1))),

	'Ch0_pid2_diff_ifb_gain':	(REG_PID_CH0_DIFF_IFBGAIN2,	
											to_reg_unsigned(7, 24, xform=lambda x: x*(2**24 -1)),
											from_reg_unsigned(7, 24, xform=lambda x: x / (2**24-1))),

	'Ch1_pid1_bypass':	(REG_PID_ENABLES,		to_reg_bool(4),
											from_reg_bool(4)),

	'Ch1_pid2_bypass':	(REG_PID_ENABLES,		to_reg_bool(5),
											from_reg_bool(5)),

	'Ch1_pid1_int_dc_pole':	(REG_PID_ENABLES,	to_reg_bool(6),
											from_reg_bool(6)),

	'Ch1_pid2_int_dc_pole':	(REG_PID_ENABLES,	to_reg_bool(7),
											from_reg_bool(7)),

	'Ch1_Ch0_gain' :	((REG_PID_CH1_CH0GAIN_MSB, REG_PID_CH0_CH0GAIN_LSB), 
											to_reg_signed(24,16, xform=lambda x : x * (2**7 -1)),
											from_reg_signed(24,16, xform=lambda x : x / (2**7 -1))),

	'Ch1_Ch1_gain' :	(REG_PID_CH1_CH1GAIN, 
											to_reg_signed(0,16, xform=lambda x : x * (2**7 -1)),
											from_reg_signed(0,16, xform=lambda x : x / (2**7 -1))),

	'Ch1_pid1_in_offset':	(REG_PID_CH1_OFFSET1,to_reg_signed(0, 16),
											from_reg_signed(0, 16)),

	'Ch1_pid2_in_offset':	(REG_PID_CH1_OFFSET2,to_reg_signed(0, 16),
											from_reg_signed(0, 16)),

	'Ch1_pid1_out_offset':	(REG_PID_CH1_OFFSET1,to_reg_signed(16, 16),
											from_reg_signed(16, 16)),	

	'Ch1_pid2_out_offset':	(REG_PID_CH1_OFFSET2,to_reg_signed(16, 16),
											from_reg_signed(16, 16)),

	'Ch1_pid1_pidgain':		(REG_PID_CH1_PIDGAIN1,	to_reg_signed(0, 32, xform=lambda x : x * 2**16),
											from_reg_signed(0, 32, xform=lambda x: x / 2**16)),

	'Ch1_pid2_pidgain':		(REG_PID_CH1_PIDGAIN2,	to_reg_signed(0, 32, xform=lambda x : x * 2**16),
											from_reg_signed(0, 32, xform=lambda x: x / 2**16)),

	'Ch1_pid1_int_i_gain':	(REG_PID_CH1_INT_IGAIN1,	to_reg_unsigned(0, 24, xform=lambda x: x*(2**24 -1)),
											from_reg_unsigned(0, 24, xform=lambda x: x / (2**24-1))),

	'Ch1_pid2_int_i_gain':	((REG_PID_CH1_INT_IGAIN2_MSB, REG_PID_CH1_INT_IGAIN2_LSB),	to_reg_unsigned(24, 24, xform=lambda x: (x*(2**24 -1))),
											from_reg_unsigned(24, 24, xform=lambda x: x / (2**24-1))),

	'Ch1_pid1_int_ifb_gain':	((REG_PID_CH1_INT_IFBGAIN1_MSB, REG_PID_CH1_INT_IFBGAIN1_LSB),	to_reg_unsigned(16, 24, xform=lambda x: (x*(2**24 -1))),
											from_reg_unsigned(16, 24, xform=lambda x: x / (2**24-1))),

	'Ch1_pid2_int_ifb_gain':	(REG_PID_CH1_INT_IFBGAIN2,	to_reg_unsigned(8, 24, xform=lambda x: x*(2**24 -1)),
											from_reg_unsigned(8, 24, xform=lambda x: x / (2**24-1))),

	'Ch1_pid1_int_p_gain':	(REG_PID_CH1_INT_PGAIN1,	to_reg_unsigned(0, 24, xform=lambda x: (x*(2**24 -1))),
											from_reg_unsigned(0, 24, xform=lambda x: x / (2**24-1))),

	'Ch1_pid2_int_p_gain':	((REG_PID_CH1_INT_PGAIN2_MSB, REG_PID_CH1_INT_PGAIN2_LSB),	to_reg_unsigned(24, 24, xform=lambda x: x*(2**24 -1)),
											from_reg_unsigned(24, 24, xform=lambda x: x / (2**24-1))),

	'Ch1_pid1_diff_d_gain':	((REG_PID_CH1_DIFF_DGAIN1_MSB, REG_PID_CH1_DIFF_DGAIN1_LSB),	
											to_reg_unsigned(16, 24, xform=lambda x: (x*(2**24 -1))),
											from_reg_unsigned(16, 24, xform=lambda x: x / (2**24-1))),

	'Ch1_pid2_diff_d_gain':	(REG_PID_CH1_DIFF_DGAIN2,	
											to_reg_unsigned(8, 24, xform=lambda x: x*(2**24 -1)),
											from_reg_unsigned(8, 24, xform=lambda x: x / (2**24-1))),

	'Ch1_pid1_diff_p_gain':	(REG_PID_CH1_DIFF_PGAIN1,	
											to_reg_unsigned(0, 24, xform=lambda x: x*(2**24 -1)),
											from_reg_unsigned(0, 24, xform=lambda x: x / (2**24-1))),

	'Ch1_pid2_diff_p_gain':	((REG_PID_CH1_DIFF_PGAIN2_MSB, REG_PID_CH1_DIFF_PGAIN2_LSB),	
											to_reg_unsigned(24, 24, xform=lambda x: (x*(2**24 -1))),
											from_reg_unsigned(24, 24, xform=lambda x: x / (2**24-1))),

	'Ch1_pid1_diff_i_gain':	((REG_PID_CH1_DIFF_IGAIN2_MSB, REG_PID_CH1_DIFF_IGAIN1_LSB),	
											to_reg_unsigned(16, 24, xform=lambda x: (x*(2**24 -1))),
											from_reg_unsigned(16, 24, xform=lambda x: x / (2**24-1))),

	'Ch1_pid1_diff_ifb_gain':	(REG_PID_CH1_DIFF_IFBGAIN1,	
											to_reg_unsigned(0, 24, xform=lambda x: x*(2**24 -1)),
											from_reg_unsigned(0, 24, xform=lambda x: x / (2**24-1))),

	'Ch1_pid2_diff_ifb_gain':	(REG_PID_CH1_DIFF_IFBGAIN2,	
											to_reg_unsigned(7, 24, xform=lambda x: x*(2**24 -1)),
											from_reg_unsigned(7, 24, xform=lambda x: x / (2**24-1))),
	'monitor_select0':	(REG_PID_MONSELECT0,	
											to_reg_unsigned(18, 3),
											from_reg_unsigned(18, 3)),

	'monitor_select1':	(REG_PID_MONSELECT1,	
											to_reg_unsigned(21, 3),
											from_reg_unsigned(21, 3)),
	}
# _instrument._attach_register_handlers(_lia_reg_hdl, LockInAmp)
