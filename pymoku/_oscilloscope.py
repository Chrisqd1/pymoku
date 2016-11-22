
import math
import logging

from ._instrument import *
from . import _frame_instrument
from . import _siggen

log = logging.getLogger(__name__)

REG_OSC_OUTSEL		= 65
REG_OSC_TRIGMODE	= 66
REG_OSC_TRIGCTL		= 67
REG_OSC_TRIGLVL		= 68
REG_OSC_ACTL		= 69
REG_OSC_DECIMATION	= 70

### Every constant that starts with OSC_ will become an attribute of pymoku.instruments ###

# REG_OSC_OUTSEL constants
OSC_SOURCE_ADC		= 0
OSC_SOURCE_DAC		= 1

# REG_OSC_TRIGMODE constants
OSC_TRIG_AUTO		= 0
OSC_TRIG_NORMAL		= 1
OSC_TRIG_SINGLE		= 2

# REG_OSC_TRIGLVL constants
OSC_TRIG_CH1		= 0
OSC_TRIG_CH2		= 1
OSC_TRIG_DA1		= 2
OSC_TRIG_DA2		= 3

OSC_EDGE_RISING		= 0
OSC_EDGE_FALLING	= 1
OSC_EDGE_BOTH		= 2

# Re-export the top level attributes so they'll be picked up by pymoku.instruments, we
# do actually want to give people access to these constants directly for Oscilloscope
OSC_ROLL			= ROLL
OSC_SWEEP			= SWEEP
OSC_FULL_FRAME		= FULL_FRAME

_OSC_LB_ROUND		= 0
_OSC_LB_CLIP		= 1

_OSC_AIN_DDS		= 0
_OSC_AIN_DECI		= 1

_OSC_ADC_SMPS		= ADC_SMP_RATE
_OSC_BUFLEN			= CHN_BUFLEN
_OSC_SCREEN_WIDTH	= 1024
_OSC_FPS			= 10

class VoltsFrame(_frame_instrument.DataFrame):
	"""
	Object representing a frame of data in units of Volts. This is the native output format of
	the :any:`Oscilloscope` instrument and similar.

	This object should not be instantiated directly, but will be returned by a supporting *get_frame*
	implementation.

	.. autoinstanceattribute:: pymoku._frame_instrument.VoltsFrame.ch1
		:annotation: = [CH1_DATA]

	.. autoinstanceattribute:: pymoku._frame_instrument.VoltsFrame.ch2
		:annotation: = [CH2_DATA]

	.. autoinstanceattribute:: pymoku._frame_instrument.VoltsFrame.frameid
		:annotation: = n

	.. autoinstanceattribute:: pymoku._frame_instrument.VoltsFrame.waveformid
		:annotation: = n
	"""
	def __init__(self, scales):
		super(VoltsFrame, self).__init__()

		#: Channel 1 data array in units of Volts. Present whether or not the channel is enabled, but the
		#: contents are undefined in the latter case.
		self.ch1 = []

		#: Channel 2 data array in units of Volts.
		self.ch2 = []

		self.scales = scales

	def __json__(self):
		return { 'ch1': self.ch1, 'ch2' : self.ch2 }

	def process_complete(self):
		if self.stateid not in self.scales:
			log.error("Can't render voltage frame, haven't saved calibration data for state %d", self.stateid)
			return

		scales = self.scales[self.stateid]
		g1 = scales['g1']
		g2 = scales['g2']
		d1 = scales['d1']
		d2 = scales['d2']
		s1 = scales['s1']
		s2 = scales['s2']
		l1 = scales['l1']
		l2 = scales['l2']
		t1 = scales['t1']
		t2 = scales['t2']

		def _compute_scaling_factor(adc,dac,src,lmode):
			# Change scaling factor depending on the source type
			if (src == OSC_SOURCE_ADC):
				scale = adc
			elif (src == OSC_SOURCE_DAC):
				if(lmode == _OSC_LB_CLIP):
					scale = dac 
				else: # Rounding mode
					scale = dac * 16
			else:
				log.error("Invalid source type on channel.")
				return
			return scale

		scale1 = _compute_scaling_factor(g1,d1,s1,l1)
		scale2 = _compute_scaling_factor(g2,d2,s2,l2)

		try:
			smpls = int(len(self.raw1) / 4)
			dat = struct.unpack('<' + 'i' * smpls, self.raw1)
			dat = [ x if x != -0x80000000 else None for x in dat ]

			self.ch1_bits = [ float(x) if x is not None else None for x in dat[:1024] ]
			self.ch1 = [ x * scale1 if x is not None else None for x in self.ch1_bits]

			smpls = int(len(self.raw2) / 4)
			dat = struct.unpack('<' + 'i' * smpls, self.raw2)
			dat = [ x if x != -0x80000000 else None for x in dat ]

			self.ch2_bits = [ float(x) if x is not None else None for x in dat[:1024] ]
			self.ch2 = [ x * scale2 if x is not None else None for x in self.ch2_bits]
		except (IndexError, TypeError, struct.error):
			# If the data is bollocksed, force a reinitialisation on next packet
			log.exception("Oscilloscope packet")
			self.frameid = None
			self.complete = False

		return True


	'''
		Plotting helper functions
	'''
	def _get_timeScale(self, tspan):
		# Returns a scaling factor and units for time 'T'
		if(tspan <  1e-6):
			scale_str = 'ns'
			scale_const = 1e9
		elif (tspan < 1e-3):
			scale_str = 'us'
			scale_const = 1e6
		elif (tspan < 1):
			scale_str = 'ms'
			scale_const = 1e3
		else:
			scale_str = 's'
			scale_const = 1.0

		return [scale_str,scale_const]

	def _get_xaxis_fmt(self,x,pos):
		# This function returns a format string for the x-axis ticks and x-coordinates along the time scale
		# Use this to set an x-axis format during plotting of Oscilloscope frames

		if self.stateid not in self.scales:
			log.error("Can't get x-axis format, haven't saved calibration data for state %d", self.stateid)
			return

		scales = self.scales[self.stateid]
		t1 = scales['t1']
		t2 = scales['t2']
		ts = abs(t2 - t1) / _OSC_SCREEN_WIDTH
		tscale_str, tscale_const = self._get_timeScale(abs(t2-t1))

		return {'xaxis': '%.1f %s' % ((t1 + x*ts)*tscale_const, tscale_str), 'xcoord': '%.3f %s' % ((t1 + x*ts)*tscale_const, tscale_str)}

	def get_xaxis_fmt(self, x, pos):
		return self._get_xaxis_fmt(x,pos)['xaxis']

	def get_xcoord_fmt(self, x):
		return self._get_xaxis_fmt(x,None)['xcoord']

	def _get_yaxis_fmt(self,y,pos):
		return {'yaxis': '%.1f %s' % (y,'V'), 'ycoord': '%.3f %s' % (y,'V')}

	def get_yaxis_fmt(self, y, pos):
		return self._get_yaxis_fmt(y,pos)['yaxis']

	def get_ycoord_fmt(self, y):
		return self._get_yaxis_fmt(y,None)['ycoord']


