import itertools
import pytest, time
from pymoku import Moku, FrameTimeout
from pymoku.instruments import *
from pymoku._oscilloscope import _OSC_SCREEN_WIDTH, _OSC_ADC_SMPS, OSC_TRIG_NORMAL, OSC_TRIG_SINGLE, OSC_TRIG_AUTO
from pymoku._siggen import SG_MOD_NONE, SG_MOD_AMPL, SG_MOD_PHASE, SG_MOD_FREQ, SG_MODSOURCE_INT, SG_MODSOURCE_ADC, SG_MODSOURCE_DAC, SG_WAVE_SINE, SG_WAVE_SQUARE, SG_WAVE_TRIANGLE, SG_WAVE_DC
import conftest
import numpy, math
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

OSC_MAX_TRIGRATE = 8e3 #Approximately 8kHz
OSC_AUTO_TRIGRATE = 20

# Assertion helpers
def in_bounds(v, center, err):
	if (v is None) or (center is None):
		return True
	return abs(v - center) <= abs(err)

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

def _sinewave(t,ampl,ph,off,freq):
	# Taken from commissioning/calibration.py
	return off+ampl*numpy.sin(2*numpy.pi*freq*t+ph)
	#return numpy.array([off+ampl*math.sin(2*math.pi*freq*x+ph) for x in t])

@pytest.fixture(scope="module")
def base_instrs(conn_mokus):
	m1 = conn_mokus[0]
	m2 = conn_mokus[1]
	print("Attaching instruments")

	i1 = Oscilloscope()
	i2 = Oscilloscope()

	m1.attach_instrument(i1)
	m2.attach_instrument(i2)

	i1.set_defaults()
	i2.set_defaults()
	i1.commit()
	i2.commit()

	return (i1,i2)

