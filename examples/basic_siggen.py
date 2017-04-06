from pymoku import Moku, ValueOutOfRangeException
from pymoku.instruments import *
import time

# Use Moku.get_by_serial() or get_by_name() if you don't know the IP
m = Moku.get_by_name("example")
i = SignalGenerator()
m.deploy_instrument(i)

try:
	# Generate a 1.0Vpp 1MHz Sinewave on Channel 1
	i.gen_sinewave(1, 1.0, 1e6)
	
	# Generate a 1.0Vpp 2MHz Squarewave on Channel 2 
	# 30% Duty cycle, 10% Rise time, 10% Fall time
	i.gen_squarewave(2, 1.0, 2e6, risetime=0.1, falltime=0.1, duty=0.3)

	# Amplitude modulate the CH1 sinewave with another internally-generated sinewave.
	# 100% modulation depth at 10Hz.
	i.gen_modulate(1, SG_MOD_AMPL, SG_MODSOURCE_INT, 1, 10)
	i.commit()
finally:
	m.close()
