import itertools
import pytest, time
from pymoku import Moku, FrameTimeout
from pymoku.instruments import *
from pymoku._oscilloscope import _OSC_SCREEN_WIDTH, _OSC_ADC_SMPS, OSC_TRIG_NORMAL, OSC_TRIG_SINGLE, OSC_TRIG_AUTO
from pymoku._siggen import SG_MOD_NONE, SG_MOD_AMPL, SG_MOD_PHASE, SG_MOD_FREQ, SG_MODSOURCE_INT, SG_MODSOURCE_ADC, SG_MODSOURCE_DAC, SG_WAVE_SINE, SG_WAVE_SQUARE, SG_WAVE_TRIANGLE, SG_WAVE_DC
import conftest
import numpy, math
import scipy.signal
import matplotlib.pyplot as plt
from functools import partial

OSC_MAX_TRIGRATE = 8e3 #Approximately 8kHz
OSC_AUTO_TRIGRATE = 20

# WAVEFORM TOLERANCES
# _P - Percentage
# _R - Relative
ADC_OFF_TOL_R = 0.100 # Volts
ADC_AMP_TOL_P = 0.05
ADC_AMP_TOL_R = 0.03
DAC_DUTY_TOL_R = 0.05
PHASE_TOL_R = 0.02

# Threshold bounds
MAX_RMS_ERROR_SQUARE = 0.15
MAX_RMS_ERROR_SINE = 0.07
MAX_RMS_ERROR_TRIANGLE = 0.13

AC_COUPLE_CORNER_FREQ_1MO = 50
AC_COUPLE_CORNER_FREQ_50O = 1e6

FRAME_TIMEOUT = 5 # seconds

DEBUG_TESTS = True

# Assertion helpers
def in_bounds(v, center, err):
	if (v is None) or (center is None):
		return True
	return abs(v - center) <= abs(err)

def _calculate_rms_error(frame1, frame2):
	return numpy.sqrt(numpy.sum((numpy.array(frame1-frame2)**2))/len(frame1))

def in_rms_bounds(frame1, frame2, waveform, scale):
	rms_error = _calculate_rms_error(numpy.array(frame1)/float(scale), numpy.array(frame2)/float(scale))

	if waveform == SG_WAVE_SINE:
		print "RMS Error (SINE): %f/%f" % (rms_error,MAX_RMS_ERROR_SINE)
		return rms_error < MAX_RMS_ERROR_SINE
	elif waveform == SG_WAVE_TRIANGLE:
		print "RMS Error (TRIANGLE): %f/%f" % (rms_error,MAX_RMS_ERROR_TRIANGLE)
		return rms_error < MAX_RMS_ERROR_TRIANGLE
	elif waveform == SG_WAVE_SQUARE:
		print "RMS Error (SQUARE): %f/%f" % (rms_error,MAX_RMS_ERROR_SQUARE)
		return rms_error < MAX_RMS_ERROR_SQUARE
	else:
		print "Invalid waveform type"
		return False

def _is_rising(p1,p2):
	if (p1 is None) or (p2 is None):
		return True
	if (p2-p1) > 0:
		return True
	else:
		return False

def _is_falling(p1,p2):
	if (p1 is None) or (p2 is None):
		return True
	if (p2-p1) < 0:
		return True
	else:
		return False

def zero_crossings(a):
	return numpy.where(numpy.diff(numpy.sign(a)))[0]

def _sinewave(t,ampl,ph,off,freq):
	# Taken from commissioning/calibration.py
	return off+ampl*numpy.sin(2*numpy.pi*freq*t+ph)
	#return numpy.array([off+ampl*math.sin(2*math.pi*freq*x+ph) for x in t])

def _sawtooth(t, ampl, phase, offset, freq, width):
	return scipy.signal.sawtooth(freq*(2.0*numpy.pi)*t + phase , width=width)*ampl + offset

def _squarewave(t, ampl, phase, offset, freq, duty):
	return scipy.signal.square(freq*(2.0*numpy.pi)*t + phase, duty=duty)*ampl + offset

# Helper function to compute the timestep per sample of a frame
def _get_frame_timesteps(moku, length):
	ts = moku._calculate_frame_timestep(moku.decimation_rate, moku.render_deci)
	start_t = moku._calculate_frame_start_time(moku.decimation_rate, moku.render_deci, moku.offset)
	return numpy.cumsum([ts]*length) - ts + start_t

def _crop_frame_of_nones(frame):
	if None in frame:
		return frame[0:frame.index(None)]
	return frame


@pytest.fixture(scope="module")
def base_instrs(conn_mokus):
	m1 = conn_mokus[0]
	m2 = conn_mokus[1]
	print("Attaching instruments")

	i1 = Oscilloscope()
	i2 = Oscilloscope()

	m1.attach_instrument(i1, use_external=False) # Master is 10MHz reference clock
	m2.attach_instrument(i2, use_external=False)

	i1.set_defaults()
	i2.set_defaults()

	# Set precision mode
	i1.set_precision_mode(True)
	i2.set_precision_mode(True)

	i1.commit()
	i2.commit()

	return (i1,i2)

