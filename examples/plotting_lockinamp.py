#
# pymoku example: Plotting Oscilloscope
#
# This example demonstrates how you can configure the Oscilloscope instrument,
# and view triggered time-voltage data frames in real-time. 
#
# (c) 2017 Liquid Instruments Pty. Ltd.
#
from pymoku import Moku
from pymoku.instruments import *
import time, logging

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

#logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s::%(message)s')
#logging.getLogger('pymoku').setLevel(logging.DEBUG)

# Connect to your Moku by its device name
# Alternatively, use Moku.get_by_serial('#####') or Moku('192.168.###.###')
m = Moku('192.168.69.120')

ipad_reg_list =  m._read_regs(range(127))
#for n,x in ipad_reg_list:
#	print("%3d - %x" % (n,x))

i = LockInAmp()

m.deploy_instrument(i)

try:

	# Trigger on input Channel 1, rising edge, 0V with 0.1V hysteresis
	# Remap the trigger function in the oscilloscope to be {'in1','in2','1','2'}
	i.set_trigger('B', 'rising', 0)

	 # View +- 0.1 second, i.e. trigger in the centre
	i.set_timebase(-1e-6, 1e-6)

	# Monitor the input signal on CH1 and the PID output on CH2

	# These must change the scaling factor of the Oscilloscope, refer to IPad code
	i.set_monitor('A', 'i')
	i.set_monitor('B', 'aux')

	i.set_demodulation('internal')

	i.set_lo_output(1.0,1e6,0)

	i.set_outputs(main='i',aux='demod')
	i.set_gain('aux',1.0)
	i.set_gain('main',1.0)
	#i.set_pid_by_gain('main',1.0)

	pymoku_reg_list =  m._read_regs(range(127))
	print("		PYMOKU 					|  IPAD")
	for n,x in pymoku_reg_list:
		if pymoku_reg_list[n] != ipad_reg_list[n]:
			print("{:3d} - {:032b} | {:032b}".format(n,x,ipad_reg_list[n][1]))
	#i.set_lo_output(0.5, 1e3, 0)

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
