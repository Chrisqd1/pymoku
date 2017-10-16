from pymoku import Moku
from pymoku.instruments import ArbWaveGen
import numpy as np


#generate a signal the the Arb Waveform Gen should generate on the output
fs = 100 	# sample rate 
f = 2 		# the frequency of the signal

# the points on the x axis for plotting
x = np.arange(fs) 	

# compute the value (amplitude) of the sin wave at the for each sample
signalx = [ np.sin(2*np.pi*f * (i/fs)) for i in np.arange(fs)]
signaly = [ np.sin(2*np.pi*f * (i/fs)) for i in np.arange(fs)]

amplitudex = max(signalx)
amplitudey = max(signaly)

xdatanew = [x/amplitudex for x in signalx]
ydatanew = [y/amplitudey for y in signaly]

# Connect to your Moku by its device name
# Alternatively, use Moku.get_by_serial('#####') or Moku('192.168.###.###')
m = Moku.get_by_name('Moku')

# Prepare the ArbWaveformGenerator instrument
i = ArbWaveGen()
m.deploy_instrument(i)

try:
	i.write_lut(1, xdatanew, 3)
	i.write_lut(2, ydatanew, 3)

	i.gen_waveform(1, 1e-6, 0, 1, 0.0, False, 0, 0.0, False)
	i.gen_waveform(2, 1e-6, 0, 1, 0.0, True, 0, 0.0, False)


finally:
	m.close()