class Test_Siggen:
	def _calculate_triangle_phase(symmetry):
		return symmetry * numpy.pi

	'''
		This class tests the correctness of the embedded signal generator 
	'''
	@pytest.mark.parametrize("ch, vpp, freq, offset, duty, waveform", 
		itertools.product(
			[1,2],
			[0.3, 0.7],
			[50, 1e3, 900e3], 
			[0.1, 0.0, -0.1], 
			[0.2, 0.5, 0.95],
			[SG_WAVE_SINE, SG_WAVE_SQUARE, SG_WAVE_TRIANGLE]
			))
	def test_output_waveform(self, base_instrs, ch, vpp, freq, offset, duty, waveform):
		# Check input parameters
		assert (offset + 0.5*vpp) <= 1.0
		assert (offset - 0.5*vpp) >= -1.0

		master = base_instrs[0]
		slave = base_instrs[1]

		timebase_cyc = 10.0
		slave.set_timebase(0, timebase_cyc/freq)
		slave.set_source(ch, OSC_SOURCE_ADC)
		slave.set_frontend(ch, fiftyr=True, atten=False, ac=False)

		if ch == 1:
			slave.set_trigger(OSC_TRIG_CH1, OSC_EDGE_RISING, offset, mode = OSC_TRIG_NORMAL, hysteresis = 100,)
		else:
			slave.set_trigger(OSC_TRIG_CH2, OSC_EDGE_RISING, offset, mode = OSC_TRIG_NORMAL, hysteresis = 100, )

		if waveform == SG_WAVE_SINE:
			master.synth_sinewave(ch, vpp, freq, offset)
		elif waveform == SG_WAVE_SQUARE:
			master.synth_squarewave(ch, vpp, freq, offset=offset, duty = duty)
		elif waveform == SG_WAVE_TRIANGLE:
			master.synth_rampwave(ch, vpp, freq, offset=offset, symmetry = duty)
		else:
			print "Invalid waveform type."
			assert False

		master.commit()
		slave.commit()
		slave.get_frame(timeout = FRAME_TIMEOUT) # Throwaway
		slave.get_frame(timeout = FRAME_TIMEOUT)
		if ch == 1:
			frame = slave.get_frame(timeout = FRAME_TIMEOUT).ch1
		else:
			frame = slave.get_frame(timeout = FRAME_TIMEOUT).ch2
		frame = _crop_frame_of_nones(frame)

		ts =_get_frame_timesteps(slave, len(frame))

		if waveform == SG_WAVE_SINE:
			# Generate the frame that minimises the error
			expected_phase = 0.0
			gen_frame = _sinewave(ts,vpp/2.0,expected_phase,offset,freq)

		elif waveform == SG_WAVE_TRIANGLE:
			# Generate the frame that minimises the error
			expected_phase = _calculate_triangle_phase(duty)
			gen_frame = _sawtooth(ts, vpp/2.0, expected_phase, offset, freq, duty)

		elif waveform == SG_WAVE_SQUARE:
			# Generate the frame that minimises the error
			expected_phase = 0.0
			gen_frame = _squarewave(ts, vpp/2.0, expected_phase, offset, freq, duty)

		else:
			print "Invalid waveform"
			assert False

		if DEBUG_TESTS:
			if not in_rms_bounds(frame, gen_frame, waveform, vpp):
				plt.plot(ts,frame - gen_frame)
				plt.plot(ts, frame)
				plt.plot(ts, gen_frame)	
				plt.show()

		assert in_rms_bounds(frame, gen_frame, waveform, vpp)

	@pytest.mark.parametrize("ch, freq, phase, waveform",
		itertools.product(
			[1,2],
			[1e3, 1e6], 
			[0.1, 0.3, 0.5, 0.7, 0.85],
			[SG_WAVE_SINE, SG_WAVE_TRIANGLE, SG_WAVE_SQUARE]
			))
	def test_output_phase(self, base_instrs, ch, freq, phase, waveform):

		master = base_instrs[0]
		slave = base_instrs[1]

		source_vpp = 1.0
		source_freq = freq
		source_offset = 0.0
		source_duty = 0.5

		timebase_cyc = 10.0
		slave.set_timebase(0, timebase_cyc/freq)
		slave.set_source(1, OSC_SOURCE_ADC)
		slave.set_source(2, OSC_SOURCE_ADC)
		slave.set_frontend(1, fiftyr=True, atten=False, ac=False)
		slave.set_frontend(2, fiftyr=True, atten=False, ac=False)
		# Reset phase from last test
		master.out1_phase = 0.0
		master.out2_phase = 0.0

		# Trigger on the channel we aren't changing the phase on
		if ch == 1:
			slave.set_trigger(OSC_TRIG_CH2, OSC_EDGE_RISING, source_offset, hysteresis = 5, mode=OSC_TRIG_NORMAL)
		else:
			slave.set_trigger(OSC_TRIG_CH1, OSC_EDGE_RISING, source_offset, hysteresis = 5, mode=OSC_TRIG_NORMAL)

		# Generate signals on master
		if waveform == SG_WAVE_SINE:
			master.synth_sinewave(1, source_vpp, freq, source_offset)
			master.synth_sinewave(2, source_vpp, freq, source_offset)
		elif waveform == SG_WAVE_SQUARE:
			master.synth_squarewave(1, source_vpp, freq, offset=source_offset, duty = source_duty)
			master.synth_squarewave(2, source_vpp, freq, offset=source_offset, duty = source_duty)
		elif waveform == SG_WAVE_TRIANGLE:
			master.synth_rampwave(1, source_vpp, freq, offset=source_offset, symmetry = source_duty)
			master.synth_rampwave(2, source_vpp, freq, offset=source_offset, symmetry = source_duty)
		else:
			print "Invalid waveform type."
			assert False

		master.commit()
		slave.commit()

		def approximate_phase(t, waveform, waveform_type, vpp, freq, offset, duty):
			# Generate signals on master
			phase_values = numpy.linspace(0, 2.0*numpy.pi, num=100, endpoint=False)
			rms_errors = []
			for p in phase_values:
				if waveform_type == SG_WAVE_SINE:
					compare_waveform = _sinewave(t, vpp/2.0, p, offset, freq)
				elif waveform_type == SG_WAVE_SQUARE:
					compare_waveform = _sawtooth(t, vpp/2.0, p, offset, freq, duty)
				elif waveform_type == SG_WAVE_TRIANGLE:
					compare_waveform = _sawtooth(t, vpp/2.0, p, offset, freq, duty)
				else:
					print "Invalid waveform type."
					assert False 

				rms_errors = rms_errors + [_calculate_rms_error(waveform, compare_waveform)]

			return phase_values[numpy.argmin(rms_errors)]/(2.0*numpy.pi)

		# Get the relative phase on slave
		slave.get_frame(timeout=FRAME_TIMEOUT) # Throwaway
		frame1 = slave.get_frame(timeout=FRAME_TIMEOUT)
		if ch==1:
			frame1 = frame1.ch1
		else:
			frame1 = frame1.ch2

		# Initial phase
		ts = _get_frame_timesteps(slave, len(frame1))
		phase_1 = approximate_phase(ts, frame1, SG_WAVE_SINE, source_vpp/2.0, source_freq, source_offset, source_duty)

		# Change the output phase of desired output waveform
		if ch == 1:
			master.out1_phase = phase
		else:
			master.out2_phase = phase
		master.commit()
		slave.commit()

		# Calculate new phase
		slave.get_frame(timeout=FRAME_TIMEOUT)
		time.sleep(2.0*timebase_cyc/source_freq)
		slave.get_frame(timeout=FRAME_TIMEOUT)
		frame2 = slave.get_frame(timeout=FRAME_TIMEOUT)
		if ch==1:
			frame2 = frame2.ch1
		else:
			frame2 = frame2.ch2

		phase_2 = approximate_phase(ts, frame2, SG_WAVE_SINE, source_vpp/2.0, source_freq, source_offset, source_duty)

		# Check the change in phase is as expected
		if DEBUG_TESTS:
			if not in_bounds( ((phase_2 % 1.0) - (phase_1 % 1.0)) % 1.0, phase, PHASE_TOL_R):
				plt.plot(ts, frame1)
				plt.plot(ts, frame2)
				plt.show()
		assert in_bounds( ((phase_2 % 1.0) - (phase_1 % 1.0)) % 1.0, phase, PHASE_TOL_R)

