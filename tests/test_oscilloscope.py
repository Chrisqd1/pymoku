import itertools
import pytest, time
from pymoku import Moku
from pymoku.instruments import *
from pymoku._oscilloscope import _OSC_SCREEN_WIDTH, _OSC_ADC_SMPS
from pymoku._siggen import SG_MOD_NONE, SG_MOD_AMPL, SG_MOD_PHASE, SG_MOD_FREQ, SG_MODSOURCE_INT, SG_MODSOURCE_ADC, SG_MODSOURCE_DAC, SG_WAVE_SINE, SG_WAVE_SQUARE, SG_WAVE_TRIANGLE, SG_WAVE_DC
import conftest
import numpy

# Assertion helpers
def in_bounds(v, center, err):
	if (v is None) or (center is None):
		return True
	return abs(v - center) < abs(err)

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

class Test_Siggen:
	'''
		This class tests the correctness of the embedded signal generator 
	'''

	@pytest.mark.parametrize("ch, vpp, freq, offset, waveform", 
		itertools.product([1,2],[0, 0.5, 1.0],[1e3, 1e6], [0, 0.3, 0.5], [SG_WAVE_SINE, SG_WAVE_SQUARE, SG_WAVE_TRIANGLE]))
	def test_waveform_amp(self, base_instrs, ch, vpp, freq, offset, waveform):
		'''
			Test the max/min amplitude of the waveforms are correct
		'''
		base_instr = base_instrs[0]


		# Set timebase to allow for 5 cycles
		if freq == 0:
			tspan = 1.0 # Set DC to 1 second
		else:
			tspan = (1.0/freq) * 5.0
		base_instr.set_timebase(0,tspan)

		# Loop DAC to input to measure the generated waveforms
		base_instr.set_source(ch,OSC_SOURCE_DAC)
		if(ch==1):
			base_instr.set_trigger(OSC_TRIG_DA1, OSC_EDGE_RISING, 0)
		else:
			base_instr.set_trigger(OSC_TRIG_DA2, OSC_EDGE_RISING, 0)

		# Generate the desired waveform
		if waveform == SG_WAVE_SINE:
			base_instr.synth_sinewave(ch, vpp, freq, offset)
		elif waveform == SG_WAVE_SQUARE:
			base_instr.synth_squarewave(ch, vpp, freq,offset=offset)
		elif waveform == SG_WAVE_TRIANGLE:
			base_instr.synth_rampwave(ch, vpp, freq, offset=offset)
		base_instr.commit()

		# 5mV Tolerance on max/min values
		tolerance = 0.005


		# Test amplitudes on a few frames worth of generated output
		for _ in range(10):
			frame = base_instr.get_frame(wait=True)
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
	def test_waveform_freq(self, base_instrs, ch, vpp, freq, waveform):
		'''
			Test the frequency of generated waveforms

			This is done by checking that the amplitude of generated signals is constant as we jump across multiple cycles
			of the waveform.
		'''
		base_instr = base_instrs[0]

		# Set timebase to allow for 5 cycles
		number_periods = 5
		period = (1.0/freq)
		tspan = period * number_periods
		base_instr.set_timebase(0,tspan)

		# Loop DAC output to input for measurement
		base_instr.set_source(ch,OSC_SOURCE_DAC)
		base_instr.set_xmode(OSC_FULL_FRAME)
		if(ch==1):
			base_instr.set_trigger(OSC_TRIG_DA1, OSC_EDGE_RISING, 0)
		else:
			base_instr.set_trigger(OSC_TRIG_DA2, OSC_EDGE_RISING, 0)

		# Get back actual timebase (this will not be precisely 5 cycles due to rounding)
		(tstart, tend) = base_instr._get_timebase(base_instr.decimation_rate, base_instr.pretrigger, base_instr.render_deci, base_instr.offset)

		# Compute the approximate number of samples per waveform period
		time_per_smp = (tend-tstart)/_OSC_SCREEN_WIDTH
		smps_per_period = period/time_per_smp

		# Generate the waveform type to be tested
		# Define the offset into each frame that we should start measuring amplitudes from
		if waveform == SG_WAVE_SINE:
			base_instr.synth_sinewave(ch,vpp,freq,0.0)
			start_xs = [0, int(smps_per_period/2), int(smps_per_period/3), int(smps_per_period/4), int(smps_per_period/8), int(3*smps_per_period/4)]
		elif waveform == SG_WAVE_SQUARE:
			base_instr.synth_squarewave(ch, vpp, freq)
			# Don't start on a squarewave edge
			start_xs = [int(smps_per_period/3), int(3*smps_per_period/4), int(2*smps_per_period/3), int(smps_per_period/8), int(7*smps_per_period/8)]
		elif waveform == SG_WAVE_TRIANGLE:
			base_instr.synth_rampwave(ch, vpp, freq)
			start_xs = [0, int(smps_per_period/2), int(smps_per_period/3), int(smps_per_period/4), int(smps_per_period/8), int(3*smps_per_period/4)]
		base_instr.commit()

		# Allow 2% variation in amplitude
		allowable_error = 0.02*vpp

		# Workaround for ensuring we receive a valid waveform in the frame
		# The squarewave generator has unpredictable initial conditions currently
		# So we want to skip the first frame
		time.sleep(3*(tend-tstart))
		base_instr.flush()
		base_instr.get_frame()

		# Test multiple frames worth
		for _ in range(5):

			frame = base_instr.get_frame()
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
					# print "Allowable tolerance: %.10f, Error: %.10f, Frame index: %d, Expected value: %.10f, Actual value: %.10f, Samples per period: %d, Render deci: %f" % (allowable_error, expectedv-actualv, x, expectedv, actualv, smps_per_period, base_instr.render_deci)
					
					# Check actual value is within tolerance
					assert in_bounds(actualv, expectedv, allowable_error)

	
	# NOTE: Modulation cannot be tested using the Oscilloscope instrument as it is not enabled.
	# 		The SignalGenerator bitstream should be tested on its own with full modulation functionality enabled.
	@pytest.mark.parametrize("ch, source, depth, frequency", [
		#(1, 0, 0.5, 3)
		])
	def tes2_am_modulation(self, base_instrs, ch, source, depth, frequency):
		base_instr = base_instrs[0]

		# Set a sampling frequency
		base_instr.set_timebase(0,1.0) # 1 second
		base_instr.synth_sinewave(1, 1.0, 10, 0)
		base_instr.synth_sinewave(2, 1.0, 5, 0)
		base_instr.synth_modulate(1, SG_MOD_AMPL, SG_MODSOURCE_INT, depth, frequency)
		base_instr.commit()

		# Get sampling frequency
		fs = _OSC_ADC_SMPS / (base_instr.decimation_rate * base_instr.render_deci)
		fstep = fs / _OSC_SCREEN_WIDTH

		assert False

