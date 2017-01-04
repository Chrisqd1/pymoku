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
# REG_NA_HOLD_OFF_H			= 70
REG_NA_SWEEP_LENGTH			= 71
REG_NA_AVERAGE_TIME			= 72
REG_NA_SINGLE_SWEEP			= 73
REG_NA_SWEEP_AMP_MULT		= 74
REG_NA_SETTLE_CYCLES		= 76
REG_NA_AVERAGE_CYCLES		= 77


_NA_ADC_SMPS		= 500e6
_NA_FPGA_CLOCK 		= 125e6
_NA_DAC_SMPS 		= 1e9
_NA_DAC_VRANGE 		= 2
_NA_DAC_BITDEPTH 	= 2**16
_NA_DAC_V2BITS 		= _NA_DAC_BITDEPTH/_NA_DAC_VRANGE
_NA_BUFLEN			= 2**14
_NA_SCREEN_WIDTH	= 1024
_NA_SCREEN_STEPS	= _NA_SCREEN_WIDTH - 1
_NA_FPS				= 2
_NA_FREQ_SCALE		= 2**48 / _NA_DAC_SMPS
_NA_INT_VOLTS_SCALE = (1.437*pow(2.0,-8.0))
_NA_FXP_SCALE 		= 2.0**31

'''
	Plotting helper functions
'''
def calculate_freq_axis(start_freq, freq_step, sweep_length, log_scale):
	# generates the frequency vector for plotting. The logarithmic scale is calculated on the FPGA with fixed point precision,
	# hence the forced fxp calculation when log_scale = True.

	F_start = start_freq*_NA_FREQ_SCALE
	F_axis = [F_start]
	freq_axis = [start_freq]

	for k in range(1, sweep_length) :
		if log_scale:
			F_axis.append(math.floor(F_axis[k-1] * (freq_step + _NA_FXP_SCALE)/_NA_FXP_SCALE))
		else :
			freq_axis.append(freq_axis[k-1] + (freq_step/_NA_FREQ_SCALE))

	if log_scale:
		freq_axis = [(x/_NA_FREQ_SCALE) for x in F_axis]

	# print 'FREQUENCY CALCULATION: ', freq_axis
	# print 'F_fpga', F_start
	return freq_axis

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
	class _NetAnChannel():
		# convert an RMS voltage to a power level (assuming 50 Ohm load)
		def _mag_to_db(self, v):
			if v == None :
				return None
			elif v <= 0 :
				return None
			else :
				return 20.0*math.log10( v / 20.0)

		def _calculate_magnitude(self, i_signal, q_signal, dbscale):
			if i_signal == None or q_signal == None:
				return None
			elif dbscale:
				return self._mag_to_db(math.sqrt(i_signal**2 + q_signal**2))
			else:
				return math.sqrt(i_signal**2 + q_signal**2)

		def _calculate_phase(self, i_signal, q_signal):
			if i_signal == None or q_signal == None:
				return None
			else:
				return math.atan2(i_signal, q_signal)

		def _generate_signals(self, input_signal, dbscale):
			self.i_sig = [ input_signal[x] for x in range(0,len(input_signal ), 2 ) ]
			self.q_sig = [ input_signal[x] for x in range(1,len(input_signal ), 2 ) ]
	
			self.magnitude =  [ self._calculate_magnitude(self.i_sig[x], self.q_sig[x], dbscale) for x in range(len(self.q_sig)) ] #self._calculate_magnitude( self.i_sig[x], self.q_sig[x] )
			self.phase = [ self._calculate_phase(self.i_sig[x], self.q_sig[x]) for x in range(len(self.q_sig)) ]

		i_sig = []
		q_sig = []
		magnitude = []
		phase = []

	def __init__(self, scales):
		super(NetAnFrame, self).__init__()

		#: Channel 1 data array in units of power. Present whether or not the channel is enabled, but the
		#: contents are undefined in the latter case.
		self.ch1 = self._NetAnChannel()

		#: Channel 2 data array in units of power.
		self.ch2 = self._NetAnChannel()

		#: The frequency range associated with both channels
		self.fs = []

		#: Obtain all data scaling factors relevant to current NetAn configuration
		self.scales = scales

	def __json__(self):
		return { 'ch1' : self.ch1, 'ch2' : self.ch2, 'fs' : self.fs }

	def process_complete(self):

		if self.stateid not in self.scales:
			log.error("Can't render NetAn frame, haven't saved calibration data for state %d", self.stateid)

			smpls = int(len(self.raw1) / 4)
			dat = struct.unpack('<' + 'i' * smpls, self.raw1)
			dat = [ x if x != -0x80000000 else None for x in dat ]

			# print dat
			return

		# Get scaling/correction factors based on current instrument configuration
		scales = self.scales[self.stateid]
		scale1 = scales['g1']
		scale2 = scales['g2']
		# fs = scales['fs']
		# f1, f2 = scales['fspan']
		# fcorrs = scales['fcorrs']
		dbscale = scales['dbscale']

		try:
			# Find the starting index for the valid frame data
			# NetAn generally gives more than we ask for due to integer decimations
			# start_index = bisect_right(fs,f1)

			# Set the frequency range of valid data in the current frame (same for both channels)
			self.ch1_fs = calculate_freq_axis( scales['sweep_freq_min'], scales['sweep_freq_delta'], scales['sweep_length'], scales['log_en'] )
			self.ch2_fs = calculate_freq_axis( scales['sweep_freq_min'], scales['sweep_freq_delta'], scales['sweep_length'], scales['log_en'] )

			##################################
			# Process Ch1 Data
			##################################
			smpls = int(len(self.raw1) / 4)
			dat = struct.unpack('<' + 'i' * smpls, self.raw1)
			dat = [ x if x != -0x80000000 else None for x in dat ]

			# NetAn data is backwards because $(EXPLETIVE), also remove zeros for the sake of common
			# display on a log axis.
			self.ch1_bits = [ float(x) if x is not None else None for x in dat[:1024] ]
			print self.ch1_bits[100]
			#self.ch1.i_sig = [ self.ch1_bits[x] for x in range(0,len(self.ch1_bits ), 2 ) ]
			#self.ch1.q_sig = [ self.ch1_bits[x] for x in range(1,len(self.ch1_bits ), 2 ) ]
			#self.ch1.magnitude = [ self.ch1._calculate_magnitude(self.ch1.i_sig[x], self.ch1.q_sig[x]) for x in range(len(self.ch1.i_sig)) ] #[ math.sqrt(self.ch1.i_sig[x]**2 + self.ch1.q_sig[x]**2) for x in range(len(self.ch1.i_sig))]
			self.ch1._generate_signals(self.ch1_bits, dbscale)
		
			self.ch1.magnitude = self.gain_correction(self.ch1.magnitude,scales['sweep_freq_delta'], scales['sweep_freq_min'], scales['sweep_length'], scales['averaging_time'], scales['log_en'])

			# print self.ch1_bits
			# Apply frequency dependent corrections
			# self.ch1 = [ self._vrms_to_dbm(a*c*scale1) if dbmscale else a*c*scale1 if a is not None else None for a,c in zip(self.ch1_bits, fcorrs)]

			# Trim invalid part of frame
			# self.ch1 = self.ch1[start_index:-1]

			##################################
			# Process Ch2 Data
			##################################
			smpls = int(len(self.raw2) / 4)
			dat = struct.unpack('<' + 'i' * smpls, self.raw2)
			dat = [ x if x != -0x80000000 else None for x in dat ]

			self.ch2_bits = [ float(x) if x is not None else None for x in dat[:1024] ]

			# self.ch2._generate_signals(self.ch2_bits)

			# self.ch2 = [ self._vrms_to_dbm(a*c*scale2) if dbmscale else a*c*scale2 if a is not None else None for a,c in zip(self.ch2_bits, fcorrs)]
			# self.ch2 = self.ch2[start_index:-1]

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
		dbm = scales['dbscale']

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

	def gain_correction(self, magnitude, sweep_freq_delta, sweep_freq_min, sweep_points, averaging_time, log_scale):
		 
		sweep_freq = calculate_freq_axis(sweep_freq_min, sweep_freq_delta, sweep_points, log_scale)
		
		points_per_freq = [math.ceil(f*averaging_time) for f in sweep_freq]

		gain_scale = [0.0]*sweep_points
		scaled_magnitude = [0.0]*sweep_points

		for f in range(sweep_points) :
			if sweep_freq[f] > 0.0 :
				gain_scale[f] =  math.ceil(points_per_freq[f]*(_NA_FPGA_CLOCK/sweep_freq[f]))
			else :
				gain_scale[f] = 1.0

			if magnitude[f] == None :
				scaled_magnitude[f] = None
			else :
				scaled_magnitude[f] = magnitude[f]/gain_scale[f] 

		print 'Gain scale: ', gain_scale
		return scaled_magnitude


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

		self.set_dbscale(True)


	def commit(self):
		# Compute remaining control register values based on window, rbw and fspan
		#self._setup_controls()

		# Push the controls through to the device
		super(NetAn, self).commit()

		# Update the scaling factors for processing of incoming frames
		# stateid allows us to track which scales correspond to which register state
		self.scales[self._stateid] = self._calculate_scales()

		# TODO: Trim scales dictionary, getting rid of old ids

	# Bring in the docstring from the superclass for our docco.
	commit.__doc__ = MokuInstrument.commit.__doc__


	def set_sweep_parameters(self, start_frequency=1.0e3, end_frequency=1.0e6, sweep_length=512, log_scale=False, sweep_amplitude_ch1=0.5, sweep_amplitude_ch2=0.5, averaging_time=1e-6, settling_time=1e-6, averaging_cycles=0, settling_cycles=0):
		self.sweep_freq_min = start_frequency
		self.sweep_length = sweep_length
		self.log_en = log_scale
		self.sweep_amplitude_ch1 = sweep_amplitude_ch1 * self._get_dac_calibration()[0]
		self.sweep_amplitude_ch2 = sweep_amplitude_ch2 * self._get_dac_calibration()[1]
		self.averaging_time = averaging_time
		self.averaging_cycles = averaging_cycles
		self.settling_time = settling_time
		self.settling_cycles = settling_cycles
		

		if log_scale:
			print ((float(end_frequency) / float(start_frequency))**(1.0/(sweep_length - 1)) - 1)
			self.sweep_freq_delta = round(((float(end_frequency) / float(start_frequency))**(1.0/(sweep_length - 1)) - 1) * _NA_FXP_SCALE)
		else:
			print ((end_frequency - start_frequency)/(sweep_length-1)) 
			self.sweep_freq_delta = ((end_frequency - start_frequency)/(sweep_length-1)) * _NA_FREQ_SCALE
			

	def set_sweep_freq_delta(self, start_freq, stop_freq, sweep_length, log_scale):
		if log_scale:
			freq_delta = ((float(end_frequency) / float(start_frequency))**(1.0/(sweep_length - 1)) - 1)
			self.sweep_freq_delta = round(((float(end_frequency) / float(start_frequency))**(1.0/(sweep_length - 1)) - 1) * _NA_FXP_SCALE)
		else:
			freq_delta = ((end_frequency - start_frequency)/(sweep_length-1)) 
			self.sweep_freq_delta = round((end_frequency - start_frequency)/(sweep_length-1)) * _NA_FREQ_SCALE

		return freq_delta
		print 'Calculated frequency delta: ', freq_delta

	def get_sweep_freq_delta(self):

		if self.log_en:
			return float(self.sweep_freq_delta) / _NA_FXP_SCALE + 1
		else:
			return float(self.sweep_freq_delta) / _NA_FREQ_SCALE

	def set_xmode(self, xmode):
		self.x_mode = xmode

	def set_defaults(self):
		super(NetAn, self).set_defaults()

		self.framerate = _NA_FPS
		self.frame_length = _NA_SCREEN_WIDTH

		self.sweep_freq_min = 1

		self.en_in_ch1 = True
		self.en_in_ch2 = True

		self.calibration = None
		self.set_xmode(FULL_FRAME)

		self.set_frontend(0, True, True, False)
		self.set_frontend(1, True, True, False)

		self.log_en = False
		self.sweep_length = 512
		self.sweep_amp_mult = 1
		self.offset = 0
		self.averaging_time = 0.1 
		self.single_sweep = 0
		self.render_mode = RDR_DDS

	def set_start_freq(self, start_freq):
		self.sweep_freq_min = start_freq

	def get_sweep_freq_min(self) :
		return float(self.sweep_freq_min)

	def set_stop_freq(self, stop_freq):
		self.stop_freq = stop_freq

	def set_sweep_length(self, sweep_length):
		self.sweep_length = sweep_length

	def _calculate_scales(self):	

		"""
			Returns per-channel correction and scaling parameters required for interpretation of incoming bit frames
			Parameters are based on current instrument state
		"""
		# Returns the bits-to-volts numbers for each channel in the current state

		# TODO: Centralise the calibration parsing, shared with Oscilloscope

		sect1 = "calibration.AG-%s-%s-%s-1" % ( "50" if self.relays_ch1 & RELAY_LOWZ else "1M",
								  "L" if self.relays_ch1 & RELAY_LOWG else "H",
								  "D" if self.relays_ch1 & RELAY_DC else "A")

		sect2 = "calibration.AG-%s-%s-%s-1" % ( "50" if self.relays_ch2 & RELAY_LOWZ else "1M",
								  "L" if self.relays_ch2 & RELAY_LOWG else "H",
								  "D" if self.relays_ch2 & RELAY_DC else "A")

		# Compute per-channel constant scaling factors
		try:
			g1 = 1 #/ float(self.calibration[sect1])
			g2 = 1 #/ float(self.calibration[sect2])
		except KeyError:
			log.warning("Moku appears uncalibrated")
			g1 = g2 = 1

		return {'g1': g1, 'g2': g2, 'dbscale': self.dbscale, 'sweep_freq_min': self.sweep_freq_min, 'sweep_freq_delta': self.sweep_freq_delta, 'sweep_length': self.sweep_length, 'log_en': self.log_en, 'averaging_time': self.averaging_time}


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


	def set_dbscale(self,dbm=True):
		self.dbscale = dbm

	def attach_moku(self, moku):
		super(NetAn, self).attach_moku(moku)

		# The moku contains calibration data for various configurations
		self.calibration = dict(self._moku._get_property_section("calibration"))

	attach_moku.__doc__ = MokuInstrument.attach_moku.__doc__

