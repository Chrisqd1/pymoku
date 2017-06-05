import math
import logging

from ._instrument import *
from . import _frame_instrument

log = logging.getLogger(__name__)

REG_NA_SWEEP_FREQ_MIN_L 	= 64
REG_NA_SWEEP_FREQ_MIN_H 	= 65
REG_NA_SWEEP_FREQ_DELTA_L 	= 66
REG_NA_SWEEP_FREQ_DELTA_H 	= 67
REG_NA_LOG_EN				= 68
REG_NA_HOLD_OFF_L			= 69
REG_NA_SWEEP_LENGTH			= 71
REG_NA_AVERAGE_TIME			= 72
REG_NA_ENABLES				= 73
REG_NA_SWEEP_AMP_MULT		= 74
REG_NA_SETTLE_CYCLES		= 76
REG_NA_AVERAGE_CYCLES		= 77


_NA_ADC_SMPS		= 500e6
_NA_FPGA_CLOCK 		= 125e6
_NA_DAC_SMPS 		= 1e9
_NA_DAC_VRANGE 		= 1
_NA_DAC_BITDEPTH 	= 2**16
_NA_DAC_BITS2V		= _NA_DAC_BITDEPTH/_NA_DAC_VRANGE
_NA_BUFLEN			= 2**14
_NA_SCREEN_WIDTH	= 1024
_NA_SCREEN_STEPS	= _NA_SCREEN_WIDTH - 1
_NA_FPS				= 2
_NA_FREQ_SCALE		= 2**48 / _NA_DAC_SMPS
_NA_FXP_SCALE 		= 2.0**30


class _NetAnChannel():

	def __init__(self, input_signal, gain_correction, front_end_scale, output_amp, reference):
		# De-interleave
		self.i_sig, self.q_sig = zip(*zip(*[iter(input_signal)]*2))

		# Each I, Q and/or G entry may be None in some circumstances
		self.magnitude = [ None if not I and not Q else 2.0 * math.sqrt((I or 0)**2 + (Q or 0)**2) / (G or 1) * front_end_scale for I, Q, G in zip(self.i_sig, self.q_sig, gain_correction) ]

		if reference is not None:
			self.magnitude = [ None if not M else M / (C or 1) * output_amp for M, C in zip(self.magnitude, reference) ]

		self.magnitude_dB = [ None if not x else 20.0 * math.log10(x / output_amp) for x in self.magnitude ]

		self.phase = [ math.atan2(Q or 0, I or 0) for I, Q in zip(self.i_sig, self.q_sig)]