class Tes2_Siggen:
	'''
		This class tests the correctness of the embedded signal generator 
	'''

	@pytest.mark.parametrize("ch, vpp, freq, offset, waveform", 
		itertools.product([1,2],[0, 0.5, 1.0],[1e3, 1e6], [0, 0.3, 0.5], [SG_WAVE_SINE, SG_WAVE_SQUARE, SG_WAVE_TRIANGLE]))
	def tes2_waveform_amp(self, base_instrs, ch, vpp, freq, offset, waveform):
		'''
			Test the max/min amplitude of the waveforms are correct
		'''
		master = base_instrs[0]


		# Set timebase to allow for 5 cycles
		if freq == 0:
			tspan = 1.0 # Set DC to 1 second
		else:
			tspan = (1.0/freq) * 5.0
		master.set_timebase(0,tspan)

		# Loop DAC to input to measure the generated waveforms
		master.set_source(ch,OSC_SOURCE_DAC)
		if(ch==1):
			master.set_trigger(OSC_TRIG_DA1, OSC_EDGE_RISING, 0)
		else:
			master.set_trigger(OSC_TRIG_DA2, OSC_EDGE_RISING, 0)

		# Generate the desired waveform
		if waveform == SG_WAVE_SINE:
			master.synth_sinewave(ch, vpp, freq, offset)
		elif waveform == SG_WAVE_SQUARE:
			master.synth_squarewave(ch, vpp, freq,offset=offset)
		elif waveform == SG_WAVE_TRIANGLE:
			master.synth_rampwave(ch, vpp, freq, offset=offset)
		master.commit()

		# 5mV Tolerance on max/min values
		tolerance = 0.005


		# Test amplitudes on a few frames worth of generated output
		for _ in range(10):
			frame = master.get_frame(wait=True)
			print frame
			if(ch==1):
				ch_frame = frame.ch1
			else:
				ch_frame = frame.ch2

			# For debugging the received frame
			for y in ch_frame:
				print y

			# Get max/min amplitudes for each frame
			maxval = max(x for x in ch_frame if x is not None)
			minval = min(x for x in ch_frame if x is not None)

			# Check max/min values are within tolerance bounds
			assert in_bounds(maxval, (vpp/2.0)+offset, tolerance)
			assert in_bounds(minval, (-1*(vpp/2.0) + offset), tolerance)


	@pytest.mark.parametrize("ch, vpp, freq, waveform", 
		itertools.product([1,2],[1.0],[100, 1e3, 100e3, 1e6, 3e6],[SG_WAVE_SINE, SG_WAVE_SQUARE, SG_WAVE_TRIANGLE]))
	def tes2_waveform_freq(self, base_instrs, ch, vpp, freq, waveform):
		'''
			Test the frequency of generated waveforms

			This is done by checking that the amplitude of generated signals is constant as we jump across multiple cycles
			of the waveform.
		'''
		master = base_instrs[0]

		# Set timebase to allow for 5 cycles
		number_periods = 5
		period = (1.0/freq)
		tspan = period * number_periods
		master.set_timebase(0,tspan)

		# Loop DAC output to input for measurement
		master.set_source(ch,OSC_SOURCE_DAC)
		master.set_xmode(OSC_FULL_FRAME)
		if(ch==1):
			master.set_trigger(OSC_TRIG_DA1, OSC_EDGE_RISING, 0)
		else:
			master.set_trigger(OSC_TRIG_DA2, OSC_EDGE_RISING, 0)

		# Get back actual timebase (this will not be precisely 5 cycles due to rounding)
		(tstart, tend) = master._get_timebase(master.decimation_rate, master.pretrigger, master.render_deci, master.offset)

		# Compute the approximate number of samples per waveform period
		time_per_smp = (tend-tstart)/_OSC_SCREEN_WIDTH
		smps_per_period = period/time_per_smp

		# Generate the waveform type to be tested
		# Define the offset into each frame that we should start measuring amplitudes from
		if waveform == SG_WAVE_SINE:
			master.synth_sinewave(ch,vpp,freq,0.0)
			start_xs = [0, int(smps_per_period/2), int(smps_per_period/3), int(smps_per_period/4), int(smps_per_period/8), int(3*smps_per_period/4)]
		elif waveform == SG_WAVE_SQUARE:
			master.synth_squarewave(ch, vpp, freq)
			# Don't start on a squarewave edge
			start_xs = [int(smps_per_period/3), int(3*smps_per_period/4), int(2*smps_per_period/3), int(smps_per_period/8), int(7*smps_per_period/8)]
		elif waveform == SG_WAVE_TRIANGLE:
			master.synth_rampwave(ch, vpp, freq)
			start_xs = [0, int(smps_per_period/2), int(smps_per_period/3), int(smps_per_period/4), int(smps_per_period/8), int(3*smps_per_period/4)]
		master.commit()

		# Allow 2% variation in amplitude
		allowable_error = 0.02*vpp

		# Workaround for ensuring we receive a valid waveform in the frame
		# The squarewave generator has unpredictable initial conditions currently
		# So we want to skip the first frame
		time.sleep(3*(tend-tstart))
		master.flush()
		master.get_frame()

		# Test multiple frames worth
		for _ in range(5):

			frame = master.get_frame()
			if(ch==1):
				ch_frame = frame.ch1
			if(ch==2):
				ch_frame = frame.ch2

			for start_x in start_xs:
				# First amplitude measurement of the waveform
				expectedv = ch_frame[start_x]

				# Skip along the waveform, 1 cycle at a time and check
				# the amplitude matches the expected value.
				for i in range(number_periods-1):
					x = start_x + int(round(i*smps_per_period))

					actualv = ch_frame[x]

					# For debugging the received frame
					#for y in ch_frame:
					#	print y

					# Debugging info
					# print "Allowable tolerance: %.10f, Error: %.10f, Frame index: %d, Expected value: %.10f, Actual value: %.10f, Samples per period: %d, Render deci: %f" % (allowable_error, expectedv-actualv, x, expectedv, actualv, smps_per_period, master.render_deci)
					
					# Check actual value is within tolerance
					assert in_bounds(actualv, expectedv, allowable_error)

	
	# NOTE: Modulation cannot be tested using the Oscilloscope instrument as it is not enabled.
	# 		The SignalGenerator bitstream should be tested on its own with full modulation functionality enabled.
	@pytest.mark.parametrize("ch, source, depth, frequency", [
		#(1, 0, 0.5, 3)
		])
	def tes2_am_modulation(self, base_instrs, ch, source, depth, frequency):
		master = base_instrs[0]

		# Set a sampling frequency
		master.set_timebase(0,1.0) # 1 second
		master.synth_sinewave(1, 1.0, 10, 0)
		master.synth_sinewave(2, 1.0, 5, 0)
		master.synth_modulate(1, SG_MOD_AMPL, SG_MODSOURCE_INT, depth, frequency)
		master.commit()

		# Get sampling frequency
		fs = _OSC_ADC_SMPS / (master.decimation_rate * master.render_deci)
		fstep = fs / _OSC_SCREEN_WIDTH

		assert False

