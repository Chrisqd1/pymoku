import math
import logging

from ._instrument import *
from . import _frame_instrument

from bisect import bisect_right

log = logging.getLogger(__name__)

REG_NA_SWEEP_FREQ_MIN_L 	= 64
REG_NA_SWEEP_FREQ_MIN_H 	= 65
REG_NA_SWEEP_FREQ_DELTA_L 	= 66
REG_NA_SWEEP_FREQ_DELTA_H 	= 67
REG_NA_LOG_EN				= 68
REG_NA_HOLD_OFF_L			= 69
REG_NA_HOLD_OFF_H			= 70
REG_NA_SWEEP_LENGTH			= 71
REG_NA_SWEEP_AMP_BITSHIFT	= 72
REG_NA_SWEEP_AMP_MULT		= 73


_NA_ADC_SMPS		= 500e6
_NA_DAC_SMPS		= 1e9
_NA_BUFLEN			= 2**14
_NA_SCREEN_WIDTH	= 1024
_NA_SCREEN_STEPS	= _NA_SCREEN_WIDTH - 1
_NA_FPS				= 2
_NA_FREQ_SCALE		= 2**48 / _NA_DAC_SMPS
_NA_INT_VOLTS_SCALE = (1.437*pow(2.0,-8.0))


class NetAnFrame(_frame_instrument.DataFrame):
	"""
	Object representing a frame of data in units of power vs frequency. This is the native output format of
	the :any:`NetAn` instrument and similar.

	This object should not be instantiated directly, but will be returned by a supporting *get_frame*
	implementation.

	.. autoinstanceattribute:: pymoku._frame_instrument.SpectrumFrame.ch1
		:annotation: = [CH1_DATA]

	.. autoinstanceattribute:: pymoku._frame_instrument.SpectrumFrame.ch2
		:annotation: = [CH2_DATA]

	.. autoinstanceattribute:: pymoku._frame_instrument.SpectrumFrame.fs
		:annotation: = [FREQ]

	.. autoinstanceattribute:: pymoku._frame_instrument.SpectrumFrame.frameid
		:annotation: = n

	.. autoinstanceattribute:: pymoku._frame_instrument.SpectrumFrame.waveformid
		:annotation: = n
	"""
	def __init__(self, scales):
		super(NetAnFrame, self).__init__()

		#: Channel 1 data array in units of power. Present whether or not the channel is enabled, but the
		#: contents are undefined in the latter case.
		self.ch1 = []

		#: Channel 2 data array in units of power.
		self.ch2 = []

		#: The frequency range associated with both channels
		self.fs = []

		#: Obtain all data scaling factors relevant to current NetAn configuration
		self.scales = scales

	def __json__(self):
		return { 'ch1' : self.ch1, 'ch2' : self.ch2, 'fs' : self.fs }

	# convert an RMS voltage to a power level (assuming 50Ohm load)
	def _vrms_to_dbm(self, v):
		return 10.0*math.log(v*v/50.0,10) + 30.0

	def process_complete(self):

		if self.stateid not in self.scales:
			log.error("Can't render NetAn frame, haven't saved calibration data for state %d", self.stateid)
			return

		# Get scaling/correction factors based on current instrument configuration
		scales = self.scales[self.stateid]
		scale1 = scales['g1']
		scale2 = scales['g2']
		fs = scales['fs']
		f1, f2 = scales['fspan']
		fcorrs = scales['fcorrs']
		dbmscale = scales['dbmscale']

		try:
			# Find the starting index for the valid frame data
			# NetAn generally gives more than we ask for due to integer decimations
			start_index = bisect_right(fs,f1)

			# Set the frequency range of valid data in the current frame (same for both channels)
			self.ch1_fs = fs[start_index:-1]
			self.ch2_fs = fs[start_index:-1]

			##################################
			# Process Ch1 Data
			##################################
			smpls = int(len(self.raw1) / 4)
			dat = struct.unpack('<' + 'i' * smpls, self.raw1)
			dat = [ x if x != -0x80000000 else None for x in dat ]

			# NetAn data is backwards because $(EXPLETIVE), also remove zeros for the sake of common
			# display on a log axis.
			self.ch1_bits = [ max(float(x), 1) if x is not None else None for x in reversed(dat[:_SA_SCREEN_WIDTH]) ]

			# Apply frequency dependent corrections
			self.ch1 = [ self._vrms_to_dbm(a*c*scale1) if dbmscale else a*c*scale1 if a is not None else None for a,c in zip(self.ch1_bits, fcorrs)]

			# Trim invalid part of frame
			self.ch1 = self.ch1[start_index:-1]

			##################################
			# Process Ch2 Data
			##################################
			smpls = int(len(self.raw2) / 4)
			dat = struct.unpack('<' + 'i' * smpls, self.raw2)
			dat = [ x if x != -0x80000000 else None for x in dat ]

			self.ch2_bits = [ max(float(x), 1) if x is not None else None for x in reversed(dat[:_SA_SCREEN_WIDTH]) ]

			self.ch2 = [ self._vrms_to_dbm(a*c*scale2) if dbmscale else a*c*scale2 if a is not None else None for a,c in zip(self.ch2_bits, fcorrs)]
			self.ch2 = self.ch2[start_index:-1]

		except (IndexError, TypeError, struct.error):
			# If the data is bollocksed, force a reinitialisation on next packet
			log.exception("NetAn packet")
			self.frameid = None
			self.complete = False

		# A valid frame is there's at least one valid sample in each channel
		return any(self.ch1) and any(self.ch2)

	'''
		Plotting helper functions
	'''
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

		return [scale_str,scale_const]

	def _get_xaxis_fmt(self,x,pos):
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

	def _get_yaxis_fmt(self,y,pos):

		if self.stateid not in self.scales:
			log.error("Can't get current frequency format, haven't saved calibration data for state %d", self.stateid)
			return

		scales = self.scales[self.stateid]
		dbm = scales['dbmscale']

		yfmt = {
			'linear' : '%.1f %s' % (y,'V'),
			'log' : '%.1f %s' % (y,'dBm')
		}
		ycoord = {
			'linear' : '%.3f %s' % (y,'V'),
			'log' : '%.3f %s' % (y,'dBm')
		}

		return {'yaxis': (yfmt['log'] if dbm else yfmt['linear']), 'ycoord': (ycoord['log'] if dbm else ycoord['linear'])}

	def get_yaxis_fmt(self, y, pos):
		return self._get_yaxis_fmt(y,pos)['yaxis']

	def get_ycoord_fmt(self, y):
		return self._get_yaxis_fmt(y,None)['ycoord']


