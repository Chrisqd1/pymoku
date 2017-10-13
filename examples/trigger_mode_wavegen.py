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
m = Moku('192.168.69.222')

# Prepare the Signal Generator instrument
i = WaveformGenerator()

# Deploy the Signal Generator to your Moku
m.deploy_instrument(i)
try:
	# Channel 1 generates a 1.0Vpp 5Hz Sinewave 
	i.gen_sinewave(1, 1.0, 5)
	# Channel 2 generates a Squarewave 2 vpp 1Hz
	i.gen_squarewave(2, 2.0, 1, duty=0.3, risetime = 0.1, falltime=0.1)

	i.set_trigger_threshold(ch = 1, adc = 0.5, dac = 0.5)
	
	# set the trigger mode on channel 1 to gateway	
	i.set_trigger(ch = 1, mode = 'gateway', trigger_source = 'adc')
	input("Tigger is in gateway mode now. Load next trigger?")

	i.set_trigger(ch = 1, mode = 'startmode', trigger_source = 'adc')
	input("Tigger is in start mode. Load next trigger?")

	i.set_trigger(ch = 1, mode = 'ncycle', trigger_source = 'adc', ncycles = 4)
	input("Tigger is in ncycle mode. Load next trigger?")

	i.set_trigger(ch = 1, mode = 'sweep', trigger_source = 'adc', sweep_init_freq = 1.0, sweep_final_freq = 5.0, sweep_duration = 10.0)
	input("Tigger is in sweep mode. Close the waveform?")
finally:
	m.close()
