
import math
import logging
import re

from ._instrument import *
from . import _frame_instrument
from . import _waveform_generator
from . import _utils

log = logging.getLogger(__name__)

REG_OSC_OUTSEL		= 65
REG_OSC_TRIGMODE	= 66
REG_OSC_TRIGCTL		= 67
REG_OSC_TRIGLVL		= 68
REG_OSC_ACTL		= 69
REG_OSC_DECIMATION	= 70

### Every constant that starts with OSC_ will become an attribute of pymoku.instruments ###

# REG_OSC_OUTSEL constants
_OSC_SOURCE_ADC		= 0
_OSC_SOURCE_DAC		= 1

# REG_OSC_TRIGMODE constants
_OSC_TRIG_AUTO		= 0
_OSC_TRIG_NORMAL	= 1
_OSC_TRIG_SINGLE	= 2

# REG_OSC_TRIGLVL constants
_OSC_TRIG_CH1		= 0
_OSC_TRIG_CH2		= 1
_OSC_TRIG_DA1		= 2
_OSC_TRIG_DA2		= 3
_OSC_TRIG_EXT		= 4

_OSC_EDGE_RISING	= 0
_OSC_EDGE_FALLING	= 1
_OSC_EDGE_BOTH		= 2

_OSC_ROLL			= ROLL
_OSC_SWEEP			= SWEEP
_OSC_FULL_FRAME		= FULL_FRAME

_OSC_LB_ROUND		= 0
_OSC_LB_CLIP		= 1

_OSC_AIN_DDS		= 0
_OSC_AIN_DECI		= 1

_OSC_ADC_SMPS		= ADC_SMP_RATE
_OSC_BUFLEN			= CHN_BUFLEN
_OSC_SCREEN_WIDTH	= 1024

# Max/min values for instrument settings
_OSC_TRIGLVL_MAX = 10.0 # V
_OSC_TRIGLVL_MIN = -10.0 # V

_OSC_SAMPLERATE_MIN = 10 # smp/s
_OSC_SAMPLERATE_MAX = _OSC_ADC_SMPS

_OSC_PRETRIGGER_MAX = (2**12)-1
_OSC_POSTTRIGGER_MAX = -2**28