class Test_Trigger:
	'''
		This class tests Trigger modes of the Oscilloscope
	'''

	@pytest.mark.parametrize("trig_ch, freq, edge, trig_lvl",
		itertools.product(
			[OSC_TRIG_CH1, OSC_TRIG_DA1, OSC_TRIG_CH2, OSC_TRIG_DA2],
			[5e3, 1e6],
			[OSC_EDGE_RISING, OSC_EDGE_FALLING, OSC_EDGE_BOTH], 
			[0.0, 0.0, 0.1, 0.3]))
	def test_triggered_edge(self, base_instrs, trig_ch, freq, edge, trig_lvl):
		'''
			Test the triggered edge type and level are correct
		'''
		# Get the Master Moku
		master = base_instrs[0]
		slave = base_instrs[1]

		master.set_frontend(1, fiftyr=True, atten=False, ac=False)
		master.set_frontend(2, fiftyr=True, atten=False, ac=False)

		# Set up the source signal to test triggering on
		source_freq = freq #Hz
		source_vpp = 1.0
		source_offset = 0.0

		if trig_ch == OSC_TRIG_DA1:
			master.set_source(1, OSC_SOURCE_DAC)
			master.synth_sinewave(1, source_vpp, source_freq, source_offset)
		elif trig_ch == OSC_TRIG_CH1:
			master.set_source(1, OSC_SOURCE_ADC)
			slave.synth_sinewave(1, source_vpp, source_freq, source_offset)
		elif trig_ch == OSC_TRIG_DA2:
			master.set_source(2, OSC_SOURCE_DAC)
			master.synth_sinewave(2, source_vpp, source_freq, source_offset)
		elif trig_ch == OSC_TRIG_CH2:
			master.set_source(2, OSC_SOURCE_ADC)
			slave.synth_sinewave(2, source_vpp, source_freq, source_offset)
		else:
			print "Invalid trigger channel"
			assert False

		timebase_cyc = 10.0
		master.set_timebase(-timebase_cyc/source_freq,timebase_cyc/source_freq)

		slave.commit()
		master.set_trigger(trig_ch, edge, trig_lvl, hysteresis=25, hf_reject=False, mode=OSC_TRIG_NORMAL)
		master.commit()

		master.get_frame(timeout = FRAME_TIMEOUT, wait=True) # Throwaway
		master.get_frame(timeout = FRAME_TIMEOUT)
		t_step = master._calculate_frame_timestep(master.decimation_rate, master.render_deci)
		ts = master._calculate_frame_start_time(master.decimation_rate, master.render_deci, master.offset) + ((numpy.cumsum([t_step]*_OSC_SCREEN_WIDTH))- t_step)
		
		# Calculate the index of the trigger point
		time_zero_idx = zero_crossings(ts)

		# Test multiple triggers
		num_trigger_tests = 10
		for _ in range(num_trigger_tests):
			frame = master.get_frame(timeout=FRAME_TIMEOUT)
			if (trig_ch == OSC_TRIG_DA1) or (trig_ch == OSC_TRIG_CH1):
				ch_frame = frame.ch1
			else:
				ch_frame = frame.ch2

			# Check correct amplitude
			assert in_bounds((ch_frame[time_zero_idx]+ch_frame[time_zero_idx+1])/2.0, trig_lvl, max(ADC_AMP_TOL_P*source_vpp, 0.01))

			# Check the correct edge type near start of frame
			if(edge == OSC_EDGE_RISING):
				assert _is_rising(ch_frame[time_zero_idx],ch_frame[time_zero_idx+1])
			elif(edge == OSC_EDGE_FALLING):
				assert _is_falling(ch_frame[time_zero_idx],ch_frame[time_zero_idx+1])
			elif(edge == OSC_EDGE_BOTH):
				assert _is_rising(ch_frame[time_zero_idx],ch_frame[time_zero_idx+1]) or _is_falling(ch_frame[time_zero_idx],ch_frame[time_zero_idx+1])


	def _setup_trigger_mode_test(self, master, trig_ch, trig_lvl, trig_edge, trig_mode, source_vpp, source_offset, source_freq):
		# Set up a DAC trigger source
		# And turn on triggering

		# Generate waveform to trigger off
		master.synth_sinewave(trig_ch, source_vpp, source_freq, source_offset)

		master.set_source(trig_ch, OSC_SOURCE_DAC)
		if trig_ch == 1:
			master.set_trigger(OSC_TRIG_DA1, trig_edge, trig_lvl, hysteresis = 0, hf_reject = False, mode = trig_mode)
		if trig_ch == 2:
			master.set_trigger(OSC_TRIG_DA2, trig_edge, trig_lvl, hysteresis = 0, hf_reject = False, mode = trig_mode)

	@pytest.mark.parametrize("freq",
		itertools.product(
			[20, 30, 40, 1e3, 10e3, 1e6, 10e6]
			))
	def test_trigger_mode_normal(self, base_instrs, freq):
		'''
			Tests 'Normal' trigger mode
		'''
		master = base_instrs[0]

		timebase_cyc = 10.0

		trig_ch = 1
		trig_lvl = 0.0
		trig_edge = OSC_EDGE_RISING
		trig_mode = OSC_TRIG_NORMAL
		trig_source_vpp = 1.0
		trig_source_offset = 0.0
		trig_source_freq = freq
		self._setup_trigger_mode_test(master, trig_ch, trig_lvl, trig_edge, trig_mode, trig_source_vpp, trig_source_offset, trig_source_freq)
		
		master.set_timebase(0, timebase_cyc/freq)
		master.commit()

		triggers_per_frame = min((freq/timebase_cyc)/master.framerate, OSC_MAX_TRIGRATE/master.framerate)
		triggers_per_frame_tolerance = 0.2 #20%

		# Case when trigger rate is greater than frame rate
		if triggers_per_frame > 2:
			waveformid = None

			for _ in range(10):
				frame = master.get_frame(timeout = FRAME_TIMEOUT)

				if waveformid:
					# Waveform ID has increased since last frame
					assert frame.waveformid > waveformid

					# The change in waveform ID is approximately the expected number of triggers per frame
					delta_id = frame.waveformid - waveformid
					assert in_bounds(triggers_per_frame, delta_id, max(triggers_per_frame*triggers_per_frame_tolerance, 1))
					# Debug print
					if DEBUG_TESTS:
						print("Delta ID: %f, Triggers Per Frame: %f" % (delta_id, triggers_per_frame))
				
				waveformid = frame.waveformid

		# Case when trigger rate is slower than frame rate
		else:
			frames_per_trigger = 1.0/triggers_per_frame

			for _ in range(10):
				frame = master.get_frame(timeout = 30)
				waveformid = frame.waveformid
				frame_ctr = 0

				while (frame.waveformid == waveformid):
					frame_ctr = frame_ctr + 1
					frame = master.get_frame(timeout = 30)

				# The number of frames per trigger is approximately as expected
				assert in_bounds(frames_per_trigger, frame_ctr, 2)

				# Debug print
				if DEBUG_TESTS:
					print("Frame Ctr: %f, Frames Per Trigger: %f" % (frame_ctr, frames_per_trigger))

	def test_trigger_mode_normal_notrigger(self, base_instrs):
		'''
			Tests the case of Normal trigger mode when there are no trigger events
		'''
		master = base_instrs[0]

		timebase_cyc = 10.0

		trig_ch = 1
		trig_lvl = 1.5
		trig_edge = OSC_EDGE_RISING
		trig_mode = OSC_TRIG_NORMAL
		trig_source_vpp = 1.0
		trig_source_offset = 0.0
		trig_source_freq = 1e3
		self._setup_trigger_mode_test(master, trig_ch, trig_lvl, trig_edge, trig_mode, trig_source_vpp, trig_source_offset, trig_source_freq)
		master.set_timebase(0, timebase_cyc/trig_source_freq)
		master.commit()
		# There should be no trigger events
		with pytest.raises(FrameTimeout):
			frame = master.get_frame(timeout = 5)
 
	def test_trigger_mode_auto_notrigger(self, base_instrs):
		'''
			Tests 'Auto' trigger mode
		'''
		master = base_instrs[0]

		timebase_cyc = 10.0

		trig_ch = 1
		trig_lvl = 1.5
		trig_edge = OSC_EDGE_RISING
		trig_mode = OSC_TRIG_AUTO
		trig_source_vpp = 1.0
		trig_source_offset = 0.0
		trig_source_freq = 1e3
		self._setup_trigger_mode_test(master, trig_ch, trig_lvl, trig_edge, trig_mode, trig_source_vpp, trig_source_offset, trig_source_freq)
		master.set_timebase(0, timebase_cyc/trig_source_freq)
		master.commit()

		# Auto mode test - every frame should have maximum number of triggers
		ids = []
		for _ in range(20):
			frame = master.get_frame(timeout = 5)
			ids = ids + [frame.waveformid]

		delta_ids = numpy.diff(ids)
		avg = sum(delta_ids)/float(len(delta_ids))
		if DEBUG_TESTS:
			print("Delta IDs: %s, Avg: %f" % (delta_ids, avg))
		assert in_bounds(avg, OSC_AUTO_TRIGRATE/master.framerate, 0.2)

	def test_trigger_mode_single(self, base_instrs):
		'''
			Tests 'Single' trigger mode
		'''
		master = base_instrs[0]

		# Set up a trigger source
		trig_ch = 1
		trig_lvl = 0.0
		trig_edge = OSC_EDGE_RISING
		trig_mode = OSC_TRIG_SINGLE
		trig_source_vpp = 1.0
		trig_source_offset = 0.0
		trig_source_freq = 1e3
		self._setup_trigger_mode_test(master, trig_ch, trig_lvl, trig_edge, trig_mode, trig_source_vpp, trig_source_offset, trig_source_freq)
		master.set_timebase(0, 5.0/trig_source_freq)
		master.commit()

		frame = master.get_frame(timeout=FRAME_TIMEOUT)
		init_state_id = frame.stateid
		init_waveform_id = frame.waveformid
		init_trig_id = frame.trigstate

		# Force a change of state ID and check it doesn't retrigger
		master.commit()

		while frame.stateid == init_state_id:
			frame = master.get_frame(wait=False, timeout = 5)

		# Assert that the same waveform is being sent in the frame, and no additional triggers have occurred
		assert frame.waveformid == init_waveform_id
		assert frame.stateid > init_trig_id

		print("State ID: %s, Trigstate: %s, Waveform ID: %s, Frame ID: %s" % (frame.stateid, frame.trigstate, frame.waveformid, frame.frameid))

	@pytest.mark.parametrize("ch", [OSC_TRIG_CH1, OSC_TRIG_CH2, OSC_TRIG_DA1, OSC_TRIG_DA2])
	def test_trigger_channels(self, base_instrs, ch):
		'''
			Tests triggering on ADC and DAC channels
		'''
		master = base_instrs[0]
		slave = base_instrs[1]

		timebase_cyc = 10.0 

		trig_source_freq = [1e3, 1e3, 0.75e3, 1.75e3]
		trig_source_vpp = [1.0, 0.5, 1.0, 0.5]
		trig_source_offset = [0.0, 0.0, 0.0, 0.0]
		trig_lvl = [0.0,0.0,0.0,0.0]

		# Make sure signals coming from slave are not amplified or attenuated
		master.set_frontend(1, fiftyr=True, atten=False, ac=False)
		master.set_frontend(2, fiftyr=True, atten=False, ac=False)

		# Generate a different output on Channel 2 so 
		master.synth_sinewave(1, trig_source_vpp[0], trig_source_freq[0], trig_source_offset[0])
		master.synth_sinewave(2, trig_source_vpp[1], trig_source_freq[1], trig_source_offset[1])
		slave.synth_sinewave(1, trig_source_vpp[2], trig_source_freq[2], trig_source_offset[2])
		slave.synth_sinewave(2, trig_source_vpp[3], trig_source_freq[3], trig_source_offset[3])

		# Check the correct frame is being received
		if ch == OSC_TRIG_CH1:
			master.set_source(1, OSC_SOURCE_ADC)
			idx = 2
		elif ch == OSC_TRIG_DA1:
			master.set_source(1, OSC_SOURCE_DAC)
			idx = 0
		elif ch == OSC_TRIG_CH2:
			master.set_source(2, OSC_SOURCE_ADC)
			idx = 3
		elif ch == OSC_TRIG_DA2:
			master.set_source(2, OSC_SOURCE_DAC)
			idx = 1
		else:
			print "Invalid trigger channel"
			assert False

		master.set_trigger(ch, OSC_EDGE_RISING, 0.0, mode=OSC_TRIG_NORMAL)
		master.set_timebase(0,timebase_cyc/trig_source_freq[idx])
		master.commit()
		slave.commit()

		master.get_frame(timeout = FRAME_TIMEOUT)
		master.get_frame(timeout = FRAME_TIMEOUT)
		# Get a frame on the appropriate channel and check it is as expected
		frame = master.get_frame(timeout = FRAME_TIMEOUT)

		# Check the frame
		if ch == OSC_TRIG_CH1 or ch == OSC_TRIG_DA1:
			frame = frame.ch1
		elif ch == OSC_TRIG_CH2 or ch == OSC_TRIG_DA2:
			frame = frame.ch2
		else:
			print "Invalid trigger channel"
			assert False
		frame = _crop_frame_of_nones(frame)

		ts = _get_frame_timesteps(master, len(frame))

		# Curve fit the frame data to ensure correct waveform has been triggered
		# Generate the expected waveform and compare difference (should be same)
		expected_waveform = _sinewave(ts, trig_source_vpp[idx]/2.0, 0.0, trig_source_offset[idx], trig_source_freq[idx])

		assert in_rms_bounds(expected_waveform, frame, SG_WAVE_SINE, trig_source_vpp[idx])

