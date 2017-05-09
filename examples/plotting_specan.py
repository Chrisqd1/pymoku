#
# pymoku example: Plotting Spectrum Analyser
#
# This example demonstrates how you can configure the Spectrum Analyser 
# instrument and plot its spectrum data in real-time. It also shows how
# you can use its embedded signal generator to generate a sweep and single
# frequency waveform on the output channels.
#
# (c) 2017 Liquid Instruments Pty. Ltd.
#
from pymoku import Moku
from pymoku.instruments import *
import time, logging

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s::%(message)s')
logging.getLogger('pymoku').setLevel(logging.INFO)

# Use Moku.get_by_serial() or Moku('192.168.XXX.XXX') if you know the IP
m = Moku.get_by_name('Moku')

i = m.discover_instrument()
if i is None or i.type != 'specan':
	print("No or wrong instrument deployed")
	i = SpectrumAnalyser()
	m.deploy_instrument(i)
else:
	print("Attached to existing Spectrum Analyser")
	m.take_ownership()

# Use dBm scaling on the y-axis
dbm=True

try:
	# Set spectrum analyser configuration
	i.set_defaults()
	i.set_dbmscale(dbm)
	i.set_span(0, 70e6)
	i.set_rbw() # Auto-mode

	# Set up the embedded signal generator
	i.gen_sinewave(1, 1.0, None, sweep=True)
	i.gen_sinewave(2, 0.5, 20e6)

	# Configure ADC inputs
	i.set_frontend(1, fiftyr=True)
	i.set_frontend(2, fiftyr=True)

	# Set up basic plot configurations
	line1, = plt.plot([])
	line2, = plt.plot([])
	plt.ion()
	plt.show()
	plt.grid(b=True)
	if(dbm):
		plt.ylim([-200, 100])
	else:
		plt.ylim([-0.5,1.0])
	plt.autoscale(axis='x',tight=True)

	# Get an initial frame of data to set any frame-specific plot parameters
	frame = i.get_data()

	# Format the x-axis as a frequency scale
	ax = plt.gca()
	ax.xaxis.set_major_formatter(FuncFormatter(frame.get_xaxis_fmt))
	ax.yaxis.set_major_formatter(FuncFormatter(frame.get_yaxis_fmt))
	ax.fmt_xdata = frame.get_xcoord_fmt
	ax.fmt_ydata = frame.get_ycoord_fmt

	# Get and update the plot with new data
	while True:
		frame = i.get_data()
		plt.pause(0.001)

		# Set the frame data for each channel plot
		line1.set_ydata(frame.ch1)
		line2.set_ydata(frame.ch2)
		# Frequency axis shouldn't change, but to be sure
		line1.set_xdata(frame.frequency)
		line2.set_xdata(frame.frequency)
		# Ensure the frequency axis is a tight fit
		ax.relim()
		ax.autoscale_view()

		# Redraw the lines
		plt.draw()
finally:
	m.close()