class VoltsData(_frame_instrument.InstrumentData):
	"""
	Object representing a frame of dual-channel data in units of Volts, and time in units of seconds.
	This is the native output format of	the :any:`Oscilloscope` instrument. The *waveformid* property
	enables identification of uniqueness of a frame of data, as it is possible to retrieve the same
	data more than once (i.e. if the instrument has been paused).

	This object should not be instantiated directly, but will be returned by a call to
	:any:`get_data <pymoku.instruments.Oscilloscope.get_data>` or
	:any:`get_realtime_data <pymoku.instruments.Oscilloscope.get_realtime_data>` on the associated
	:any:`Oscilloscope`	instrument.

	.. autoinstanceattribute:: pymoku._frame_instrument.VoltsData.ch1
		:annotation: = [CH1_DATA]

	.. autoinstanceattribute:: pymoku._frame_instrument.VoltsData.ch2
		:annotation: = [CH2_DATA]

	.. autoinstanceattribute:: pymoku._frame_instrument.VoltsData.time
		:annotation: = [TIME]

	.. autoinstanceattribute:: pymoku._frame_instrument.VoltsData.waveformid
		:annotation: = n
	"""
	def __init__(self, instrument, scales):
		super(VoltsData, self).__init__(instrument)

		#: Channel 1 data array in units of Volts. Present whether or not the channel is enabled, but the
		#: contents are undefined in the latter case.
		self.ch1 = []

		#: Channel 2 data array in units of Volts.
		self.ch2 = []

		#: Timebase
		self.time = []

		self._scales = scales

	def __json__(self):
		return { 'ch1': self.ch1, 'ch2' : self.ch2, 'time' : self.time, 'waveform_id' : self.waveformid }

	def process_complete(self):
		super(VoltsData, self).process_complete()

		if self._stateid not in self._scales:
			log.info("Can't render voltage frame, haven't saved calibration data for state %d", self._stateid)
			return

		scales = self._scales[self._stateid]
		scale_ch1 = scales['scale_ch1']
		scale_ch2 = scales['scale_ch2']
		t1 = scales['time_min']
		ts = scales['time_step']

		try:
			smpls = int(len(self._raw1) / 4)
			dat = struct.unpack('<' + 'i' * smpls, self._raw1)
			dat = [ x if x != -0x80000000 else None for x in dat ]

			self._ch1_bits = [ float(x) if x is not None else None for x in dat[:1024] ]
			self.ch1 = [ x * scale_ch1 if x is not None else None for x in self._ch1_bits]

			smpls = int(len(self._raw2) / 4)
			dat = struct.unpack('<' + 'i' * smpls, self._raw2)
			dat = [ x if x != -0x80000000 else None for x in dat ]

			self._ch2_bits = [ float(x) if x is not None else None for x in dat[:1024] ]
			self.ch2 = [ x * scale_ch2 if x is not None else None for x in self._ch2_bits]
		except (IndexError, TypeError, struct.error):
			# If the data is bollocksed, force a reinitialisation on next packet
			log.exception("Oscilloscope packet")
			self._frameid = None
			self._complete = False


		self.time = [ t1 + (x * ts) for x in range(_OSC_SCREEN_WIDTH)]

		return True

	def process_buffer(self):
		# Compute the x-axis of the buffer
		if self._stateid not in self._scales:
			log.error("Can't process buffer - haven't saved calibration for state %d", self._stateid)
			return
		scales = self._scales[self._stateid]
		self.time = [scales['buff_time_min'] + (scales['buff_time_step'] * x) for x in range(len(self.ch1))]
		return True
	'''
		Plotting helper functions
	'''
	def _get_timescale(self, tspan):
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

		if self._stateid not in self._scales:
			log.error("Can't get x-axis format, haven't saved calibration data for state %d", self._stateid)
			return

		scales = self._scales[self._stateid]
		t1 = scales['time_min']
		ts = scales['time_step']
		tscale_str, tscale_const = self._get_timescale(ts*_OSC_SCREEN_WIDTH)

		return {'xaxis': '%.1f %s' % (x*tscale_const, tscale_str), 'xcoord': '%.3f %s' % (x*tscale_const, tscale_str)}

	def get_xaxis_fmt(self, x, pos):
		""" Function suitable to use as argument to a matplotlib FuncFormatter for X (time) axis """
		return self._get_xaxis_fmt(x,pos)['xaxis']

	def get_xcoord_fmt(self, x):
		""" Function suitable to use as argument to a matplotlib FuncFormatter for X (time) coordinate """
		return self._get_xaxis_fmt(x,None)['xcoord']

	def _get_yaxis_fmt(self,y,pos):
		return {'yaxis': '%.1f %s' % (y,'V'), 'ycoord': '%.3f %s' % (y,'V')}

	def get_yaxis_fmt(self, y, pos):
		""" Function suitable to use as argument to a matplotlib FuncFormatter for Y (voltage) axis """
		return self._get_yaxis_fmt(y,pos)['yaxis']

	def get_ycoord_fmt(self, y):
		""" Function suitable to use as argument to a matplotlib FuncFormatter for Y (voltage) coordinate """
		return self._get_yaxis_fmt(y,None)['ycoord']


