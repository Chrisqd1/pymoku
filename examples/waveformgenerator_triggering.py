#
# pymoku example: trigger modes for waveform generation
#
# This example demonstrates how you can use the Waveform Generator instrument to
# generate a triggered sinewave on Channel 1 and 2 using different tigger sources 
#
# (c) 2017 Liquid Instruments Pty. Ltd.
#
from pymoku import *
from pymoku.instruments import WaveformGenerator
import time

# Connect to your Moku by its device name
# Alternatively, use Moku.get_by_serial('#####') or Moku('192.168.###.###')
m = Moku.get_by_name('Moku')

# Prepare the Signal Generator instrument
i = WaveformGenerator()

# Deploy the Signal Generator to your Moku
m.deploy_instrument(i)
try:
	# Channel 1 generates a 1.0Vpp 5Hz Sinewave 
	i.gen_sinewave(1, 1.0, 5)
	# Channel 2 generates a Squarewave 2 vpp 1Hz
	i.gen_squarewave(2, 2.0, 1)
	
	# if the trigger_source that you connect a trigger signal accordingly (if not used 'external' is used by default)
	# set the trigger mode on channel 1 to gated (ch, mode, trigger_source, trigger_threshold)
	i.set_trigger(ch = 1, mode = 'gated', trigger_source = 'external', trigger_threshold = 0.5)

	# set the trigger mode on channel 1 to sweep (ch, mode, sweep_init_freq, sweep_final_freq, sweep_duration, trigger_source, trigger_threshold)
	i.set_trigger(ch = 2, mode = 'sweep', sweep_init_freq = 1.0, sweep_final_freq = 5.0, sweep_duration = 10.0, trigger_source = 'in', trigger_threshold = 0.5)

finally:
	m.close()
