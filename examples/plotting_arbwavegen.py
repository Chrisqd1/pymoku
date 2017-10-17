from pymoku import Moku
from pymoku.instruments import ArbWaveGen

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# generates  waveform so interpolation can be observed
signalx = [1,3,2,4,3,5,4,6,5,7,6,8,1,3,2,4,3,5,4,6,5,7,6,8,1,3,2,4,3,5,4,6,5,7,6,8,1,3,2,4,3,5,4,6,5,7,6,8]

# normalise the values to be between [-1, 1]
signalx = [x/max(signalx) for x in signalx]
signaly = signalx 

# Connect to your Moku by its device name
# Alternatively, use Moku.get_by_serial('#####') or Moku('192.168.###.###')
m = Moku.get_by_name('Moku')

# Prepare the ArbWaveformGenerator instrument
i = ArbWaveGen()
m.deploy_instrument(i)

try:
	# reset the device to defaults
	i.set_defaults()

	# writing values to lookup tables
	i.write_lut(ch = 1, data = signalx, mode = '1GS')
	i.write_lut(ch = 2, data = signaly, mode = '125MS')

	# use gen waveform to generate a signal from look up table
	i.gen_waveform(ch = 1, period = 1e-6, phase = 0, amplitude = 1, offset = 0.0, interpolation = False, dead_time = 0, dead_voltage = 0.0)
	i.gen_waveform(ch = 2, period = 1e-6, phase = 0, amplitude = 1, offset = 0.0, interpolation = True, dead_time = 0, dead_voltage = 0.0)

	# sync the phase from channel 2 to channel 1
	i.sync_phase(ch = 2)
	
	# set up the oscilloscope to read data from the Output channels
	i.set_source(1, 'out', lmode='round')
	i.set_source(2, 'out', lmode='round')
	i.set_trigger('out1', 'rising', 0.0, hysteresis=True, mode='auto')
	i.set_timebase(0, 2e-6)
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