class _CoreOscilloscope(_frame_instrument.FrameBasedInstrument):

	def __init__(self):
		super(_CoreOscilloscope, self).__init__()
		self._register_accessors(_osc_reg_handlers)

		self.id = 1
		self.type = "oscilloscope"
		self.calibration = None

		# NOTE: Register mapped properties will be overwritten in sync registers call
		# on deploy_instrument(). No point setting them here.
		self.scales = {}
		self._set_frame_class(VoltsData, instrument=self, scales=self.scales)

		# Define any (non-register-mapped) properties that are used when committing
		# as a commit is called when the instrument is set running
		self.trig_volts = 0
		#self.hysteresis_volts = 0

		# All instruments need a binstr, procstr and format string.
		self.logname = "MokuOscilloscopeData"
		self.binstr = "<s32"
		self.procstr = ['','']
		self.fmtstr = ''
		self.hdrstr = ''
		self.timestep = 1

	def _calculate_decimation(self, t1, t2):

		# Calculate time the buffer should contain
		# Want one frame to be approximately 1/3 of a buffer (RD ~ 5)
		# or the full buffer if it would take longer than 100ms

		# TODO: Put some limits on what the span/decimation can be
		if (t2 < 0):
			buffer_span = -float(t1)
		else:
			buffer_span = float(t2 - t1)

		deci = math.ceil(ADC_SMP_RATE * buffer_span / _OSC_BUFLEN)

		return deci


	def _calculate_render_downsample(self, t1, t2, decimation):
		# Calculate how much to render downsample
		tspan = float(t2) - float(t1)
		buffer_smp_rate = ADC_SMP_RATE/float(decimation)
		buffer_time_span = _OSC_BUFLEN/buffer_smp_rate

		def _cubic_int_to_scale(integer):
			# Integer to cubic scaling ratio (see Wiki)
			return float(integer/(2.0**7)) + 1

		# Enforce a maximum ADC sampling rate
		screen_smp_rate = min(_OSC_SCREEN_WIDTH/tspan, ADC_SMP_RATE)

		# Clamp the render downsampling ratio between 1.0 and ~16.0
		render_downsample = min(max(buffer_smp_rate/screen_smp_rate, 1.0), _cubic_int_to_scale(0x077E))
		return render_downsample

	def _calculate_buffer_offset(self, t1, decimation):
		# Calculate the number of pretrigger samples and offset it by an additional (CubicRatio) samples
		buffer_smp_rate = ADC_SMP_RATE/decimation
		buffer_offset_secs = -1.0 * t1
		buffer_offset = math.ceil(min(max(math.ceil(buffer_offset_secs * buffer_smp_rate / 4.0), _OSC_POSTTRIGGER_MAX), _OSC_PRETRIGGER_MAX))

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

	def _calculate_buffer_timestep(self, decimation):
		return float(decimation)/float(ADC_SMP_RATE)

	def _calculate_buffer_start_time(self, decimation, buffer_offset):
		return self._calculate_buffer_timestep(decimation) * (-1.0 * buffer_offset) * 4.0

	def _deci_gain(self):
		if self.decimation_rate == 0:
			return 1

		if self.decimation_rate < 2**20:
			return self.decimation_rate
		else:
			return self.decimation_rate / 2**10


	@needs_commit
	def set_timebase(self, t1, t2):
		""" Set the left- and right-hand span for the time axis.
		Units are seconds relative to the trigger point.

		:type t1: float
		:param t1:
			Time, in seconds, from the trigger point to the left of screen. This may be negative (trigger on-screen)
			or positive (trigger off the left of screen).

		:type t2: float
		:param t2: As *t1* but to the right of screen.

		:raises InvalidConfigurationException: if the timebase is backwards or zero.
		"""
		if(t2 <= t1):
			raise InvalidConfigurationException("Timebase must be non-zero, with t1 < t2. Attempted to set t1=%f and t2=%f" % (t1, t2))

		decimation = self._calculate_decimation(t1,t2)
		render_decimation = self._calculate_render_downsample(t1, t2, decimation)
		buffer_offset = self._calculate_buffer_offset(t1, decimation)
		frame_offset = self._calculate_render_offset(t1, decimation)

		self.decimation_rate = decimation
		self.render_deci = render_decimation
		self.pretrigger = buffer_offset
		self.offset = frame_offset

	def _source_volts_per_bit(self, source, scales):
		"""
			Converts volts to bits depending on the source (ADC1/2, DAC1/2)
		"""
		if (source == _OSC_TRIG_CH1):
			level = scales['gain_adc1']
		elif (source == _OSC_TRIG_CH2):
			level = scales['gain_adc2']
		elif (source == _OSC_TRIG_DA1):
			level = (scales['gain_dac1'])*16
		elif (source == _OSC_TRIG_DA2):
			level = (scales['gain_dac2'])*16
		else:
			level = 1.0
		return level

	@needs_commit
	def set_samplerate(self, samplerate, trigger_offset=0):
		""" Manually set the sample rate of the instrument.

		The sample rate is automatically calculated and set in :any:`set_timebase`.

		This interface allows you to specify the rate at which data is sampled, and set
		a trigger offset in number of samples. This interface is useful for datalogging and capturing
		of data frames.

		:type samplerate: float; *0 < samplerate <= 500 Msmp/s*
		:param samplerate: Target samples per second. Will get rounded to the nearest allowable unit.

		:type trigger_offset: int; *-2^16 < trigger_offset < 2^31*
		:param trigger_offset: Number of samples before (-) or after (+) the trigger point to start capturing.

		:raises ValueOutOfRangeException: if either parameter is out of range.
		"""
		_utils.check_parameter_valid('range', samplerate, [_OSC_SAMPLERATE_MIN,_OSC_SAMPLERATE_MAX], 'samplerate', 'smp/s')
		_utils.check_parameter_valid('range', trigger_offset, [-2**16 + 1, 2**31 - 1], 'trigger offset', 'samples')

		decimation = _OSC_ADC_SMPS / samplerate

		self.decimation_rate = decimation
		self.timestep = 1.0/(_OSC_ADC_SMPS/self.decimation_rate)
		# Ensure the buffer offset is large enough to incorporate the desired pretrigger/posttrigger data
		self.pretrigger = - math.ceil(trigger_offset/4.0) if trigger_offset > 0 else - math.floor(trigger_offset/4.0)
		# We don't want any rendering as each sample is already at the desired samplerate
		self.render_deci = 1
		# The render offset needs to be corrected for cubic downsampling (even with unity decimation)
		self.offset = - round(trigger_offset) + self.render_deci

	def get_samplerate(self):
		""" :return: The current instrument sample rate (Hz) """
		if(self.decimation_rate == 0):
			log.info("Decimation rate appears to be unset.")
			return _OSC_ADC_SMPS
		return _OSC_ADC_SMPS / float(self.decimation_rate)

	@needs_commit
	def set_xmode(self, xmode):
		"""
		Set rendering mode for the horizontal axis.

		:type xmode: string, {'roll','sweep','fullframe'}
		:param xmode:
			Respectively; Roll Mode (scrolling), Sweep Mode (normal oscilloscope trace sweeping across the screen)
			or Full Frame (like sweep, but waits for the frame to be completed).
		"""
		_str_to_xmode = {
			'roll' : _OSC_ROLL,
			'sweep' : _OSC_SWEEP,
			'fullframe' : _OSC_FULL_FRAME
		}
		xmode = _utils.str_to_val(_str_to_xmode, xmode, 'X-mode')
		self.x_mode = xmode

	@needs_commit
	def set_precision_mode(self, state):
		""" Change aquisition mode between downsampling and decimation.
		Precision mode, a.k.a Decimation, samples at full rate and applies a low-pass filter to the data. This improves
		precision. Normal mode works by direct downsampling, throwing away points it doesn't need.

		Precision mode canot be enabled if the trigger hysteresis has been explicitly set to an explicit, non-zero voltage.
		See :any:`set_trigger <pymoku.instruments.Oscilloscope.set_trigger`.

		:param state: Select Precision Mode
		:type state: bool
		"""
		_utils.check_parameter_valid('bool', state, desc='precision mode enable')
		#if state and self.hysteresis > 0 :
		#	raise InvalidConfigurationException("Precision mode and Hysteresis can't be set at the same time.")
		self.ain_mode = _OSC_AIN_DECI if state else _OSC_AIN_DDS

	def is_precision_mode(self):
		return self.ain_mode is _OSC_AIN_DECI

	@needs_commit
	def set_trigger(self, source, edge, level, hysteresis=False, hf_reject=False, mode='auto'):
		""" Sets trigger source and parameters.

		The hysteresis value changes behaviour based on aquisition mode, due to hardware limitations.  If the
		Oscilloscope is in precision mode, hysteresis must be 0 or one of the strings 'auto' or 'noise'; an explicit,
		non-zero value in volts can only be specified for normal aquisition (see
		:any:`set_precision_mode <pymoku.instruments.Oscilloscope.set_precision_mode>`).  If hysteresis is 'auto' or
		'noise', a small value will be automatically calulated based on decimation. Values 'auto' and 'noise' are suitable
		for high- and low-SNR signals respectively.

		:type source: string, {'in1','in2','out1','out2','ext'}
		:param source: Trigger Source. May be either an input or output channel, or external. The output options allow
				triggering off an internally-generated waveform. External refers to the back-panel connector of the same
				name, allowing triggering from an externally-generated digital [LV]TTL or CMOS signal.

		:type edge: string, {'rising','falling','both'}
		:param edge: Which edge to trigger on.

		:type level: float, [-10.0, 10.0] volts
		:param level: Trigger level

		:type hysteresis: bool
		:param hysteresis: Enable Hysteresis around trigger point.

		:type hf_reject: bool
		:param hf_reject: Enable high-frequency noise rejection

		:type mode: string, {'auto', 'normal'}
		:param mode: Trigger mode.

		.. note::
			Traditional Oscilloscopes have a "Single Trigger" mode that captures an event then
			pauses the instrument. In pymoku, there is no need to pause the instrument as you
			can simply choose to continue using the last captured frame.  That is, set trigger
			``mode='normal'`` then retrieve a single frame using :any:`get_data <pymoku.instruments.Oscilloscope.get_data>`
			or :any:`get_realtime_data <pymoku.instruments.Oscilloscope.get_realtime_data>`
			with ``wait=True``.

		"""
		# Convert the input parameter strings to bit-value mappings
		_utils.check_parameter_valid('bool', hysteresis, desc="enable hysteresis")
		_utils.check_parameter_valid('range', level, [_OSC_TRIGLVL_MIN, _OSC_TRIGLVL_MAX], 'trigger level', 'Volts')
		_utils.check_parameter_valid('bool', hf_reject, 'High-frequency reject enable')

		# External trigger source is only available on Moku 20
		if (self._moku.get_hw_version() == 1.0) and source == 'ext':
			raise ValueOutOfRangeException('External trigger source is not available on your hardware.')

		# Precision mode should be off if hysteresis is being used
		#if self.ain_mode == _OSC_AIN_DECI and hysteresis > 0:
		#	raise InvalidConfigurationException("Precision mode and Hysteresis can't be set at the same time.")

		# self.hysteresis_volts = hysteresis
		# TODO: Enable setting hysteresis level. For now we use the iPad LSB values for ON/OFF.
		self.hysteresis = 25 if hysteresis else 5

		_str_to_trigger_source = {
			'in1' : _OSC_TRIG_CH1,
			'in2' : _OSC_TRIG_CH2,
			'out1' : _OSC_TRIG_DA1,
			'out2' : _OSC_TRIG_DA2,
			'ext' : _OSC_TRIG_EXT
		}
		_str_to_edge = {
			'rising' : _OSC_EDGE_RISING,
			'falling' : _OSC_EDGE_FALLING,
			'both'	: _OSC_EDGE_BOTH
		}
		_str_to_trigger_mode = {
			'auto' : _OSC_TRIG_AUTO,
			'normal' : _OSC_TRIG_NORMAL
			#'single' : _OSC_TRIG_SINGLE
		}
		source = _utils.str_to_val(_str_to_trigger_source, source, 'trigger source')
		edge = _utils.str_to_val(_str_to_edge, edge, 'edge type')
		mode = _utils.str_to_val(_str_to_trigger_mode, mode,'trigger mode')

		self.trig_ch = source
		self.trig_edge = edge

		self.hf_reject = hf_reject
		self.trig_mode = mode
		self.trig_volts = level # Save the desired trigger voltage

	@needs_commit
	def set_source(self, ch, source, lmode='round'):
		""" Sets the source of the channel data to either the analog input or internally looped-back digital output.

		This feature allows the user to preview the Waveform Generator outputs.

		:type ch: int; {1,2}
		:param ch: Channel Number

		:type source: string, {'in','out'}
		:param source: Where the specified channel should source data from (either the input or internally looped back output)

		:type lmode: string, {'clip','round'}
		:param lmode: DAC Loopback mode (ignored 'in' sources)
		"""
		_utils.check_parameter_valid('set', ch, [1,2], 'channel')
		_str_to_lmode = {
			'round' : _OSC_LB_ROUND,
			'clip' : _OSC_LB_CLIP
		}
		_str_to_channel_data_source = {
			'in' : _OSC_SOURCE_ADC,
			'out' : _OSC_SOURCE_DAC
		}
		source = _utils.str_to_val(_str_to_channel_data_source, source, 'channel data source')
		lmode = _utils.str_to_val(_str_to_lmode, lmode, 'DAC loopback mode')
		if ch == 1:
			self.source_ch1 = source
			if source == _OSC_SOURCE_DAC:
				self.loopback_mode_ch1 = lmode
		elif ch == 2:
			self.source_ch2 = source
			if source == _OSC_SOURCE_DAC:
				self.loopback_mode_ch2 = lmode
		else:
			raise ValueOutOfRangeException("Incorrect channel number %d", ch)

	@needs_commit
	def set_defaults(self):
		""" Reset the Oscilloscope to sane defaults. """
		super(_CoreOscilloscope, self).set_defaults()
		self.set_source(1,'in')
		self.set_source(2,'in')
		self.set_trigger('in1','rising', 0)
		self.set_precision_mode(False)
		self.set_timebase(-1, 1)
		self._set_pause(False)

		self.frame_length = _OSC_SCREEN_WIDTH
		self._set_buffer_length(4)
		self.set_xmode('fullframe')

		self.set_frontend(1, fiftyr=True, atten=False, ac=False)
		self.set_frontend(2, fiftyr=True, atten=False, ac=False)
		self.en_in_ch1 = True
		self.en_in_ch2 = True

	def _calculate_scales(self):
		g1, g2 = self._adc_gains()
		d1, d2 = self._dac_gains()

		l1 = self.loopback_mode_ch1
		l2 = self.loopback_mode_ch2

		s1 = self.source_ch1
		s2 = self.source_ch2

		if(self.decimation_rate == 0 or self.render_deci == 0):
			log.warning("ADCs appear to be turned off or decimation unset")
			t1 = 0
			ts = 1
			bt1 = 0
			bts = 1
		else:
			t1 = self._calculate_frame_start_time(self.decimation_rate, self.render_deci, self.offset)
			ts = self._calculate_frame_timestep(self.decimation_rate, self.render_deci)
			bt1 = self._calculate_buffer_start_time(self.decimation_rate, self.pretrigger)
			bts = self._calculate_buffer_timestep(self.decimation_rate)

		scale_ch1 = g1 if s1 == _OSC_SOURCE_ADC else d1
		scale_ch2 = g2 if s2 == _OSC_SOURCE_ADC else d2

		if self.ain_mode == _OSC_AIN_DECI:
			scale_ch1 /= self._deci_gain()
			scale_ch2 /= self._deci_gain()

		def _compute_total_scaling_factor(adc,dac,src,lmode):
			# Change scaling factor depending on the source type
			if (src == _OSC_SOURCE_ADC):
				scale = 1.0
			elif (src == _OSC_SOURCE_DAC):
				if(lmode == _OSC_LB_CLIP):
					scale = 1.0
				else: # Rounding mode
					scale = 16.0
			else:
				log.error("Invalid source type on channel.")
				return
			return scale

		# These are the combined scaling factors for both channel 1 and channel 2 raw data
		scale_ch1 *= _compute_total_scaling_factor(g1,d1,s1,l1)
		scale_ch2 *= _compute_total_scaling_factor(g2,d2,s2,l2)


		return {'scale_ch1': scale_ch1,
				'scale_ch2': scale_ch2,
				'gain_adc1': g1,
				'gain_adc2': g2,
				'gain_dac1': d1,
				'gain_dac2': d2,
				'source_ch1': s1,
				'source_ch2': s2,
				'gain_loopback1': l1,
				'gain_loopback2': l2,
				'time_min': t1,
				'time_step': ts,
				'buff_time_min': bt1,
				'buff_time_step': bts}

	def _update_dependent_regs(self, scales):
		# Trigger level must be scaled depending on the current relay settings and chosen trigger source
		self.trigger_level = self.trig_volts / self._source_volts_per_bit(self.trig_ch, scales)
		#self.hysteresis = self.hysteresis_volts / self._source_volts_per_bit(self.trig_ch, scales)

	def _update_datalogger_params(self):
		scales = self._calculate_scales()

		samplerate = self.get_samplerate()
		self.timestep = 1.0/samplerate

		# Use the new scales to decide on the processing string
		self.procstr[0] = "*{:.15f}".format(scales['scale_ch1'])
		self.procstr[1] = "*{:.15f}".format(scales['scale_ch2'])

		self.fmtstr = self._get_fmtstr(self.ch1,self.ch2)
		self.hdrstr = self._get_hdrstr(self.ch1,self.ch2)

	def _get_hdrstr(self, ch1, ch2):
		chs = [ch1, ch2]

		hdr = "% Moku:Oscilloscope\r\n"
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

	def _on_reg_sync(self):
		# Do the instrument-level post-sync stuff
		super(_CoreOscilloscope, self)._on_reg_sync()

		# This function is used to update any local variables when a Moku has
		# had its registers synchronised with the current instrument
		if self.decimation_rate == 0:
			self.timestep = 1.0/(_OSC_ADC_SMPS)
		else:
			samplerate = _OSC_ADC_SMPS / float(self.decimation_rate)
			self.timestep = 1.0/samplerate

		scales = self._calculate_scales()
		self.scales[self._stateid] = scales

		# Update internal state given new reg values. This is the inverse of update_dependent_regs
		self.trig_volts = self.trigger_level * self._source_volts_per_bit(self.trig_ch, scales)
		# self.hysteresis_volts = self.hysteresis * self._source_volts_per_bit(self.trig_ch, scales)

		self._update_datalogger_params()


	def commit(self):
		scales = self._calculate_scales()
		# Update any calibration scaling dependent register values
		self._update_dependent_regs(scales)
		self._update_datalogger_params()

		# Commit the register values to the device
		super(_CoreOscilloscope, self).commit()
		# Associate new state ID with the scaling factors of the state
		self.scales[self._stateid] = scales
		# TODO: Trim scales dictionary, getting rid of old ids

	# Bring in the docstring from the superclass for our docco.
	commit.__doc__ = MokuInstrument.commit.__doc__