_na_reg_handlers = {
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
	'settling_time':			((REG_NA_HOLD_OFF_L),
											to_reg_unsigned(0, 32, xform=lambda obj, t: t * _NA_FPGA_CLOCK),
											from_reg_unsigned(0, 32, xform=lambda obj, t: t / _NA_FPGA_CLOCK)),
	'averaging_time':			(REG_NA_AVERAGE_TIME,
											to_reg_unsigned(0, 32, xform=lambda obj, t: t * _NA_FPGA_CLOCK),
											from_reg_unsigned(0, 32, xform=lambda obj, t: t / _NA_FPGA_CLOCK)),
	'single_sweep':				(REG_NA_SINGLE_SWEEP,
											to_reg_unsigned(0, 1),
											from_reg_unsigned(0, 1)),
	'sweep_amplitude_ch1':		(REG_NA_SWEEP_AMP_MULT,		
											to_reg_unsigned(0, 16, xform=lambda obj, a: a * _NA_DAC_V2BITS),
											from_reg_unsigned(0, 16, xform=lambda obj, a: a / _NA_DAC_V2BITS)),
	'sweep_amplitude_ch2':		(REG_NA_SWEEP_AMP_MULT,
											to_reg_unsigned(16, 16, xform=lambda obj, a: a * _NA_DAC_V2BITS),
											from_reg_unsigned(16, 16, xform=lambda obj, a: a / _NA_DAC_V2BITS)),
	'settling_cycles':			(REG_NA_SETTLE_CYCLES,
											to_reg_unsigned(0, 32),
											from_reg_unsigned(0, 32)),
	'averaging_cycles':			(REG_NA_AVERAGE_CYCLES,
											to_reg_unsigned(0, 32),
											from_reg_unsigned(0, 32)),
}