class Test_Trigger:
	'''
		This class tests Trigger modes of the Oscilloscope
	'''
	
	@pytest.mark.parametrize("trig_ch, edge, trig_level, waveform",
		itertools.product([1,2],
			[OSC_EDGE_RISING, OSC_EDGE_FALLING, OSC_EDGE_BOTH], 
			[-0.1, 0.0, 0.1, 0.3], 
			[SG_WAVE_SINE, SG_WAVE_SQUARE, SG_WAVE_TRIANGLE]))
	def test_triggered_edge(self, base_instrs, trig_ch, edge, trig_level, waveform):
		'''
			Test the triggered edge type and level are correct
		'''
		base_instr = base_instrs[0]

		# Set up the source signal to test triggering on
		source_freq = 100 #Hz
		source_vpp = 1.0
		source_offset = 0.0
		base_instr.set_source(trig_ch, OSC_SOURCE_DAC)
		if waveform == SG_WAVE_SINE:
			base_instr.synth_sinewave(trig_ch, source_vpp, source_freq, source_offset)
		elif waveform == SG_WAVE_SQUARE:
			base_instr.synth_squarewave(trig_ch, source_vpp, source_freq, source_offset)
		elif waveform == SG_WAVE_TRIANGLE:
			base_instr.synth_rampwave(trig_ch, source_vpp, source_freq, source_offset)
		else:
			print "Invalid waveform type"
			assert False

		# Set a symmetric timebase of ~10 cycles
		base_instr.set_timebase(-5/source_freq,5/source_freq)

		# Sample number of trigger point given a symmetric timebase
		half_idx = (_OSC_SCREEN_WIDTH / 2) - 1

		# Trigger on correct DAC channel
		if trig_ch == 1:
			base_instr.set_trigger(OSC_TRIG_DA1, edge, trig_level, hysteresis=0, hf_reject=False, mode=OSC_TRIG_NORMAL)
		if trig_ch == 2:
			base_instr.set_trigger(OSC_TRIG_DA2, edge, trig_level, hysteresis=0, hf_reject=False, mode=OSC_TRIG_NORMAL)

		base_instr.commit()

		for _ in range(5):
			frame = base_instr.get_frame(timeout=5)
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
	def test_dac(self, base_instr, ch, amp):
		i = base_instr
		i.synth_sinewave(ch,amp,1e6,0)
		i.set_source(ch, OSC_SOURCE_DAC)
		i.set_timebase(0,2e-6)
		i.commit()

		# Max and min should be around ~amp
		frame = i.get_frame()
		assert in_bounds(max(getattr(frame, "ch"+str(ch))), amp, 0.05)
		assert in_bounds(min(getattr(frame, "ch"+str(ch))), amp, 0.05)

