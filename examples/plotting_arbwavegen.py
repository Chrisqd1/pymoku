from pymoku import Moku
from pymoku.instruments import ArbWaveGen
import struct, logging, math
import numpy as np

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

import pickle, base64, zlib

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s::%(message)s')
logging.getLogger('pymoku').setLevel(logging.INFO)

ARB_MODE_1000 = 0x0
ARB_MODE_500 = 0x1
ARB_MODE_250 = 0x2
ARB_MODE_125 = 0x3

# generates a funny looking waveform so interpolation can be observed
signalx = [1,3,2,4,3,5,4,6,5,7,6,8,1,3,2,4,3,5,4,6,5,7,6,8,1,3,2,4,3,5,4,6,5,7,6,8,1,3,2,4,3,5,4,6,5,7,6,8]

# normalise the values to be between [-1, 1]
signaly = [x/max(signalx) for x in signalx]

# beeing lacy and just copied the signal across
signalx = signaly 


# connect to moku device
m = Moku('192.168.69.222')
i = ArbWaveGen()
m.deploy_instrument(i)

try:
	# reset the device to defaults
	i.set_defaults()

	# writing values to lookup tables
	i.write_lut(1, signalx, ARB_MODE_1000)
	i.write_lut(2, signaly, ARB_MODE_125)

	# use gen waveform to generate a signal from look up table (ch, period, phase, amplitude, offset, interpolation, dead_time, dead_value, fiftyr)
	i.gen_waveform(1, 1e-6, 0, 1, 0.0, False, 0, 0.0, False)
	i.gen_waveform(2, 1e-6, 0, 1, 0.0, True, 0, 0.0, False)

	# sync the phase from channel 2 to channel 1
	i.sync_phase(2)
	
	# reset the phase(restart phase from 0)
	i.reset_phase(2)
	
	# set up the oscilloscope to read data from the Output channels
	i.set_source(1, 'out', lmode='round')
	i.set_source(2, 'out', lmode='round')
	i.set_trigger('out1', 'rising', 0.0, hysteresis=True, mode='auto')
	i.set_timebase(0, 0.001)
	data = i.get_realtime_data()

	# Set up the plotting parameters
	plt.ion()
	plt.show()
	plt.grid(b=True)
	plt.ylim([-0.5,2])
	plt.xlim([data.time[0], data.time[-1]])

	line1, = plt.plot([])
	line2, = plt.plot([])
	
	# Configure labels for axes
	ax = plt.gca()
	ax.xaxis.set_major_formatter(FuncFormatter(data.get_xaxis_fmt))
	ax.yaxis.set_major_formatter(FuncFormatter(data.get_yaxis_fmt))
	ax.fmt_xdata = data.get_xcoord_fmt
	ax.fmt_ydata = data.get_ycoord_fmt

	# This loops continuously updates the plot with new data
	while True:
		# Get new data
		data = i.get_realtime_data()

		# Update the plot
		line1.set_ydata(data.ch1)
		line2.set_ydata(data.ch2)
		line1.set_xdata(data.time)
		line2.set_xdata(data.time)
		plt.pause(0.1)

finally:
	m.close()