class Oscilloscope(_frame_instrument.FrameBasedInstrument, _siggen.SignalGenerator):
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
		"""Create a new Oscilloscope instrument, ready to be attached to a Moku."""
		super(Oscilloscope, self).__init__()
		self._register_accessors(_osc_reg_handlers)

		self.id = 1
		self.type = "oscilloscope"
		self.calibration = None

		self.logname = "MokuDataloggerData"
		self.binstr = "<s32"
		self.procstr = ["*C","*C"]
		self.timestep = 1

		# NOTE: Register mapped properties will be overwritten in sync registers call
		# on attach_instrument(). No point setting them here.

		self.scales = {}

		self.set_frame_class(VoltsFrame, scales=self.scales)

		# Define any (non- register-mapped) properties that are used when committing
		# as a commit is called when the instrument is set running
		self.trig_volts = 0

	def _calculate_decimation(self, tspan):

		# Calculate time the buffer should contain
		# Want one frame to be approximately 1/3 of a buffer (RD ~ 5)
		# or the full buffer if it would take longer than 100ms

		# TODO: Put some limits on what the span/decimation can be
		buffer_span = float(tspan) 

		return math.ceil(ADC_SMP_RATE * buffer_span / _OSC_BUFLEN)


	def _calculate_render_downsample(self, t1, t2, decimation):
		# Calculate how much to render downsample
		tspan = float(t2) - float(t1)
		buffer_smp_rate = ADC_SMP_RATE/float(decimation)
		buffer_time_span = _OSC_BUFLEN/buffer_smp_rate

		def _cubic_int_to_scale(integer):
			# Integer to cubic scaling ratio (see Wiki)
			return float(integer/(2**7)) + 1

		# Enforce a maximum ADC sampling rate
		screen_smp_rate = min(_OSC_SCREEN_WIDTH/tspan, ADC_SMP_RATE)
		# Clamp the render downsampling ratio between 1.0 and ~16.0
		render_downsample = min(max(buffer_smp_rate/screen_smp_rate, 1.0), _cubic_int_to_scale(0x077E))
		return render_downsample

	def _calculate_buffer_offset(self, t1, decimation):
		# Calculate the number of pretrigger samples and offset it by an additional (CubicRatio) samples
		buffer_smp_rate = ADC_SMP_RATE/decimation
		buffer_offset_secs = -1.0 * t1
		buffer_offset = math.ceil(min(max(math.ceil(buffer_offset_secs * buffer_smp_rate / 4.0), -2**28), (2**12)-1))

		# Apply a correction in pretrigger because of the way cubic interpolation occurs when rendering
		return buffer_offset

	def _calculate_render_offset(self, t1, decimation):
		# TODO: Render offset should be unique to buffer offset
		# 		For now they are the same thing.
		buffer_offset = self._calculate_buffer_offset(t1, decimation)

		return buffer_offset * 4.0

	def _calculate_frame_start_time(self, decimation, render_decimation, frame_offset):
		return (render_decimation - frame_offset) * decimation/ADC_SMP_RATE

	def _calculate_frame_timestep(self, decimation, render_decimation):
		return decimation*render_decimation/ADC_SMP_RATE

	def _deci_gain(self):
		if self.decimation_rate == 0:
			return 1

		if self.decimation_rate < 2**20:
			return self.decimation_rate
		else:
			return self.decimation_rate / 2**10


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
		if(t2 <= t1):
			raise Exception("Timebase must be non-zero, with t1 < t2. Attempted to set t1=%f and t2=%f" % (t1, t2))

		decimation = self._calculate_decimation(t2-t1)
		render_decimation = self._calculate_render_downsample(t1, t2, decimation)
		buffer_offset = self._calculate_buffer_offset(t1, decimation)
		frame_offset = self._calculate_render_offset(t1, decimation)

		self.decimation_rate = decimation
		self.render_deci = render_decimation
		self.pretrigger = buffer_offset
		self.offset = frame_offset


	def _trigger_level(self, amplitude, source, scales):
		# An amplitude in volts is scaled to an ADC level depending on the trigger input source 
		# and its current configuration
		if (source == OSC_TRIG_CH1):
			level = amplitude/scales['g1']
		elif (source == OSC_TRIG_CH2):
			level = amplitude/scales['g2']
		elif (source == OSC_TRIG_DA1):
			level = (amplitude/scales['d1'])/16
		elif (source == OSC_TRIG_DA2):
			level = (amplitude/scales['d2'])/16

		return level

	def _update_datalogger_params(self, ch1, ch2):
		if self.decimation_rate == 0:
			log.warning("Decimation appears to be unset")
			decimation = 1
		else:
			decimation = self.decimation_rate

		samplerate = _OSC_ADC_SMPS / decimation
		self.timestep = 1 / samplerate

		if self.ain_mode == _OSC_AIN_DECI:
			self.procstr[0] = "*C/{:f}".format(self._deci_gain())
			self.procstr[1] = "*C/{:f}".format(self._deci_gain())
		else:
			self.procstr[0] = "*C"
			self.procstr[1] = "*C"
		self.fmtstr = self.get_fmtstr(ch1,ch2)
		self.hdrstr = self.get_hdrstr(ch1,ch2)

	def get_hdrstr(self, ch1, ch2):
		chs = [ch1, ch2]

		hdr = "Moku:Lab Data Logger\r\nStart,{{T}}\r\nSample Rate {} Hz\r\nTime".format(self.get_samplerate())
		for i,c in enumerate(chs):
			if c:
				hdr += ", Channel {i}".format(i=i+1)
		hdr += "\r\n"
		return hdr

	def get_fmtstr(self, ch1, ch2):
		chs = [ch1, ch2]
		fmtstr = "{t}"
		for i,c in enumerate(chs):
			if c:
				fmtstr += ",{{ch{i}:.8e}}".format(i=i+1)
		fmtstr += "\r\n"
		return fmtstr

	def datalogger_start(self, start=0, duration=0, use_sd=True, ch1=True, ch2=False, filetype='csv'):
		self._update_datalogger_params(ch1, ch2)
		super(Oscilloscope, self).datalogger_start(start=start, duration=duration, use_sd=use_sd, ch1=ch1, ch2=ch2, filetype=filetype)

	datalogger_start.__doc__ = _frame_instrument.FrameBasedInstrument.datalogger_start.__doc__

	def datalogger_start_single(self, use_sd=True, ch1=True, ch2=False, filetype='csv'):
		self._update_datalogger_params(ch1, ch2)
		super(Oscilloscope, self).datalogger_start_single(use_sd=use_sd, ch1=ch1, ch2=ch2, filetype=filetype)

	def set_samplerate(self, samplerate):
		""" Manually set the sample rate of the instrument.

		The sample rate is automatically calcluated and set in :any:`set_timebase`; setting it through this
		interface if you've previously set the scales through that will have unexpected results.

		This interface is most useful for datalogging and similar aquisition where one will not be looking
		at data frames.

		:type samplerate: float; *0 < samplerate < 500MSPS*
		:param samplerate: Target samples per second. Will get rounded to the nearest allowable unit.
		"""
		self.decimation_rate = _OSC_ADC_SMPS / samplerate

	def get_samplerate(self):
		if(self.decimation_rate == 0):
			raise Exception("Decimation rate appears to be unset.")
		return _OSC_ADC_SMPS / self.decimation_rate

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
		self.ain_mode = _OSC_AIN_DECI if state else _OSC_AIN_DDS

	
	def set_source(self, ch, source=OSC_SOURCE_ADC):
		""" Sets input source for given channel

		:type ch: [1,2]
		:param ch: Which input channel to set the source of.

		:type source: OSC_SOURCE_DAC, OSC_SOURCE_ADC
		:param source: Input source. May be either from the ADC or DAC of the corresponding channel. 

		"""
		valid_sources = [OSC_SOURCE_ADC, OSC_SOURCE_DAC]
		if source not in valid_sources:
			log.error("Invalid input source of %d. Expected one of %s", source, valid_sources)
			return

		if(ch==1):
			self.source_ch1 = source
		if(ch==2):
			self.source_ch2 = source

	def set_trigger(self, source, edge, level, hysteresis=0, hf_reject=False, mode=OSC_TRIG_AUTO):
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
		self.trig_volts = level # Save the desired trigger voltage

	def set_source(self, ch, source):
		""" Sets the source of the channel data to either the ADC input or internally looped-back DAC output.

		This feature allows the user to preview the Signal Generator outputs.

		:type ch: int
		:param ch: Channel Number

		:type source: OSC_SOURCE_ADC, OSC_SOURCE_DAC
		:param source: Data source
		"""
		if ch == 1:
			self.source_ch1 = source
		elif ch == 2:
			self.source_ch2 = source
		else:
			raise ValueOutOfRangeException("Incorrect channel number %d", ch)

	def set_defaults(self):
		""" Reset the Oscilloscope to sane defaults. """
		super(Oscilloscope, self).set_defaults()
		#TODO this should reset ALL registers
		self.set_source(1,OSC_SOURCE_ADC)
		self.set_source(2,OSC_SOURCE_ADC)
		self.set_trigger(OSC_TRIG_CH1, OSC_EDGE_RISING, 0)
		self.set_precision_mode(False)
		self.set_timebase(-1, 1)

		self.framerate = _OSC_FPS
		self.frame_length = _OSC_SCREEN_WIDTH
		self.set_buffer_length(4)
		self.set_xmode(OSC_FULL_FRAME)

		self.set_frontend(1, fiftyr=True)
		self.set_frontend(2, fiftyr=True)
		self.en_in_ch1 = True
		self.en_in_ch2 = True

	def _calculate_scales(self):
		# Returns the bits-to-volts numbers for each channel in the current state

		sect1 = "calibration.AG-%s-%s-%s-1" % ( "50" if self.relays_ch1 & RELAY_LOWZ else "1M",
								  "L" if self.relays_ch1 & RELAY_LOWG else "H",
								  "D" if self.relays_ch1 & RELAY_DC else "A")

		sect2 = "calibration.AG-%s-%s-%s-1" % ( "50" if self.relays_ch2 & RELAY_LOWZ else "1M",
								  "L" if self.relays_ch2 & RELAY_LOWG else "H",
								  "D" if self.relays_ch2 & RELAY_DC else "A")
		dac1 = "calibration.DG-1"
		dac2 = "calibration.DG-2"

		s1 = self.source_ch1
		s2 = self.source_ch2
		l1 = self.loopback_mode_ch1
		l2 = self.loopback_mode_ch2

		if(self.decimation_rate == 0 or self.render_deci == 0):
			log.warning("ADCs appear to be turned off or decimation unset")
			t1 = 0
			t2 = 1
		else:

			t1 = self._calculate_frame_start_time(self.decimation_rate, self.render_deci, self.offset)
			t2 = t1 + self._calculate_frame_timestep(self.decimation_rate, self.render_deci) * (_OSC_SCREEN_WIDTH - 1)

		try:
			g1 = 1 / float(self.calibration[sect1])
			g2 = 1 / float(self.calibration[sect2])
			d1 = 1 / float(self.calibration[dac1])
			d2 = 1 / float(self.calibration[dac2])
		except (KeyError, TypeError):
			log.warning("Moku appears uncalibrated")
			g1 = g2 = d1 = d2 = 1

		log.debug("gain values for sections %s, %s, %s, %s = %f, %f, %f, %f; deci %f", sect1, sect2, dac1, dac2, g1, g2, d1, d2, self._deci_gain())

		if self.ain_mode == _OSC_AIN_DECI:
			g1 /= self._deci_gain()
			g2 /= self._deci_gain()
			d1 /= self._deci_gain()
			d2 /= self._deci_gain()

		return {'g1':g1, 'g2':g2, 'd1':d1, 'd2':d2, 's1':s1, 's2':s2, 'l1':l1, 'l2':l2, 't1':t1, 't2':t2}

	def _update_dependent_regs(self, scales):
		# Trigger level must be scaled depending on the current relay settings and chosen trigger source
		self.trigger_level = self._trigger_level(self.trig_volts, self.trig_ch, scales)
		
	def commit(self):
		scales = self._calculate_scales()
		# Update any calibration scaling dependent register values
		self._update_dependent_regs(scales)

		# Commit the register values to the device
		super(Oscilloscope, self).commit()
		# Associate new state ID with the scaling factors of the state
		self.scales[self._stateid] = scales
		# TODO: Trim scales dictionary, getting rid of old ids

	# Bring in the docstring from the superclass for our docco.
	commit.__doc__ = MokuInstrument.commit.__doc__

	def attach_moku(self, moku):
		super(Oscilloscope, self).attach_moku(moku)

	attach_moku.__doc__ = MokuInstrument.attach_moku.__doc__