class NetAn(_frame_instrument.FrameBasedInstrument):
	""" Network Analyser instrument object. This should be instantiated and attached to a :any:`Moku` instance.

	.. automethod:: pymoku.instruments.NetAn.__init__

	.. attribute:: hwver

		Hardware Version

	.. attribute:: hwserial

		Hardware Serial Number

	.. attribute:: framerate
		:annotation: = 9

		Frame Rate, range 1 - 30.

	.. attribute:: type
		:annotation: = "NetAn"

		Name of this instrument.

	"""
	def __init__(self):
		"""Create a new Spectrum Analyser instrument, ready to be attached to a Moku."""
		super(NetAn, self).__init__()
		self._register_accessors(_na_reg_handlers)

		self.scales = {}
		self.set_frame_class(NetAnFrame, scales=self.scales)

		self.id = 9
		self.type = "NetAn"
		self.calibration = None

		# self.set_dbmscale(True)


	def commit(self):
		# Compute remaining control register values based on window, rbw and fspan
		# self._setup_controls()

		# Push the controls through to the device
		super(NetAn, self).commit()

		# Update the scaling factors for processing of incoming frames
		# stateid allows us to track which scales correspond to which register state
		# self.scales[self._stateid] = self._calculate_scales()

		# TODO: Trim scales dictionary, getting rid of old ids

	# Bring in the docstring from the superclass for our docco.
	commit.__doc__ = MokuInstrument.commit.__doc__

	def set_defaults(self):
		super(NetAn, self).set_defaults()

		self.calibration = None

		self.set_frontend(0, True, True, False)
		self.set_frontend(1, True, True, False)
		self.sweep_freq_min = 1
		self.sweep_freq_delta = 1
		self.log_en = True
		self.hold_off_time = 125
		self.sweep_length = 126
		self.sweep_amp_bitshift = 0
		self.sweep_amp_mult = 1



	def attach_moku(self, moku):
		super(NetAn, self).attach_moku(moku)

		# The moku contains calibration data for various configurations
		self.calibration = dict(self._moku._get_property_section("calibration"))

	attach_moku.__doc__ = MokuInstrument.attach_moku.__doc__

_na_reg_handlers = {
	'sweep_freq_min':			((REG_NA_SWEEP_FREQ_MIN_H, REG_NA_SWEEP_FREQ_MIN_L),
											to_reg_unsigned(0, 48, xform=lambda f: f * _NA_FREQ_SCALE),
											from_reg_unsigned(0, 48, xform=lambda f: f / _NA_FREQ_SCALE)),
	'sweep_freq_delta':			((REG_NA_SWEEP_FREQ_DELTA_H, REG_NA_SWEEP_FREQ_DELTA_L),		
											to_reg_unsigned(0, 48, xform=lambda f : f * _NA_FREQ_SCALE),
											from_reg_unsigned(0, 48, xform=lambda f : f * _NA_FREQ_SCALE)),
	'log_en':					(REG_NA_LOG_EN,
											to_reg_bool(0),		
											from_reg_bool(0)),
	'hold_off_time':			((REG_NA_HOLD_OFF_H, REG_NA_HOLD_OFF_L),
											to_reg_unsigned(0, 48),
											from_reg_unsigned(0, 48)),
	'sweep_length':				(REG_NA_SWEEP_LENGTH,		
											to_reg_unsigned(0, 10),
											from_reg_unsigned(0, 10)),
	'sweep_amp_bitshift':		(REG_NA_SWEEP_AMP_BITSHIFT,		
											to_reg_unsigned(0, 17),		
											from_reg_unsigned(0, 17)),
	'sweep_amp_mult':			(REG_NA_SWEEP_AMP_MULT,		
											to_reg_unsigned(0, 17),
											from_reg_unsigned(0, 17)),
}
