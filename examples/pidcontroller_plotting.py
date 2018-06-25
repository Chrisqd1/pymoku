# pymoku example: PID Controller Plotting Example
#
# (c) 2018 Liquid Instruments
#
from pymoku import Moku
from pymoku.instruments import PIDController

import math
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

import logging
logging.basicConfig(level=logging.DEBUG)

def from_dB(dB):
	# Helper function that converts from dB to linear scale
	return 10**(dB/20.0)

# Connect to your Moku by its device name
# Alternatively, use Moku.get_by_serial('#####') or Moku('192.168.###.###')
m = Moku.get_by_name('TurtleOne')
i = PIDController()
m.deploy_instrument(i)

try:

	# Configure the PID Controller using frequency response characteristics
	# 	P = -10dB
	#	I Crossover = 100Hz
	# 	D Crossover = 10kHz
	# 	I Saturation = 10dB
	# 	D Saturation = 10dB
	# 	Double-I = OFF
	# Note that gains must be converted from dB first
	i.set_by_frequency(1, kp=from_dB(-10), i_xover=1e2, ii_xover=None, d_xover =1e4, si=from_dB(10), sd=from_dB(10))

	# Set which signals to view on each monitor channel, and the timebase on
	# which to view them.
	i.set_timebase(-1e6, 1e-6)
	i.set_monitor('a', 'in1')
	i.set_monitor('b', 'out1')

	i.set_trigger('a', 'rising', 0, mode='auto')

	# Get initial data frame to set up plotting parameters. This can be done once
	# if we know that the axes aren't going to change (otherwise we'd do
	# this in the loop)
	data = i.get_realtime_data()

	# Set up the plotting parameters
	plt.ion()
	plt.show()
	plt.grid(b=True)
	plt.ylim([-1,1])
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
		plt.pause(0.001)

finally:
	m.close()