class NetAnFrame(_frame_instrument.DataFrame):
	"""
	Object representing a frame of data in units of power vs frequency. This is the native output format of
	the :any:`NetAn` instrument and similar.

	This object should not be instantiated directly, but will be returned by a supporting *get_frame*
	implementation.

	.. autoinstanceattribute:: pymoku._frame_instrument.NetAnFrame.ch1
		:annotation: = [CH1_DATA]

	.. autoinstanceattribute:: pymoku._frame_instrument.NetAnFrame.ch2
		:annotation: = [CH2_DATA]

	.. autoinstanceattribute:: pymoku._frame_instrument.NetAnFrame.fs
		:annotation: = [FREQ]

	.. autoinstanceattribute:: pymoku._frame_instrument.NetAnFrame.waveformid
		:annotation: = n
	"""
	def __init__(self, scales):
		super(NetAnFrame, self).__init__()

		#: Channel 1 data array in units of power. Present whether or not the channel is enabled, but the
		#: contents are undefined in the latter case.

		#: The frequency range associated with both channels
		self.fs = []

		#: Obtain all data scaling factors relevant to current NetAn configuration
		self.scales = scales

	def __json__(self):
		return { 'ch1' : self.ch1, 'ch2' : self.ch2, 'fs' : self.fs }

	def process_complete(self):
		if self.stateid not in self.scales:
			log.error("Can't render NetAn frame, haven't saved calibration data for state %d", self.stateid)
			self.complete = False
			return

		# Get scaling/correction factors based on current instrument configuration
		scales = self.scales[self.stateid]

		try:
			# Set the frequency range of valid data in the current frame (same for both channels)
			self.fs = scales['frequency_axis']

			smpls = int(len(self.raw1) / 4)
			dat = struct.unpack('<' + 'i' * smpls, self.raw1)
			dat = [ x if x != -0x80000000 else None for x in dat ]

			# NetAn data is backwards because $(EXPLETIVE), also remove zeros for the sake of common
			# display on a log axis.
			self.ch1_bits = [ float(x) if x is not None else None for x in dat[:1024] ]
			self.ch1 = _NetAnChannel(self.ch1_bits, scales['gain_correction'], scales['g1'], scales['sweep_amplitude_ch1'], scales['reference_ch1'])


			smpls = int(len(self.raw2) / 4)
			dat = struct.unpack('<' + 'i' * smpls, self.raw2)
			dat = [ x if x != -0x80000000 else None for x in dat ]

			self.ch2_bits = [ float(x) if x is not None else None for x in dat[:1024] ]
			self.ch2 = _NetAnChannel(self.ch2_bits, scales['gain_correction'], scales['g2'], scales['sweep_amplitude_ch2'], scales['reference_ch2'])

		except (IndexError, TypeError, struct.error):
			# If the data is bollocksed, force a reinitialisation on next packet
			log.exception("NetAn packet")
			self.frameid = None
			self.complete = False

		# A valid frame is there's at least one valid sample in each channel
		return self.ch1 and self.ch2


	def _get_freqScale(self, f):
		# Returns a scaling factor and units for frequency 'X'
		if(f > 1e6):
			scale_str = 'MHz'
			scale_const = 1e-6
		elif (f > 1e3):
			scale_str = 'kHz'
			scale_const = 1e-3
		elif (f > 1):
			scale_str = 'Hz'
			scale_const = 1
		elif (f > 1e-3):
			scale_str = 'mHz'
			scale_const = 1e3
		else:
			scale_str = 'uHz'
			scale_const = 1e6

		return [scale_str, scale_const]

	def _get_xaxis_fmt(self, x, pos):
		# This function returns a format string for the x-axis ticks and x-coordinates along the frequency scale
		# Use this to set an x-axis format during plotting of NetAn frames
		if self.stateid not in self.scales:
			log.error("Can't get x-axis format, haven't saved calibration data for state %d", self.stateid)
			return

		scales = self.scales[self.stateid]
		f1, f2 = scales['fspan']

		fscale_str, fscale_const = self._get_freqScale(f2)

		return {'xaxis': '%.1f %s' % (x*fscale_const, fscale_str), 'xcoord': '%.3f %s' % (x*fscale_const, fscale_str)}

	def get_xaxis_fmt(self, x, pos):
		return self._get_xaxis_fmt(x,pos)['xaxis']

	def get_xcoord_fmt(self, x):
		return self._get_xaxis_fmt(x,None)['xcoord']

	def _get_yaxis_fmt(self, y, pos, scale='log'):
		yfmt = {
			'linear' : '%.1f %s' % (y,'V'),
			'log' : '%.1f %s' % (y,'dBm')
		}
		ycoord = {
			'linear' : '%.3f %s' % (y,'V'),
			'log' : '%.3f %s' % (y,'dBm')
		}

		return {'yaxis': yfmt[scale], 'ycoord': ycoord[scale]}

	def get_linear_yaxis_fmt(self, y, pos):
		return self._get_yaxis_fmt(y, pos, 'linear')['yaxis']

	def get_log_yaxis_fmt(self, y, pos):
		return self._get_yaxis_fmt(y, pos, 'log')['yaxis']

	def get_linear_ycoord_fmt(self, y):
		return self._get_yaxis_fmt(y, None, 'linear')['ycoord']

	def get_log_ycoord_fmt(self, y):
		return self._get_yaxis_fmt(y, None, 'log')['ycoord']


