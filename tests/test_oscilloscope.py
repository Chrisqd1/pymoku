import pytest
from pymoku import Moku
from pymoku.instruments import *
from pymoku._oscilloscope import _OSC_SCREEN_WIDTH
import conftest
import numpy

def in_bounds(v, center, err):
	return abs(v - center) < abs(err)

class Test_Siggen:

	# Set the timebase and check it correctly sets the decimation rate
	@pytest.mark.parametrize("t1, t2", [
		(0, 1),
		(0, 1e-1),
		(0, 1e-2),
		(-1,1),
		(-2,1),
		(-0.02,1.2),
		(-10,1e-6)
		])
	def _1test_timebase(self, base_instr, t1, t2):
		base_instr.set_timebase(t1,t2)
		base_instr.commit()
		timebase_res = base_instr._get_timebase(base_instr.decimation_rate, base_instr.pretrigger, base_instr.render_deci, base_instr.offset)
		print timebase_res
		assert False

	'''
		Test the generated output waveforms are as expected
	'''
	@pytest.mark.parametrize("ch, vpp, freq, offset", [
		(1, 1.0, 10.0, 0),
		(1, 0.5, 10.0, 0),
		(1, 0.5, 33.3, 0.3),
		(1, 0.5, 100e3, 0.3),
		(1, 0.1, 100e3, 0.5),
		(2, 1.0, 100e3, 0.3),
		#(2, 2.0, 100e3, 0) # 2.0Vpp is apparently out of range in siggen
		])
	def test_sinewave_amplitude(self, base_instr, ch, vpp, freq, offset):
		# Generate an output sinewave and loop to input
		# Ensure the amplitude is right
		# Ensure the frequency seems correct as well

		# Timebase should allow ~5 cycles of input wave
		tspan = (1.0/freq) * 5.0
		base_instr.set_timebase(0,tspan)
		# Loop back output as input source and trigger on it
		base_instr.set_source(ch,OSC_SOURCE_DAC)
		if(ch==1):
			base_instr.set_trigger(OSC_TRIG_DA1, OSC_EDGE_RISING, 0)
		else:
			base_instr.set_trigger(OSC_TRIG_DA2, OSC_EDGE_RISING, 0)
		# Generate the desired sinewave
		base_instr.synth_sinewave(ch,vpp,freq,offset)
		base_instr.commit()

		# 2% Tolerance on max/min values
		tolerance = 0.002 * vpp;

		# Get a few frames and test that the max amplitudes of the generated signals are within bounds
		for n in range(10):
			frame = base_instr.get_frame(timeout=5)
			if(ch==1):
				maxval = max(x for x in frame.ch1 if x is not None)
				minval = min(x for x in frame.ch1 if x is not None)
			else:
				maxval = max(x for x in frame.ch2 if x is not None)
				minval = min(x for x in frame.ch2 if x is not None)
			assert in_bounds(maxval, (vpp/2.0)+offset, tolerance)
			assert in_bounds(minval, (-1*(vpp/2.0) + offset), tolerance)

	@pytest.mark.parametrize("ch, vpp, freq", [
		(1, 1.0, 1),
		(1, 1.0, 2),
		(1, 1.0, 100),
		(1, 1.0, 1e3),
		(1, 1.0, 100e3),
		(1, 1.0, 1e6 ),
		(1, 1.0, 50e6),
		(1, 1.0, 1e6),
		(1, 1.0, 3e6),
		(2, 0.5, 3e6)
		])
	def test_sinewave_frequency(self, base_instr, ch, vpp, freq):
		# Set timebase of 5 periods
		number_periods = 5
		period = (1.0/freq)
		tspan = period * number_periods
		base_instr.set_timebase(0,tspan)

		base_instr.set_source(ch,OSC_SOURCE_DAC)
		if(ch==1):
			base_instr.set_trigger(OSC_TRIG_DA1, OSC_EDGE_RISING, 0)
		else:
			base_instr.set_trigger(OSC_TRIG_DA2, OSC_EDGE_RISING, 0)

		# Generate the desired sinewave
		base_instr.synth_sinewave(ch,vpp,freq,0.0)
		base_instr.commit()

		# Figure out the timebase of frames
		(tstart, tend) = base_instr._get_timebase(base_instr.decimation_rate, base_instr.pretrigger, base_instr.render_deci, base_instr.offset)

		time_per_smp = (tend-tstart)/_OSC_SCREEN_WIDTH 	# Timestep per sample
		smps_per_period = period/time_per_smp 			# Number of samples before a period is reached

		# 2% amplitude tolerance
		allowable_error = 0.02*vpp

		# Test multiple frames
		for n in range(10):
			frame = base_instr.get_frame()
			if(ch==1):
				ch_frame = frame.ch1
			if(ch==2):
				ch_frame = frame.ch2

			# Start checking at different points along the waveform
			for start_x in [0, int(smps_per_period/2), int(smps_per_period/3), int(smps_per_period/4), int(smps_per_period/8)]:
				# Amplitude expected at multiples of periods along the waveform
				expectedv = ch_frame[start_x]

				# Skip along the waveform, 1 period at a time
				for i in range(number_periods-1):
					x = start_x + int(round(i*smps_per_period))

					actualv = ch_frame[x]

					# Debugging info
					print "Allowable tolerance: %.10f, Error: %.10f, Frame index: %d, Expected value: %.10f, Actual value: %.10f, Samples per period: %d, Render deci: %f" % (allowable_error, expectedv-actualv, x, expectedv, actualv, smps_per_period, base_instr.render_deci)
					
					# Check actual value is within tolerance
					assert in_bounds(actualv, expectedv, allowable_error)


	#def test_squarewave_amplitude(self, base_instr)


class Tes2_Trigger:
	'''
		We want this class to test everything around triggering settings for the oscilloscope
	'''

	@pytest.mark.parametrize("ch, edge, amp", [
		(OSC_TRIG_CH1, OSC_EDGE_RISING, 0.0),
		(OSC_TRIG_CH1, OSC_EDGE_RISING, 0.5),
		(OSC_TRIG_CH1, OSC_EDGE_RISING, 1.0),
		])
	def test_triggered_amplitude(self, base_instr, ch, edge, amp):
		'''
			Ensure that the start of the frame is the expected amplitude (within some error)
		'''
		i = base_instr
		allowable_error = 0.1 # Volts

		# Enforce buffer/frame offset of zero
		i.set_timebase(0,2e-6)
		# Set the trigger
		i.set_trigger(OSC_TRIG_CH1, OSC_EDGE_RISING, amp, hysteresis=0, hf_reject=False, mode=OSC_TRIG_NORMAL)
		i.commit()

		for n in range(10):
			frame = i.get_frame(timeout=5)
			print "Start of frame value: %.2f" % (frame.ch1[0])
			assert in_bounds(frame.ch1[0], amp, allowable_error)

		assert 0

	def test_triggered_edge(self, base_instr):
		'''
			Ensure the edge type looks right
		'''
		assert 1 == 1


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

