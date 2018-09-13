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
	i.set_frontend(1, fiftyr = True, atten = False, ac = False)
	i.set_local_oscillator(source='internal', frequency=40e3, phase=0, pll_auto_acq = True)
	i.set_aux_sine(amplitude = 1.0, frequency = 2e3, phase=0, sync_to_lo = False, output = 'none')
	i.set_pid_by_gain(1, g=0, kp=1)
	i.set_pid_enable(1, True)
	i.set_pid_bypass(1, False)
	i.set_pid_by_gain(2, g=0, kp=1)
	i.set_pid_enable(2, True)
	i.set_pid_bypass(2, False)
	i.set_scan(frequency=5e3, phase=0.0, output = 'none', amplitude=1.0, waveform='triangle')
	i.set_butterworth(1e6)
	i.set_output_range(1, 1.0, -1.0)
	i.set_output_range(2, 1.0, -1.0)

	# Monitor the I and Q signals from the mixer, before filtering
	i.set_monitor('A', 'out1')
	i.set_monitor('B', 'out2') #green

	# Trigger on Monitor 'B' ('Q' signal), rising edge, 0V with 0.1V hysteresis
	i.set_trigger('A', 'rising', 0, trig_on_scan_rising = False)

	 # View +- 0.1 second, i.e. trigger in the centre
	i.set_timebase(-2e-4, 2e-4)

	# Get initial data frame to set up plotting parameters. This can be done once
	# if we know that the axes aren't going to change (otherwise we'd do
	# this in the loop)
	data = i.get_realtime_data()

	# Set up the plotting parameters
	plt.ion()
	plt.show()
	plt.grid(b=True)
	plt.ylim([-2,2])
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