_osc_reg_handlers = {
	'source_ch1':		(REG_OSC_OUTSEL,	to_reg_unsigned(0, 1, allow_set=[OSC_SOURCE_ADC, OSC_SOURCE_DAC]),
											from_reg_unsigned(0, 1)),

	'source_ch2':		(REG_OSC_OUTSEL,	to_reg_unsigned(1, 1, allow_set=[OSC_SOURCE_ADC, OSC_SOURCE_DAC]),
											from_reg_unsigned(1, 1)),

	'trig_mode':		(REG_OSC_TRIGMODE,	to_reg_unsigned(0, 2, allow_set=[OSC_TRIG_AUTO, OSC_TRIG_NORMAL, OSC_TRIG_SINGLE]),
											from_reg_unsigned(0, 2)),

	'trig_edge':		(REG_OSC_TRIGCTL,	to_reg_unsigned(0, 2, allow_set=[OSC_EDGE_RISING, OSC_EDGE_FALLING, OSC_EDGE_BOTH]),
											from_reg_unsigned(0, 2)),

	'trig_ch':			(REG_OSC_TRIGCTL,	to_reg_unsigned(4, 6, allow_set=[OSC_TRIG_CH1, OSC_TRIG_CH2, OSC_TRIG_DA1, OSC_TRIG_DA2]),
											from_reg_unsigned(4, 6)),

	'hf_reject':		(REG_OSC_TRIGCTL,	to_reg_bool(12),			from_reg_bool(12)),
	'hysteresis':		(REG_OSC_TRIGCTL,	to_reg_unsigned(16, 16),	from_reg_unsigned(16, 16)),
	'trigger_level':	(REG_OSC_TRIGLVL,	to_reg_signed(0, 32),		from_reg_signed(0, 32)),

	'loopback_mode_ch1':	(REG_OSC_ACTL,	to_reg_unsigned(0, 1, allow_set=[_OSC_LB_CLIP, _OSC_LB_ROUND]),
											from_reg_unsigned(0, 1)),
	'loopback_mode_ch2':	(REG_OSC_ACTL,	to_reg_unsigned(1, 1, allow_set=[_OSC_LB_CLIP, _OSC_LB_ROUND]),
											from_reg_unsigned(1, 1)),
	'ain_mode':			(REG_OSC_ACTL,		to_reg_unsigned(16,2, allow_set=[_OSC_AIN_DDS, _OSC_AIN_DECI]),
											from_reg_unsigned(16,2)),
	'decimation_rate':	(REG_OSC_DECIMATION,to_reg_unsigned(0, 32),	from_reg_unsigned(0, 32))
}