class Test_Trigger:
	'''
		This class tests Trigger modes of the Oscilloscope
	'''
	


	@pytest.mark.parametrize("edge, trig_level, waveform",
		itertools.product(
			[OSC_EDGE_RISING, OSC_EDGE_FALLING, OSC_EDGE_BOTH], 
			[-0.1, 0.0, 0.1, 0.3], 
			[SG_WAVE_SINE, SG_WAVE_SQUARE, SG_WAVE_TRIANGLE]))
	def test_triggered_edge(self, base_instrs, edge, trig_level, waveform):
		'''
			Test the triggered edge type and level are correct
		'''
		# Get the Master Moku
		master = base_instrs[0]

		# Set up the source signal to test triggering on
		trig_ch = 1
		source_freq = 100 #Hz
		source_vpp = 1.0
		source_offset = 0.0
		master.set_source(trig_ch, OSC_SOURCE_DAC)

		if waveform == SG_WAVE_SINE:
			master.synth_sinewave(trig_ch, source_vpp, source_freq, source_offset)
		elif waveform == SG_WAVE_SQUARE:
			master.synth_squarewave(trig_ch, source_vpp, source_freq, source_offset)
		elif waveform == SG_WAVE_TRIANGLE:
			master.synth_rampwave(trig_ch, source_vpp, source_freq, source_offset)
		else:
			print "Invalid waveform type"
			assert False

		# Set a symmetric timebase of ~10 cycles
		master.set_timebase(-5/source_freq,5/source_freq)

		# Sample number of trigger point given a symmetric timebase
		half_idx = (_OSC_SCREEN_WIDTH / 2) - 1

		# Trigger on correct DAC channel
		if trig_ch == 1:
			master.set_trigger(OSC_TRIG_DA1, edge, trig_level, hysteresis=0, hf_reject=False, mode=OSC_TRIG_NORMAL)
		if trig_ch == 2:
			master.set_trigger(OSC_TRIG_DA2, edge, trig_level, hysteresis=0, hf_reject=False, mode=OSC_TRIG_NORMAL)

		master.commit()

		for _ in range(5):
			frame = master.get_frame(timeout=5)
			if trig_ch == 1:
				ch_frame = frame.ch1
			elif trig_ch == 2:
				ch_frame = frame.ch2

			# Check for correct level unless we are on a square edge
			if not (waveform == SG_WAVE_SQUARE):
				assert in_bounds(trig_level,ch_frame[half_idx], 0.005)

			if(edge == OSC_EDGE_RISING):
				assert _is_rising(ch_frame[half_idx-1],ch_frame[half_idx])
			elif(edge == OSC_EDGE_FALLING):
				assert _is_falling(ch_frame[half_idx-1], ch_frame[half_idx])
			elif(edge == OSC_EDGE_BOTH):
				assert _is_rising(ch_frame[half_idx-1],ch_frame[half_idx]) or _is_falling(ch_frame[half_idx-1],ch_frame[half_idx])


	def _setup_trigger_mode_test(self, master, trig_mode, trig_lvl, source_vpp, source_offset, source_freq):
		# Set up the triggering and a DAC source to trigger on
		trig_ch = 1
		trig_level = trig_lvl
		trig_edge = OSC_EDGE_RISING

		trig_source_freq = source_freq
		trig_source_vpp = source_vpp
		trig_source_offset = source_offset

		timebase_cyc = 10.0

		master.set_source(trig_ch, OSC_SOURCE_DAC)
		master.set_timebase(0, (timebase_cyc/trig_source_freq))
		if trig_ch == 1:
			master.set_trigger(OSC_TRIG_DA1, trig_edge, trig_level, hysteresis = 0, hf_reject = False, mode = trig_mode)
		if trig_ch == 2:
			master.set_trigger(OSC_TRIG_DA2, trig_edge, trig_level, hysteresis = 0, hf_reject = False, mode = trig_mode)

		# Generate waveform to trigger off
		master.synth_sinewave(trig_ch, trig_source_vpp, trig_source_freq, trig_source_offset)
		master.commit()

		return timebase_cyc

	@pytest.mark.parametrize("freq",([20, 30, 40, 1e3, 10e3, 1e6, 10e6]))
	def test_trigger_mode_normal(self, base_instrs, freq):
		'''
			Tests 'Normal' trigger mode
		'''
		master = base_instrs[0]
		timebase_cyc = self._setup_trigger_mode_test(master, OSC_TRIG_NORMAL, 0.0, 1.0, 0.0, freq)
		# Sample number of trigger point given a symmetric timebase
		half_idx = (_OSC_SCREEN_WIDTH / 2) - 1

		frame_timeout = max(5,(1/freq) * 20)
		triggers_per_frame = min((freq/timebase_cyc)/master.framerate, OSC_MAX_TRIGRATE/master.framerate)

		# Case when trigger rate is greater than frame rate
		if triggers_per_frame > 2:
			waveformid = None

			for _ in range(20):
				frame = master.get_frame(timeout = frame_timeout)

				if waveformid is None: # Get the first ID
					waveformid = frame.waveformid
				else: 
					# Waveform ID has increased since last frame
					assert frame.waveformid > waveformid

					# The change in waveform ID is approximately the expected number of triggers per frame
					delta_id = frame.waveformid - waveformid
					assert in_bounds(triggers_per_frame, delta_id, max(triggers_per_frame*0.2, 1))

				waveformid = frame.waveformid
				# Debug print
				print("Waveform ID: %s, Frame ID: %s" % (waveformid, frame.frameid))
		
		# Case when trigger rate is slower than frame rate
		else:
			frames_per_trigger = 1.0/triggers_per_frame

			for _ in range(10):
				frame = master.get_frame(timeout = frame_timeout)
				waveformid = frame.waveformid
				frame_ctr = 0

				while (frame.waveformid == waveformid):
					frame_ctr = frame_ctr + 1
					frame = master.get_frame(timeout = frame_timeout)

				# The number of frames per trigger is approximately as expected (within 1 frame)
				assert in_bounds(frames_per_trigger, frame_ctr, max(frames_per_trigger+1,1))

				# Debug print
				print("Waveform ID: %s, Frame ID: %s, Frame Counter: %s" % (waveformid, frame.frameid, frame_ctr))


	def test_trigger_mode_normal_notrigger(self, base_instrs):
		'''
			Tests the case of Normal trigger mode when there are no trigger events
		'''
		master = base_instrs[0]

		# Set up the trigger source with a trigger level exceeding the peak voltage
		source_freq = 1e3
		source_vpp = 1.0
		source_offset = 0.0
		trig_lvl = 1.5
		timebase_cyc = self._setup_trigger_mode_test(master, OSC_TRIG_NORMAL, trig_lvl, source_vpp, source_offset, source_freq)

		# There should be no trigger events
		with pytest.raises(FrameTimeout):
			frame = master.get_frame(timeout = 5)
 

	def test_trigger_mode_auto_notrigger(self, base_instrs):
		'''
			Tests 'Auto' trigger mode
		'''
		master = base_instrs[0]

		# Set up the trigger source with a trigger level exceeding the peak voltage
		source_freq = 1e3
		source_vpp = 1.0
		source_offset = 0.0
		trig_lvl = 1.5
		timebase_cyc = self._setup_trigger_mode_test(master, OSC_TRIG_AUTO, trig_lvl, source_vpp, source_offset, source_freq)

		# Auto mode test - every frame should have maximum number of triggers
		waveformid = None
		delta_ids = []
		for _ in range(20):
			frame = master.get_frame(timeout = 5)
			if waveformid == None:
				waveformid = frame.waveformid
			else:
				delta_ids = delta_ids + [frame.waveformid - waveformid]
				waveformid = frame.waveformid

			# Debug print
			print("Waveform ID: %s, Frame ID: %s" % (frame.waveformid, frame.frameid))


		avg = sum(delta_ids)/float(len(delta_ids))
		assert in_bounds(avg, OSC_AUTO_TRIGRATE/master.framerate, 0.2)
		print("Delta IDs: %s, Avg: %f" % (delta_ids, avg))


	def test_trigger_mode_single(self, base_instrs):
		'''
			Tests 'Auto' trigger mode
		'''
		master = base_instrs[0]

		# Set up the trigger source with a trigger level exceeding the peak voltage
		trig_source_freq = 1e3
		trig_source_vpp = 1.0
		trig_source_offset = 0.0
		trig_lvl = 0.0
		timebase_cyc = self._setup_trigger_mode_test(master, OSC_TRIG_SINGLE, trig_lvl, trig_source_vpp, trig_source_offset, trig_source_freq)

		frame = master.get_frame(timeout=5)
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

	@pytest.mark.parametrize("ch", ([OSC_TRIG_CH1, OSC_TRIG_CH2, OSC_TRIG_DA1, OSC_TRIG_DA2]))
	def test_trigger_channels(self, base_instrs, ch):
		'''
			Tests triggering on ADC and DAC channels
		'''
		master = base_instrs[0]
		slave = base_instrs[1]

		trig_source_freq = [1e3, 1e3, 0.5e3, 2e3]
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
		master.set_timebase(-5/trig_source_freq[idx], 5/trig_source_freq[idx])
		master.commit()
		slave.commit()

		# Get a frame on the appropriate channel and check it is as expected
		frame = master.get_frame(timeout = 5)

		# Check the frame
		if ch == OSC_TRIG_CH1 or ch == OSC_TRIG_DA1:
			data = frame.ch1
		elif ch == OSC_TRIG_CH2 or ch == OSC_TRIG_DA2:
			data = frame.ch2
		else:
			print "Invalid trigger channel"
			assert False

		# Generate timesteps for the current timebase
		# Step size
		t1, t2 = master._get_timebase(master.decimation_rate, master.pretrigger, master.render_deci, master.offset)
		ts = numpy.cumsum([(t2 - t1) / _OSC_SCREEN_WIDTH]*len(data))

		# Crop the data if there are 'None' values at the end of the frame
		try:
			invalid_indx = data.index(None)
			data = data[0:data.index(None)]
			ts = ts[0:len(data)]
		except ValueError:
			pass

		# Curve fit the frame data to ensure correct waveform has been triggered
		bounds = ([0, 0, -0.2, trig_source_freq[idx]/2.0], [2.0, 2*math.pi, 0.2, 2.0*trig_source_freq[idx]])
		p0 = [trig_source_vpp[idx], 0, 0, trig_source_freq[idx]]
		params, cov = curve_fit(_sinewave, ts, data, p0 = p0, bounds=bounds)
		ampl = params[0]
		phase = params[1]
		offset = params[2]
		freq = params[3]

		plt.plot(ts,data)
		plt.show()

		print("Vpp: %f/%f, Frequency: %f/%f, Offset: %f/%f" % (trig_source_vpp[idx], ampl*2.0, trig_source_freq[idx], freq, trig_source_offset[idx], offset))
		#assert in_bounds(params[0])



		assert False


class Tes2_Timebase:
	'''
		Ensure the timebase is correct
	'''



class Tes2_Source:
	'''
		Ensure the source is set and rendered as expected
	'''
	@pytest.mark.parametrize("ch, amp",[
		(1, 0.2),
		(1, 0.5),
		(2, 0.1),
		(2, 1.0), 
		])
	def test_dac(self, master, ch, amp):
		i = master
		i.synth_sinewave(ch,amp,1e6,0)
		i.set_source(ch, OSC_SOURCE_DAC)
		i.set_timebase(0,2e-6)
		i.commit()

		# Max and min should be around ~amp
		frame = i.get_frame()
		assert in_bounds(max(getattr(frame, "ch"+str(ch))), amp, 0.05)
		assert in_bounds(min(getattr(frame, "ch"+str(ch))), amp, 0.05)