class NetAn(_frame_instrument.FrameBasedInstrument):
	""" Network Analyser instrument object. This should be instantiated and attached to a :any:`Moku` instance.
	"""
	def __init__(self):
		super(NetAn, self).__init__()
		self._register_accessors(_na_reg_handlers)

		self.scales = {}
		self.set_frame_class(NetAnFrame, scales=self.scales)

		self.id = 9
		self.type = "NetAn"

		self.sweep_amp_volts_ch1 = 0
		self.sweep_amp_volts_ch2 = 0

		self.reference_ch1 = None
		self.reference_ch2 = None


	def commit(self):
		super(NetAn, self).commit()

		# Update the scaling factors for processing of incoming frames
		# stateid allows us to track which scales correspond to which register state
		self.scales[self._stateid] = self._calculate_scales()
	commit.__doc__ = MokuInstrument.commit.__doc__

	def _calculate_sweep_delta(self, start_frequency, end_frequency, sweep_length, log_scale):
		if log_scale:
			sweep_freq_delta = round(((end_frequency / start_frequency)**(1.0/(sweep_length - 1)) - 1) * _NA_FXP_SCALE)
		else:
			sweep_freq_delta = round(((end_frequency - start_frequency)/(sweep_length-1)) * _NA_FREQ_SCALE)

		return sweep_freq_delta

	def start_sweep(self, f_start=100, f_end=125e6, sweep_points=512, sweep_log=False, single_sweep=False, averaging_time=1e-3, settling_time=1e-3, averaging_cycles=1, settling_cycles=1):
		self.sweep_freq_min = f_start
		self.sweep_length = sweep_points
		self.log_en = sweep_log

		self.single_sweep = single_sweep
		self.loop_sweep = not single_sweep

		self.averaging_time = averaging_time
		self.averaging_cycles = averaging_cycles
		self.settling_time = settling_time

		self.sweep_freq_delta = self._calculate_sweep_delta(f_start, f_end, sweep_points, sweep_log)
		self.settling_cycles = settling_cycles

	def stop_sweep(self):
		self.single_sweep = self.loop_sweep = False

	def set_output_amplitude(self, ch, amplitude):
		# Set up the output scaling register but also save the voltage value away for use
		# in the state dictionary to scale incoming data
		if ch == 1:
			self.sweep_amplitude_ch1 = amplitude
			self.sweep_amp_volts_ch1 = amplitude
			self.channel1_en = amplitude > 0
		elif ch == 2:
			self.sweep_amplitude_ch2 = amplitude
			self.sweep_amp_volts_ch2 = amplitude
			self.channel2_en = amplitude > 0

	def set_reference_trace(self, reference):
		self.reference_ch1 = reference.ch1.magnitude
		self.reference_ch2 = reference.ch2.magnitude

	def _calculate_freq_axis(self):
		# generates the frequency vector for plotting. The logarithmic scale is calculated on the FPGA with fixed point precision,
		# hence the forced fxp calculation when log_scale = True.

		F_start = self.sweep_freq_min * _NA_FREQ_SCALE
		F_axis = [F_start]

		for k in range(1, self.sweep_length):
			if self.log_en:
				F_axis.append(math.floor(F_axis[k-1] * (self.sweep_freq_delta / _NA_FXP_SCALE)) + F_axis[k-1])
			else :
				F_axis.append(F_axis[k-1] + self.sweep_freq_delta)

		freq_axis = [(x/_NA_FREQ_SCALE) for x in F_axis]

		# Dubyeu tee eff mate?
		if self.sweep_length <= 510 :
			freq_axis = [1, 1] + freq_axis[1: -1]

		return freq_axis

	def _calculate_gain_correction(self):
		sweep_freq = self._calculate_freq_axis()

		cycles_time = [0.0] * self.sweep_length

		if all(sweep_freq):
			cycles_time = [ self.averaging_cycles / sweep_freq[n] for n in range(self.sweep_length)]

		points_per_freq = [math.ceil(a * max(self.averaging_time, b) - 1e-12) for (a, b) in zip(sweep_freq, cycles_time)]

		average_gain = [0.0] * self.sweep_length
		gain_scale = [0.0] * self.sweep_length

		#Calculate gain scaling due to accumulator bit ranging
		for f in range(self.sweep_length):
			sweep_period = 1 / sweep_freq[f]

			# Predict how many FPGA clock cycles each frequency averages for:
			average_period_cycles = self.averaging_cycles * sweep_period * 125e6
			if self.averaging_time % sweep_period == 0:
				average_period_time = self.averaging_time * 125e6
			else :
				average_period_time = math.ceil(self.averaging_time / sweep_period) * sweep_period * 125e6

			if average_period_time >= average_period_cycles:
				average_period = average_period_time
			else :
				average_period = average_period_cycles

			# Scale according to the predicted accumulator counter size:
			if average_period <= 2**16:
				average_gain[f] = 2**4
			elif average_period <= 2**21:
				average_gain[f] = 2**-1
			elif average_period <= 2**26:
				average_gain[f] = 2**-6
			elif average_period <= 2**31:
				average_gain[f] = 2**-11
			elif average_period <= 2**36:
				average_gain[f] = 2**-16
			else :
				average_gain[f] = 2**-20

		for f in range(self.sweep_length):
			if sweep_freq[f] > 0.0 :
				gain_scale[f] =  math.ceil(average_gain[f]*points_per_freq[f]*(_NA_FPGA_CLOCK/sweep_freq[f]))
			else :
				gain_scale[f] = average_gain[f]

		return gain_scale

	def set_channel_enable(self, channel, en=True):
		if channel == 1 :
			self.channel1_en = en
		elif channel == 2:
			self.channel2_en = en

	def set_defaults(self):
		super(NetAn, self).set_defaults()

		self.framerate = _NA_FPS
		self.frame_length = _NA_SCREEN_WIDTH

		self.en_in_ch1 = True
		self.en_in_ch2 = True

		self.set_frontend(1, True, False, False)
		self.set_frontend(2, True, False, False)

		self.x_mode = SWEEP
		self.render_mode = RDR_DDS

	def _calculate_scales(self):
		g1, g2 = self.adc_gains()

		return {'g1': g1, 'g2': g2,
				'gain_correction' : self._calculate_gain_correction(),
				'frequency_axis' : self._calculate_freq_axis(),
				'sweep_freq_min': self.sweep_freq_min,
				'sweep_freq_delta': self.sweep_freq_delta,
				'sweep_length': self.sweep_length,
				'log_en': self.log_en,
				'averaging_time': self.averaging_time,
				'sweep_amplitude_ch1' : self.sweep_amp_volts_ch1,
				'sweep_amplitude_ch2' : self.sweep_amp_volts_ch2,
				'reference_ch1' : self.reference_ch1,
				'reference_ch2' : self.reference_ch2,
				}



