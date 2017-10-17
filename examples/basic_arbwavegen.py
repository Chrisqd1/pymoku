from pymoku import Moku
from pymoku.instruments import ArbWaveGen
import numpy as np
import time

#generate a signal the the Arb Waveform Gen should generate on the output	

Fs = 100 #a lot more than twice per period
t = np.linspace(0,2,201) #two cycles, 100 points each

sqwave = np.sign(np.sin(2*np.pi*t)) #an actual square wave

not_sq = np.zeros(len(t))
for h in np.arange(1,15,2):
    not_sq += (4/(np.pi*h))*np.cos(2*np.pi*h*t)

not_sq = not_sq /max(not_sq)

# Connect to your Moku by its device name
# Alternatively, use Moku.get_by_serial('#####') or Moku('192.168.###.###')
m = Moku.get_by_name('Moku')

# Prepare the ArbWaveformGenerator instrument
i = ArbWaveGen()
m.deploy_instrument(i)

try:
	i.write_lut(ch = 1, data = not_sq, mode = '1GS')
	i.write_lut(ch = 2, data = sqwave, mode = '1GS')

	i.gen_waveform(ch = 1, period = 1e-6, phase = 0, amplitude = 1, offset = 0.0, interpolation = False, dead_time = 0, dead_voltage = 0.0)
	i.gen_waveform(ch = 2, period = 1e-6, phase = 0, amplitude = 1, offset = 0.0, interpolation = True, dead_time = 0, dead_voltage = 0.0)

	time.sleep(30)

finally:
	m.close()
