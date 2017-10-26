#
# pymoku example: Basic Signal Generator
#
# This example demonstrates how you can use the Signal Generator instrument to
# generate an amplitude modulated sinewave on Channel 1, and un-modulated 
# squarewave on Channel 2.
#
# (c) 2017 Liquid Instruments Pty. Ltd.
#
from pymoku import *
from pymoku.instruments import WaveformGenerator
import time

# Connect to your Moku by its device name
# Alternatively, use Moku.get_by_serial('#####') or Moku('192.168.###.###')
#m = Moku.get_by_name('Bode')
m = Moku('192.168.69.65')

# Prepare the Signal Generator instrument
i = WaveformGenerator()

# Deploy the Signal Generator to your Moku
m.deploy_instrument(i)
try:
	# Generate a 1.0Vpp 1MHz Sinewave on Channel 1
	i.gen_sinewave(1, 1.0, 50)

	# Generate a 1.0Vpp 2MHz Squarewave on Channel 2
	# 30% Duty cycle, 10% Rise time, 10% Fall time
	i.gen_squarewave(2, 1.0, 1, risetime=0.1, falltime=0.1, duty=0.3)

	# Amplitude modulate the Channel 1 sinewave with another internally-generated sinewave.
	# 100% modulation depth at 10Hz.
	i.gen_modulate(1, 'amplitude', 'internal', 1, 1)

	time.sleep(20)

	i.set_trigger(1, mode = 'ncycle', ncycles = 1, trigger_source = 'dac', trigger_threshold = 0)

finally:
	m.close()