class Test_Timebase:
	'''
		Ensure the timebase is correct
		TODO: Does it make sense to test timebase only for a single channel
	'''

	@pytest.mark.parametrize("ch, span", 
		itertools.product([1,2], [5e-6, 1e-3, 2]))
	def test_timebase_span(self, base_instrs, ch, span):
		'''
			Test that the frame's timebase is consistent with the captured waveform frequency
		'''
		master = base_instrs[0]

		timebase_cycles = 10.0
		source_freq = timebase_cycles/span
		source_vpp = 1.0
		source_offset = 0.0
		source_phase = 0.0

		master.set_source(ch, OSC_SOURCE_DAC)
		if ch == 1:
			master.set_trigger(OSC_TRIG_DA1, OSC_EDGE_RISING, 0.0, mode=OSC_TRIG_NORMAL)
		else:
			master.set_trigger(OSC_TRIG_DA2, OSC_EDGE_RISING, 0.0, mode=OSC_TRIG_NORMAL)
		master.synth_sinewave(ch, source_vpp, source_freq, source_offset)
		master.set_timebase(0,span)
		master.commit()

		frame = master.get_frame(timeout = FRAME_TIMEOUT)
		if ch==1:
			data = _crop_frame_of_nones(frame.ch1)
		else:
			data = _crop_frame_of_nones(frame.ch2)

		ts = _get_frame_timesteps(master, len(frame))

		# Assume the expected waveform and do an RMS fit
		expected_waveform = _sinewave(ts, source_vpp/2.0, source_phase, source_offset, source_freq)

		if DEBUG_TESTS:
			plt.plot(ts, expected_waveform)
			plt.plot(ts, data)
			plt.show()

		assert in_rms_bounds(expected_waveform, data, SG_WAVE_SINE, source_vpp)

	@pytest.mark.parametrize("ch, pretrigger_time",
		itertools.product(
			[1,2],
			[20e-6, 1e-6, 20e-3, 1e-3, 100e-3, 1]))
	def test_pretrigger(self, base_instrs, ch, pretrigger_time):
		'''
			Test that the captured waveform is offset by the correct amount of time (pretrigger)
		'''
		master = base_instrs[0]

		source_freq = 1.0/(3*pretrigger_time)
		source_vpp = 1.0
		source_offset = 0.0
		trig_lvl = source_offset

		# Generate a pulse of some small width and period < frame length
		master.synth_sinewave(ch, source_vpp, source_freq, source_offset)
		if ch == 1:
			master.set_trigger(OSC_TRIG_DA1, OSC_EDGE_RISING, trig_lvl, mode=OSC_TRIG_NORMAL)
		else:
			master.set_trigger(OSC_TRIG_DA2, OSC_EDGE_RISING, trig_lvl, mode=OSC_TRIG_NORMAL)
		master.set_source(ch, OSC_SOURCE_DAC)
		master.set_timebase(-pretrigger_time, 3*pretrigger_time) # Ensures trigger is first zero crossing
		master.commit()

		# Compute the index of which the rising edge should occur
		if ch == 1:
			frame = master.get_frame(timeout = FRAME_TIMEOUT*2.0).ch1
		else:
			frame = master.get_frame(timeout = FRAME_TIMEOUT*2.0).ch2
		frame = _crop_frame_of_nones(frame)
		ts = _get_frame_timesteps(master, len(frame))

		# Get index of the zero crossing
		zc = zero_crossings(frame)

		# Convert indices to timesteps
		t_step = ts[1]-ts[0]
		pretrig_time = zc[0] * t_step

		if DEBUG_TESTS:
			print("Pretrigger (s): %f/%f" % (pretrigger_time, pretrig_time))

		# Within two samples or 5% of desired pretrigger time
		assert in_bounds(pretrig_time, pretrigger_time, max(2*t_step, 0.05*pretrigger_time))

	@pytest.mark.parametrize("ch, posttrigger_time",
		itertools.product(
			[1,2],
			[20e-6, 1e-6, 20e-3, 1e-3, 100e-3, 1]))
	def test_posttrigger(self, base_instrs, ch, posttrigger_time):

		master = base_instrs[0]

		source_freq = 1.0/(2*posttrigger_time)
		source_vpp = 1.0
		source_offset = 0.0
		trig_lvl = source_offset

		master.synth_sinewave(ch, source_vpp, source_freq, duty=0.1)
		if ch == 1:
			master.set_trigger(OSC_TRIG_DA1, OSC_EDGE_RISING, 0, mode=OSC_TRIG_NORMAL)
		else:
			master.set_trigger(OSC_TRIG_DA2, OSC_EDGE_RISING, 0, mode=OSC_TRIG_NORMAL)
		master.set_source(ch, OSC_SOURCE_DAC)
		master.set_timebase(posttrigger_time, 5*posttrigger_time)
		master.commit()

		if ch == 1:
			frame = master.get_frame().ch1
		else:
			frame = master.get_frame().ch2
		frame = _crop_frame_of_nones(frame)

		# Get index of the zero crossing
		zc = zero_crossings(frame)

		# Convert indices to timesteps
		ts = _get_frame_timestep(master)
		if DEBUG_TESTS:
			plt.plot(ts, frame)
			plt.show()

		source_period = 1.0/source_freq
		period_tolerance = max(2*ts,source_period*0.05)
		measured_period = (zc[0] * ts) + posttrigger_time
		measured_period_error = abs(measured_period-source_period)/source_period

		if DEBUG_TESTS:
			print("ZC: %f, Sum: %f, Period: %f, Tolerance: %f, Error: %f" % ((zc[0] * ts), measured_period, source_period, period_tolerance, measured_period_error))
		assert in_bounds(measured_period, source_period, period_tolerance)

