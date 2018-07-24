#
# pymoku example: Basic Lock-in Amplifier
#
# This example demonstrates how you can configure the lock-in amplifier
# instrument
#
# (c) 2017 Liquid Instruments Pty. Ltd.
#
from pymoku import Moku
from pymoku.instruments import LaserLockBox

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# Use Moku.get_by_serial() or get_by_name() if you don't know the IP
m = Moku.get_by_name('PeregrinTook', force = True)
i = m.deploy_instrument(LaserLockBox)

try:
    # i.set_local_oscillator(1e6, 0)
	i.set_sample_rate('high')
	i.set_local_oscillator(1, 0)
	i.set_pid_by_gain(1, 1, 1)
	i.set_pid_enable(1, True)
	i.set_pid_bypass(1, False)

	# Monitor the I and Q signals from the mixer, before filtering
	i.set_monitor('A', 'in1')
	i.set_monitor('B', 'in2')

	# Trigger on Monitor 'B' ('Q' signal), rising edge, 0V with 0.1V hysteresis
	i.set_trigger('B', 'rising', 0)

	 # View +- 0.1 second, i.e. trigger in the centre
	i.set_timebase(-1e-6, 1e-6)

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
	# Close the connection to the Moku device
	# This ensures network resources and released correctly
	m.close()

