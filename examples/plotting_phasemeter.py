#
# pymoku example: Phasemeter networking streaming
#
# This example provides a network stream of Phasemeter
# data samples from Channel 1 and Channel 2. These samples
# are output in the form [fs, f, count, phase, I, Q] for each channel.
#
# (c) 2016 Liquid Instruments Pty. Ltd.
#

# The phasemeter is a little more complex than some instruments as its native output
# is a stream of measurements, accessed through the datalogger; rather than a sequence
# of frames containing a range of data.  One can record this stream to a CSV or binary
# file, but this example streams the samples over the network so they can be accessed,
# processed and plotted in real time.
import pymoku
from pymoku import Moku, NoDataException, FrameTimeout, StreamException
from pymoku.instruments import *
import time, logging, math, numpy
import matplotlib.pyplot as plt

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s::%(message)s')
logging.getLogger('pymoku').setLevel(logging.INFO)

# Disable auto-commit feature so we can atomically change settings
pymoku.autocommit = False

# Use Moku.get_by_serial() or get_by_name() if you don't know the IP
m = Moku.get_by_name('example')
i = m.discover_instrument()

if i is None or i.type != 'phasemeter':
	print("No or wrong instrument deployed")
	i = Phasemeter()
	m.deploy_instrument(i)
else:
	print("Attached to existing Phasemeter")
	m.take_ownership()

try:
	#################################
	# BEGIN Instrument Configuration
	# ------------------------------
	# Set these parameters
	#################################

	# Which input channels are ON?
	ch1 = True
	ch2 = True

	#Initial channel scan frequencies
	ch1_freq = 10e6
	ch2_freq = 10e6

	#Ouput sinewaves
	ch1_out_enable = True
	ch1_out_freq = 10e6
	ch1_out_amp = 1

	ch2_out_enable = True
	ch2_out_freq = 10e6
	ch2_out_amp = 1

	#Log duration (sec)
	duration = 100

	# Measurements to display on the plot
	plot_points = 500
	#################################
	# END Instrument Configuration
	#################################

	# Set the initial phase-lock loop frequency for both channels
	i.set_initfreq(1, ch1_freq)
	i.set_initfreq(2, ch2_freq)

	# Set samplerate to slow mode ~30Hz
	i.set_samplerate('slow')

	# Set up signal generator for enabled channels
	if(ch1_out_enable):
		i.gen_sinewave(1, ch1_out_amp, ch1_out_freq)
	if(ch2_out_enable):
		i.gen_sinewave(2, ch2_out_amp, ch2_out_freq)

	# Atomically apply all instrument settings above
	i.commit()

	# Allow time for commit to flow down
	time.sleep(0.8)

	# Stop any existing streaming session and start a new one
	# Logging session:
	# 		Start time - 0 sec
	#		Duration - 20 sec
	#		Channel 1 - ON, Channel 2 - ON
	i.stop_stream_data()
	i.start_stream_data(start=0, duration=20, ch1=True, ch2=True)

	# Set up basic plot configurations
	if ch1:
		ydata1 = [None] * plot_points
		line1, = plt.plot(ydata1)
	if ch2:
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
		if ch1:
			for s in data[0]:
				ydata1 = ydata1 + [math.sqrt(s[4]**2 + s[5]**2)]
		if ch2:
			for s in data[1]:
				ydata2 = ydata2 + [math.sqrt(s[4]**2 + s[5]**2)]

		ydata1 = ydata1[-plot_points:]
		ydata2 = ydata2[-plot_points:]

		# Must set lines for each draw loop
		if ch1:
			line1.set_ydata(ydata1)
			line1.set_xdata(xdata)
		if ch2:
			line2.set_ydata(ydata2)
			line2.set_xdata(xdata)

		ax.relim()
		ax.autoscale_view()
		plt.pause(0.001)
		plt.draw()

except StreamException as e:
	print("Error occured: %s" % e.message)
except FrameTimeout:
	print("Logging session timed out")
finally:
	i.stop_stream_data()
	m.close()