_na_reg_handlers = {
	'loop_sweep':				(REG_NA_ENABLES,
											to_reg_bool(0),
											from_reg_bool(0)),
	'single_sweep':				(REG_NA_ENABLES,
											to_reg_bool(1),
											from_reg_bool(1)),
	'sweep_reset':				(REG_NA_ENABLES,
											to_reg_bool(2),
											from_reg_bool(2)),
	'channel1_en':				(REG_NA_ENABLES,
											to_reg_bool(3),
											from_reg_bool(3)),
	'channel2_en':				(REG_NA_ENABLES,
											to_reg_bool(4),
											from_reg_bool(4)),
	'sweep_freq_min':			((REG_NA_SWEEP_FREQ_MIN_H, REG_NA_SWEEP_FREQ_MIN_L),
											to_reg_unsigned(0, 48, xform=lambda obj, f: f * _NA_FREQ_SCALE),
											from_reg_unsigned(0, 48, xform=lambda obj, f: f / _NA_FREQ_SCALE)),
	'sweep_freq_delta':			((REG_NA_SWEEP_FREQ_DELTA_H, REG_NA_SWEEP_FREQ_DELTA_L),
											to_reg_signed(0, 48),
											from_reg_signed(0, 48)),
	'log_en':					(REG_NA_LOG_EN,
											to_reg_bool(0),
											from_reg_bool(0)),

	'sweep_length':				(REG_NA_SWEEP_LENGTH,
											to_reg_unsigned(0, 10),
											from_reg_unsigned(0, 10)),
	'settling_time':			(REG_NA_HOLD_OFF_L,
											to_reg_unsigned(0, 32, xform=lambda obj, t: t * _NA_FPGA_CLOCK),
											from_reg_unsigned(0, 32, xform=lambda obj, t: t / _NA_FPGA_CLOCK)),
	'averaging_time':			(REG_NA_AVERAGE_TIME,
											to_reg_unsigned(0, 32, xform=lambda obj, t: t * _NA_FPGA_CLOCK),
											from_reg_unsigned(0, 32, xform=lambda obj, t: t / _NA_FPGA_CLOCK)),
	'sweep_amplitude_ch1':		(REG_NA_SWEEP_AMP_MULT,
											to_reg_unsigned(0, 16, xform=lambda obj, a: a / obj.dac_gains()[0]),
											from_reg_unsigned(0, 16, xform=lambda obj, a: a * obj.dac_gains()[0])),
	'sweep_amplitude_ch2':		(REG_NA_SWEEP_AMP_MULT,
											to_reg_unsigned(16, 16, xform=lambda obj, a: a / obj.dac_gains()[1]),
											from_reg_unsigned(16, 16, xform=lambda obj, a: a * obj.dac_gains()[1])),
	'settling_cycles':			(REG_NA_SETTLE_CYCLES,
											to_reg_unsigned(0, 32),
											from_reg_unsigned(0, 32)),
	'averaging_cycles':			(REG_NA_AVERAGE_CYCLES,
											to_reg_unsigned(0, 32),
											from_reg_unsigned(0, 32)),
	}
