#
# pymoku example: trigger modes for waveform generation
#
# This example demonstrates how you can use the Waveform Generator instrument to
# generate a triggered sinewave on Channel 1 and 2 using different tigger sources
#
# (c) 2019 Liquid Instruments Pty. Ltd.
#
from pymoku import Moku
from pymoku.instruments import WaveformGenerator

# Connect to your Moku by its device name
# Alternatively, use Moku.get_by_serial('#####') or Moku('192.168.###.###')
m = Moku.get_by_name('Moku')

try:
	i = m.deploy_or_connect(WaveformGenerator)

	# Channel 1 generates a 1.0Vpp 5Hz Sinewave
	i.gen_sinewave(1, 1.0, 5)
	# Channel 2 generates a Squarewave 2.0Vpp 1Hz
	i.gen_squarewave(2, 2.0, 1)

	# Channel 1's sinewave is gated on ADC Input 1 exceeding 0.5V
	i.set_trigger(1, 'gated', trigger_source='in', trigger_threshold=0.5)

	# Channel 2's square wave will sweep from 1Hz to 5Hz over 10 seconds after being triggered
	# at 0.5V from ADC Input 2 (the input paired with this output)
	i.set_trigger(2, 'sweep', sweep_start_freq=1.0, sweep_end_freq=5.0, sweep_duration=10.0, trigger_source='in', trigger_threshold=0.5)

finally:
	m.close()