class Oscilloscope(_CoreOscilloscope, _waveform_generator.BasicWaveformGenerator):
	""" Oscilloscope instrument object.

	To run a new Oscilloscope instrument, this should be instantiated and deployed via a connected
	:any:`Moku` object using :any:`deploy_instrument`. Alternatively, a pre-configured instrument object
	can be obtained by discovering an already running Oscilloscope instrument on a Moku:Lab device via
	:any:`discover_instrument`.

	.. automethod:: pymoku.instruments.Oscilloscope.__init__

	.. attribute:: framerate
		:annotation: = 10

		Frame Rate, range 10 - 30.

	.. attribute:: type
		:annotation: = "oscilloscope"

		Name of this instrument.

	"""
	# The Oscilloscope core is split out without the siggen so it can be used as embedded in other instruments,
	# e.g. lockin, pid etc.
	pass


_osc_reg_handlers = {
	'source_ch1':		(REG_OSC_OUTSEL,	to_reg_unsigned(0, 1, allow_set=[_OSC_SOURCE_ADC, _OSC_SOURCE_DAC]),
											from_reg_unsigned(0, 1)),

	'source_ch2':		(REG_OSC_OUTSEL,	to_reg_unsigned(1, 1, allow_set=[_OSC_SOURCE_ADC, _OSC_SOURCE_DAC]),
											from_reg_unsigned(1, 1)),

	'trig_mode':		(REG_OSC_TRIGMODE,	to_reg_unsigned(0, 2, allow_set=[_OSC_TRIG_AUTO, _OSC_TRIG_NORMAL, _OSC_TRIG_SINGLE]),
											from_reg_unsigned(0, 2)),

	'trig_edge':		(REG_OSC_TRIGCTL,	to_reg_unsigned(0, 2, allow_set=[_OSC_EDGE_RISING, _OSC_EDGE_FALLING, _OSC_EDGE_BOTH]),
											from_reg_unsigned(0, 2)),

	'trig_ch':			(REG_OSC_TRIGCTL,	to_reg_unsigned(4, 6, allow_set=[_OSC_TRIG_CH1, _OSC_TRIG_CH2, _OSC_TRIG_DA1, _OSC_TRIG_DA2, _OSC_TRIG_EXT]),
											from_reg_unsigned(4, 6)),

	'hf_reject':		(REG_OSC_TRIGCTL,	to_reg_bool(12),			from_reg_bool(12)),
	'hysteresis':		(REG_OSC_TRIGCTL,	to_reg_unsigned(16, 16),	from_reg_unsigned(16, 16)),
	# The conversion of trigger level value to register value is dependent on the trigger source
	# and therefore is performed in the _trigger_level() function above.
	'trigger_level':	(REG_OSC_TRIGLVL,	to_reg_signed(0, 32),		from_reg_signed(0, 32)),

	'loopback_mode_ch1':	(REG_OSC_ACTL,	to_reg_unsigned(0, 1, allow_set=[_OSC_LB_CLIP, _OSC_LB_ROUND]),
											from_reg_unsigned(0, 1)),
	'loopback_mode_ch2':	(REG_OSC_ACTL,	to_reg_unsigned(1, 1, allow_set=[_OSC_LB_CLIP, _OSC_LB_ROUND]),
											from_reg_unsigned(1, 1)),
	'ain_mode':			(REG_OSC_ACTL,		to_reg_unsigned(16,2, allow_set=[_OSC_AIN_DDS, _OSC_AIN_DECI]),
											from_reg_unsigned(16,2)),
	'decimation_rate':	(REG_OSC_DECIMATION,to_reg_unsigned(0, 32),	from_reg_unsigned(0, 32))
}
