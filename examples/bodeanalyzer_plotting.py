#
# pymoku example: Plotting Bode Analyzer
#
# This example demonstrates how you can generate output sweeps using the
# Bode Analyzer instrument, and view transfer function data in real-time.
#
# (c) 2017 Liquid Instruments Pty. Ltd.
#
from pymoku import *
from pymoku.instruments import BodeAnalyzer
import logging

import matplotlib
import matplotlib.pyplot as plt

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s::%(message)s')
logging.getLogger('pymoku').setLevel(logging.DEBUG)

# Connect to your Moku by its device name
# Alternatively, use Moku.get_by_serial('#####') or Moku('192.168.###.###')
m = Moku.get_by_name('Moku')

# See whether there's already a Bode Analyzer running. If there is, take
# control of it; if not, deploy a new Bode Analyzer instrument
i = m.deploy_or_connect(BodeAnalyzer)

# Define output sweep parameters here for readability
f_start = 100 # Hz
f_end = 100e6 # Hz
sweep_length = 512
log_scale = True
single_sweep = False
amp_ch1 = 0.5 # Vpp
amp_ch2 = 0.5 # Vpp
averaging_time = 1e-6 # sec
settling_time = 1e-6 # sec
averaging_cycles = 1
settling_cycles = 1

try:
	# Set the output sweep amplitudes
	i.set_output(1, amp_ch1)
	i.set_output(2, amp_ch2)

	# Set the sweep configuration
	i.set_sweep(f_start, f_end, sweep_length, log_scale, averaging_time, settling_time, averaging_cycles, settling_cycles)

	# Start the output sweep in loop mode
	i.start_sweep(single=single_sweep)

	# Set up the amplitude plot
	plt.subplot(211)
	if log_scale:
		# Plot log x-axis if frequency sweep scale is logarithmic
		line1, = plt.semilogx([])
		line2, = plt.semilogx([])
	else:
		line1, = plt.plot([])
		line2, = plt.plot([])
	ax_1 = plt.gca()
	ax_1.set_xlabel('Frequency (Hz)')
	ax_1.set_ylabel('Magnitude (dB)')

	# Set up the phase plot
	plt.subplot(212)
	if log_scale:
		line3, = plt.semilogx([])
		line4, = plt.semilogx([])
	else:
		line3, = plt.plot([])
		line4, = plt.plot([])
	ax_2 = plt.gca()
	ax_2.set_xlabel('Frequency (Hz)')
	ax_2.set_ylabel('Phase (Cycles)')

	plt.ion()
	plt.show()
	plt.grid(b=True)

	# Retrieves and plot new data
	while True:
		frame = i.get_data(timeout=5)

		# Set the frame data for each channel plot
		plt.subplot(211)
		line1.set_ydata(frame.ch1.magnitude_dB)
		line2.set_ydata(frame.ch2.magnitude_dB)
		line1.set_xdata(frame.frequency)
		line2.set_xdata(frame.frequency)

		# Phase
		plt.subplot(212)
		line3.set_ydata(frame.ch1.phase)
		line4.set_ydata(frame.ch2.phase)
		line3.set_xdata(frame.frequency)
		line4.set_xdata(frame.frequency)

		# Ensure the frequency axis is a tight fit
		ax_1.set_xlim(min(frame.frequency), max(frame.frequency))
		ax_2.set_xlim(min(frame.frequency), max(frame.frequency))
		ax_1.relim()
		ax_1.autoscale_view()
		ax_2.relim()
		ax_2.autoscale_view()

		# Redraw the lines
		plt.draw()

		plt.pause(0.001)
finally:
	m.close()