class Test_Frontend:

	@pytest.mark.parametrize("ch, fiftyr, vpp, freq, offset",
		itertools.product(
			[1,2],
			[False],
			[0.2, 0.5, 1.0, 1.5],
			[100, 1e3, 20e3, 1e6],
			[0.0, 0.2]
			))
	def test_input_impedance(self, base_instrs, ch, fiftyr, vpp, freq, offset):
		master = base_instrs[0]
		slave = base_instrs[1]

		timebase_cyc = 10.0
		source_vpp = vpp
		source_freq = freq
		source_offset = offset
		tolerance_percent = 0.05

		expected_vpp = source_vpp if fiftyr else (source_vpp*2.0)
		expected_off = source_offset if fiftyr else (source_offset*2.0)

		# Put in different waveforms and test they look correct in a frame
		master.set_frontend(ch, fiftyr=fiftyr, atten=True, ac=False)
		master.set_source(ch, OSC_SOURCE_ADC)

		if ch == 1:
			master.set_trigger(OSC_TRIG_CH1, OSC_EDGE_RISING, expected_off, hf_reject = False, hysteresis=25, mode=OSC_TRIG_NORMAL)
		else:
			master.set_trigger(OSC_TRIG_CH2, OSC_EDGE_RISING, expected_off, hf_reject = False, hysteresis=25, mode=OSC_TRIG_NORMAL)
		master.set_timebase(0,timebase_cyc/source_freq)

		slave.synth_sinewave(ch, source_vpp, source_freq, source_offset)
		slave.commit()
		master.commit()

		master.get_frame(timeout = 5) # throwaway
		time.sleep(0.01)
		master.get_frame(timeout = 5)
		if ch == 1:
			frame = master.get_frame(timeout = 5).ch1
		if ch == 2:
			frame = master.get_frame(timeout = 5).ch2
		frame = _crop_frame_of_nones(frame)

		# Fit a curve to the input waveform
		ts = _get_frame_timesteps(master, len(frame))
		expected_waveform = _sinewave(ts, expected_vpp/2.0, 0.0, expected_off, source_freq)

		if DEBUG_TESTS and not in_rms_bounds(expected_waveform, frame, SG_WAVE_SINE, expected_vpp):
			plt.plot(ts, expected_waveform)
			plt.plot(ts, frame)
			plt.show()

		assert in_rms_bounds(expected_waveform, frame, SG_WAVE_SINE, expected_vpp)

	@pytest.mark.parametrize("ch, atten, vpp",
		itertools.product(
			[1,2],
			[False, True],
			[0.3, 0.7, 1.0, 1.3, 1.8, 2.0]
			))
	def test_input_attenuation(self, base_instrs, ch, atten, vpp):
		master = base_instrs[0]
		slave = base_instrs[1]

		source_vpp = vpp # Vpp
		source_freq = 1e3 # Hz
		source_offset = 0.0

		SMALL_INPUT_RANGE= 1.0 # Vpp
		LARGE_INPUT_RANGE= 10.0 # Vpp
		tolerance_r = 0.2 # V
		
		slave.synth_sinewave(ch, source_vpp, source_freq, source_offset)
		slave.commit()

		timebase_cyc = 10.0
		master.set_frontend(ch, fiftyr=True, atten=atten, ac=False)
		master.set_timebase(0,timebase_cyc/source_freq)
		if ch == 1:
			master.set_trigger(OSC_TRIG_CH1, OSC_EDGE_RISING, source_offset, hf_reject = False, hysteresis=25, mode=OSC_TRIG_NORMAL)
		else:
			master.set_trigger(OSC_TRIG_CH2, OSC_EDGE_RISING, source_offset, hf_reject = False, hysteresis=25, mode=OSC_TRIG_NORMAL)
		master.commit()

		# Get a throwaway frame
		master.get_frame(timeout= FRAME_TIMEOUT)

		# Get a valid frame
		if ch == 1:
			frame = master.get_frame(timeout = 5).ch1
		else:
			frame = master.get_frame(timeout = 5).ch2
		frame = _crop_frame_of_nones(frame)
		ts = _get_frame_timesteps(master, len(frame))

		if (atten and source_vpp < LARGE_INPUT_RANGE) or ((not atten) and source_vpp < SMALL_INPUT_RANGE) :
			expected_waveform = _sinewave(ts, source_vpp/2.0, 0.0, source_offset, source_freq)
			assert in_rms_bounds(expected_waveform, frame, SG_WAVE_SINE, source_vpp )
		else:
			# Clipping will have occurred, full range used
			assert in_bounds(abs(max(frame)-min(frame)),SMALL_INPUT_RANGE, SMALL_INPUT_RANGE + tolerance_r)

	@pytest.mark.parametrize("ch, fiftyr, ac, amp, offset",
		itertools.product(
			[1,2],
			[True, False],
			[True, False],
			[0.3],
			[-0.2, -0.1, 0.0, 0.1, 0.2]
			))
	def test_acdc_coupling(self, base_instrs, ch, fiftyr, ac, amp, offset):

		tolerance_percent =  ADC_AMP_TOL_P
		tolerance_offset = ADC_OFF_TOL_R

		master = base_instrs[0]
		slave = base_instrs[1]

		timebase_cyc = 5.0

		source_amp = amp # Vpp
		source_offset = offset
		# Set the source frequency "large enough" to avoid attenuation
		if fiftyr:
			source_freq = AC_COUPLE_CORNER_FREQ_50O*1.0
		else:
			source_freq = AC_COUPLE_CORNER_FREQ_1MO*3.0

		# Expected offset and amplitude
		expected_amp = source_amp if fiftyr else source_amp * 2.0
		expected_offset = 0.0 if ac else (source_offset if fiftyr else source_offset * 2.0)

		slave.synth_sinewave(ch, source_amp, source_freq, source_offset)
		slave.commit()

		master.set_frontend(ch, fiftyr=fiftyr, atten=True, ac=ac)
		master.set_timebase(0, timebase_cyc/source_freq)
		if ch == 1:
			master.set_trigger(OSC_TRIG_CH1, OSC_EDGE_RISING, expected_offset, hf_reject = False, hysteresis=10, mode=OSC_TRIG_NORMAL)
		else:
			master.set_trigger(OSC_TRIG_CH2, OSC_EDGE_RISING, expected_offset, hf_reject = False, hysteresis=10, mode=OSC_TRIG_NORMAL)
		master.commit()

		# Throwaway frame
		master.get_frame(timeout = 5)
		if ch == 1:
			frame = master.get_frame(timeout = 5).ch1
		else:
			frame = master.get_frame(timeout = 5).ch2
		frame = _crop_frame_of_nones(frame)

		# Check that the amplitude is half and that it is approximately 0V mean if AC coupling is ON
		# OR "Offset" if DC coupling
		# Fit a curve to the input waveform (it shouldn't be clipped)
		ts = _get_frame_timesteps(master, len(frame))

		expected_waveform = _sinewave(ts, expected_amp/2.0, 0.0, expected_offset, source_freq)

		# Handle incorrect (falling edge) triggers by phase shifting the expected waveform by pi
		if not in_rms_bounds(expected_waveform, frame, SG_WAVE_SINE, expected_amp):
			expected_waveform = _sinewave(ts, expected_amp/2.0, numpy.pi, expected_offset, source_freq)

		assert in_rms_bounds(expected_waveform, frame, SG_WAVE_SINE, expected_amp)


