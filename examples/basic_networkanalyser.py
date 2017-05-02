from pymoku import Moku
from pymoku.instruments import *
from datetime import datetime

import time, logging

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import struct

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s::%(message)s')
logging.getLogger('pymoku').setLevel(logging.DEBUG)

m = Moku.get_by_serial('65540')

i = NetAn()
m.attach_instrument(i)

i.set_defaults()

f_start = 1e6 # Hz
f_end = 125e6  # Hz
sweep_order = 9
sweep_length = 2**sweep_order
log_scale = False
single_sweep = False
amp_ch1 = 1.0 # Volts peak-to-peak (assuming 50 Ohm impedance)
amp_ch2 = 1.0 # Volts peak-to-peak (assuming 50 Ohm impedance)
averaging_time = 0 # seconds
settling_time = 0 # seconds
averaging_cycles = 2**16-20
settling_cycles = 10000

i.set_dbscale(True)
i.set_sweep_parameters(f_start, f_end, sweep_length, log_scale, single_sweep, amp_ch1, amp_ch2, averaging_time, settling_time, averaging_cycles, settling_cycles)
i.set_frontend(1, fiftyr=True, atten=False, ac=False)
i.set_frontend(2, fiftyr=True, atten=True, ac=False)

i.commit()

i.sweep_amplitude_ch1 = 0.5
i.single_sweep = True
i.x_mode = 2
i.commit()

# i.set_calibration()

# plt.subplots_adjust(hspace=0.4)

## Create empty line vectors for ch1 and ch2 magnitude plots
plt.subplot(211)
line1, = plt.plot([])
line2, = plt.plot([])

plt.ion()
plt.show()

plt.grid(b=True)

## Create empty line vectors for ch1 and ch2 phase plots
plt.subplot(212)
line3, = plt.plot([])
line4, = plt.plot([])

try:
	# Get an initial frame to set any frame-specific plot parameters
	frame = i.get_frame()
	smpls = int(len(frame.raw1) / 4)
	dat = struct.unpack('<' + 'i' * smpls, frame.raw1)
	print dat

	# Format the x-axis as a frequency scale
	plt.subplot(211)
	ax_1 = plt.gca()
	ax_1.set_xlim(f_start, f_end)
	ax_1.set_ylim(-100, 50)

	plt.subplot(212)
	ax_2 = plt.gca()

	# Start drawing new frames
	while True:
		frame = i.get_frame()
		plt.pause(0.001)

		# Set the frame data for each channel plot
		plt.subplot(211)
		line1.set_ydata(frame.ch1.magnitude)
		line2.set_ydata(frame.ch2.magnitude)

		line1.set_xdata(frame.ch1_fs)
		line2.set_xdata(frame.ch2_fs)


		# Phase
		plt.subplot(212)
		line3.set_ydata(frame.ch1.phase)
		line4.set_ydata(frame.ch2.phase)

		line3.set_xdata(frame.ch1_fs)
		line4.set_xdata(frame.ch2_fs)

		# Ensure the frequency axis is a tight fit
		# ax_1.relim()
		# ax_1.autoscale_view()

		# ax_2.relim()
		# ax_2.autoscale_view()

		# Redraw the lines
		plt.draw()

finally:
	m.close()
