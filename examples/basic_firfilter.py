from pymoku import Moku
from pymoku.instruments import FIRFilter
import numpy as np
from scipy import signal
import time

import matplotlib
import matplotlib.pyplot as plt
from math import floor

FS = 125e6 / 500
length = 500000
amp = 2**12
f0 = 1e3
dec = 32

filt_coeff = []
with open('FIRKernal.csv', 'r') as csv:
	for l in csv:
		filt_coeff.append(map(float,  [x.strip() for x in l.split(',')] ))

#filt1 = [1.0] + [0.0]*(dec*29-1)
#filt1 = [1.0/(dec*29)]*(dec*29)
filt1 = filt_coeff[0]
print(len(filt1))

# Connect to your Moku by its device name
# Alternatively, use Moku.get_by_serial('#####') or Moku('192.168.###.###')
m = Moku('192.168.69.53', load_instruments=True, force = True)

# Prepare the ArbWaveformGenerator instrument
i = FIRFilter()
m.deploy_instrument(i)

try:

	i.set_defaults()
	i._set_frontend(1, fiftyr=True, atten=False, ac=False)
	i.set_trigger('in1', 'rising', 0.00, hysteresis=True)
	i.set_timebase(-25e-6,400e-6)

	i.set_source(1, 'in')
	i.set_source(2, 'out')

	i.set_offset_gain(ch = 1, output_scale = 0.5)
	i.set_samplerate(ch = 1, decimation_factor=dec)

	i.write_coeffs(1, filt1)
	i.commit()
	i.write_coeffs(2, filt2)
	i.commit()

	i._set_mmap_access(True)
	error = i._moku._receive_file('j', '.lutdata_moku.dat', 511 * 40 * 4 * 2)	
	i._set_mmap_access(False)

	i.link = False
	i.commit()

	data = i.get_realtime_data()
	# Set up the plotting parameters
	plt.ion()
	plt.show()
	plt.grid(b=True)
	plt.ylim([-2,2])
	plt.xlim([data.time[0], data.time[-1]])

	line1, = plt.plot([])
	line2, = plt.plot([])

	# This loops continuously updates the plot with new data
	while True:
		# Get new data
		data = i.get_realtime_data()

		# Update the plot
		# psd = signal.welch(data.ch1, fs=FS)
		# line1.set_ydata(psd[1])
		# line1.set_xdata(psd[0])

		line1.set_ydata(data.ch1)
		line2.set_ydata(data.ch2)
		line1.set_xdata(data.time)
		line2.set_xdata(data.time)
		plt.pause(0.001)


finally:
	m.close()
