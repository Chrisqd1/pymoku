#
# pymoku example: Plotting Phasemeter
#
# This example demonstrates how you can configure the Phasemeter instrument
# and stream dual-channel samples of the form [fs, f, count, phase, I, Q]. 
# The signal amplitude is calculated using these samples, and plotted for 
# real-time viewing.
#
# (c) 2017 Liquid Instruments Pty. Ltd.
#
import pymoku
from pymoku import Moku, StreamException
from pymoku.instruments import *
import math, numpy
import matplotlib.pyplot as plt

# Disable auto-commit feature so we can atomically change settings
pymoku.autocommit = False

# Use Moku.get_by_serial() or get_by_name() if you don't know the IP
m = Moku('192.168.69.212')#.get_by_name('Moku')
i = m.discover_instrument()

if i is None or i.type != 'phasemeter':
	print("No or wrong instrument deployed")
	i = Phasemeter()
	m.deploy_instrument(i)
else:
	print("Attached to existing Phasemeter")
	m.take_ownership()

try:
	# Set the initial phase-lock loop frequency for both channels to 10MHz
	i.set_initfreq(1, 10e6)
	i.set_initfreq(2, 10e6)

	# Set samplerate to slow mode ~30Hz
	i.set_samplerate('slow')

	# Set up signal generator output, 10MHz, 1Vpp on both channels
	i.gen_sinewave(1, 1, 10e6)
	i.gen_sinewave(2, 1, 10e6)

	# Atomically apply all instrument settings above
	i.commit()

	# Stop any existing streaming session and start a new one
	# Logging session:
	# 		Start time - 0 sec
	#		Duration - 20 sec
	#		Channel 1 - ON, Channel 2 - ON
	i.stop_stream_data()
	i.start_stream_data(start=0, duration=20, ch1=True, ch2=True)

	plot_points = 500
	# Set up basic plot configurations
	ydata1 = [None] * plot_points
	line1, = plt.plot(ydata1)

	ydata2 = [None] * plot_points
	line2, = plt.plot(ydata2)

	xtent = -1 * (i.get_timestep() * (plot_points - 1))
	xdata = numpy.linspace(xtent, 0, plot_points)

	plt.ion()
	plt.show()
	plt.grid(b=True)
	ax = plt.gca()
	ax.get_yaxis().get_major_formatter().set_useOffset(False)
	plt.xlim([xtent, 0])
	plt.ylabel('Amplitude (V)')
	plt.xlabel('Time (s)')

	while True:
		# Get samples
		data = i.get_stream_data()
		if not any(data):
			break

		# Process the retrieved samples
		# Process individual sample 's' here. Output format [fs, f, count, phase, I, Q]
		# fs = setpoint frequency
		# f = measured frequency
		# Convert I,Q to amplitude and append to line graph
		for s in data[0]:
			ydata1 = ydata1 + [math.sqrt(s[4]**2 + s[5]**2)]

		for s in data[1]:
			ydata2 = ydata2 + [math.sqrt(s[4]**2 + s[5]**2)]

		ydata1 = ydata1[-plot_points:]
		ydata2 = ydata2[-plot_points:]

		# Must set lines for each draw loop
		line1.set_ydata(ydata1)
		line1.set_xdata(xdata)

		line2.set_ydata(ydata2)
		line2.set_xdata(xdata)

		ax.relim()
		ax.autoscale_view()
		plt.pause(0.001)
		plt.draw()

except StreamException as e:
	print("Error occured: %s" % e.message)
finally:
	i.stop_stream_data()
	m.close()
