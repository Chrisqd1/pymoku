from pymoku import Moku
from pymoku.instruments import *

import logging

import matplotlib
import matplotlib.pyplot as plt

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s::%(message)s')
logging.getLogger('pymoku').setLevel(logging.DEBUG)

m = Moku('192.168.69.234')#.get_by_name('Moku')

i = BodeAnalyser()
m.deploy_instrument(i)

f_start = 1e5 # Hz
f_end = 2e6  # Hz
sweep_length = 512
log_scale = True
single_sweep = False
amp_ch1 = 1.0 # Volts peak-to-peak (assuming 50 Ohm impedance)
amp_ch2 = 1.0 # Volts peak-to-peak (assuming 50 Ohm impedance)
averaging_time = 1e-3 # seconds
settling_time = 1e-3# seconds
averaging_cycles = 1 #2**16-20
settling_cycles = 1 #10000

i.set_output_amplitude(1, amp_ch1)
i.set_output_amplitude(2, amp_ch2)
i.start_sweep(f_start, f_end, sweep_length, log_scale, single_sweep, averaging_time, settling_time, averaging_cycles, settling_cycles)

plt.subplot(211)
line1, = plt.semilogx([])
line2, = plt.semilogx([])

plt.ion()
plt.show()

plt.grid(b=True)

## Create empty line vectors for ch1 and ch2 phase plots
plt.subplot(212)
line3, = plt.semilogx([])
line4, = plt.semilogx([])

try:
	# Format the x-axis as a frequency scale
	plt.subplot(211)
	ax_1 = plt.gca()
	ax_1.set_xlim(f_start, f_end)


	plt.subplot(212)
	ax_2 = plt.gca()
	ax_2.set_xlim(f_start, f_end)

	# Start drawing new frames
	while True:
		frame = i.get_data()
		print(len(frame.ch2.phase), len(frame.fs))
		#exit(0)
		plt.pause(0.001)

		# Set the frame data for each channel plot
		plt.subplot(211)
		line1.set_ydata(frame.ch1.magnitude_dB)
		line2.set_ydata(frame.ch2.magnitude_dB)

		line1.set_xdata(frame.fs)
		line2.set_xdata(frame.fs)

		# Phase
		plt.subplot(212)
		line3.set_ydata(frame.ch1.phase)
		line4.set_ydata(frame.ch2.phase)

		line3.set_xdata(frame.fs)
		line4.set_xdata(frame.fs)

		# Ensure the frequency axis is a tight fit
		ax_1.relim()
		ax_1.autoscale_view()

		ax_2.relim()
		ax_2.autoscale_view()

		# Redraw the lines
		plt.draw()

finally:
	m.close()
