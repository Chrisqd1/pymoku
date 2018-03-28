#
# pymoku example: Arbitrary waveform generator
#
# This example demonstrates how you can generate and output arbitrary
# waveforms using Moku:AWG
#
# (c) 2017 Liquid Instruments Pty. Ltd.
#
from pymoku import Moku
from pymoku.instruments import ArbitraryWaveGen
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

import logging
logging.basicConfig(level=logging.DEBUG)

#generate a signal the the Arb Waveform Gen should generate on the output
t = np.linspace(0, 1, 100) # Evaluate our waveform at 100 points

# Simple square wave (can also use scipy.signal)
sq_wave = np.array([-1.0 if x < 0.5 else 1.0 for x in t])

# More interesting waveform. Note that we have to normalize this waveform
# to the range [-1, 1]
not_sq = np.zeros(len(t))
for h in np.arange(1, 15, 2):
    not_sq += (4 / (np.pi * h)) * np.cos(2 * np.pi * h * t)

not_sq = not_sq / max(not_sq)
stairs = np.linspace(-0.5,1,21)
pulse = [-1,1]

#plt.plot(not_sq)
#plt.show()

# Connect to your Moku by its device name
# Alternatively, use Moku.get_by_serial('#####') or Moku('192.168.###.###')
m = Moku.get_by_name('TurtleOne',force=True)
i = ArbitraryWaveGen()
# Prepare the ArbitraryWaveGen instrument
m.deploy_instrument(i)

try:
	# Load the waveforms to the device. This doesn't yet generate an output as we haven't
	# set the amplitude, frequency etc; this only defines the shape.
	i.write_lut(1, stairs)
	i.write_lut(2, pulse)

	i.gen_waveform(1, period=0.01, amplitude=1.0, interpolation=False, dead_voltage=0) 	# Waveform output
	i.gen_waveform(2, period=0.5, amplitude=1.0, interpolation=False) 	# Trigger pulse output

	i.set_waveform_trigger(1, 'in1', 'rising', 0) # Trigger on ADC1

	i.set_waveform_trigger_output(1, single=True, hold_last=True)
	#i.sync_phase()

	# We have configurable on-device linear interpolation between LUT points. Normally
	# interpolation is a good idea, but for sharp edges like square waves it will
	# improve jitter but reduce rise-time. Configure whatever's suitable for your application.
	#i.gen_waveform(1, period=1e-6, amplitude=0.3, interpolation=False, dead_time=0, dead_voltage=0.5, en=False )
	#i.gen_waveform(1, period=1e-6, amplitude=1.0, phase=0.25, interpolation=True, dead_time=0, dead_voltage=0.5, en=False )

	i.enable_output()
	"""
	# Test out the sweep generator class
	for s in [i._sweep1, i._sweep2]:
		s.waveform = s.WAVE_TYPE_UPDOWN
		s.start = 2
		s.stop = 2^32
		s.step = 2^10
		s.duration = 2^12
		s.hold_last = False
		s.wait_for_trig = True

		print "Waveform:", s.waveform
		print "Start:", s.start
		print "Stop:", s.stop
		print "Step:", s.step
		print "Duration:", s.duration
		print "Wait for Trig:", s.wait_for_trig
		print "Hold last:", s.hold_last
	"""

finally:
	m.close()
