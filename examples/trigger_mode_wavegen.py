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

	# configure the trigger threshold on channel 1 to default (0.0 V)
	i.set_trigger_threshold(ch = 1, adc = 0.5 )

	# set the trigger source  for channel 1 to ADC
	i.set_trigger_source(ch = 1, trigger_source = 'adc')
	
	# set the trigger mode on channel 1 to gateway	
	#i.set_trigger_mode(ch = 1, mode = 'gateway')
	#i.set_trigger_mode(ch = 1, mode = 'startmode')
	#i.set_trigger_mode(ch = 1, mode = 'ncycle', ncycles = 3)
	i.set_trigger_mode(ch = 1, mode= 'sweep', sweep_final_freq = 10.0, sweep_duration = 1.0)

finally:
	#m.close()
	print("trigger set up")