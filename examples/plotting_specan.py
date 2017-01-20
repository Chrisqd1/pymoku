from pymoku import Moku
from pymoku.instruments import *
import time, logging

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s::%(message)s')
logging.getLogger('pymoku').setLevel(logging.DEBUG)

# Use Moku.get_by_serial() or get_by_name() if you don't know the IP
m = Moku.get_by_name('example')

i = m.discover_instrument()
if i is None or i.type != 'specan':
	print("No or wrong instrument deployed")
	i = SpecAn()
	m.attach_instrument(i)
else:
	print("Attached to existing Spectrum Analyser")
	m.take_ownership()

# Set spectrum analyser configuration
dbm = False
i.set_dbmscale(dbm)
i.set_window(window_type)
i.set_span(100e6, 250e6)
i.set_rbw(None, mode=SA_RBW_AUTO)

# Set up the embedded signal generator
i.conf_output(1, 1.0, None, sweep=True)
i.conf_output(2, 0.5, 20e6)
i.enable_output(1, True)
i.enable_output(2, True)

# Configure ADC inputs
i.set_frontend(1, fiftyr=True)
i.set_frontend(2, fiftyr=True)

# Push all new configuration to the Moku device
i.commit()

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

try:
	# Get an initial frame to set any frame-specific plot parameters
	frame = i.get_frame()

	# Format the x-axis as a frequency scale 
	ax = plt.gca()
	ax.xaxis.set_major_formatter(FuncFormatter(frame.get_xaxis_fmt))
	ax.yaxis.set_major_formatter(FuncFormatter(frame.get_yaxis_fmt))
	ax.fmt_xdata = frame.get_xcoord_fmt
	ax.fmt_ydata = frame.get_ycoord_fmt

	# Start drawing new frames
	while True:
		frame = i.get_frame()
		plt.pause(0.001)

		# Set the frame data for each channel plot
		line1.set_ydata(frame.ch1)
		line2.set_ydata(frame.ch2)
		# Frequency axis shouldn't change, but to be sure
		line1.set_xdata(frame.ch1_fs)
		line2.set_xdata(frame.ch2_fs)
		# Ensure the frequency axis is a tight fit
		ax.relim()
		ax.autoscale_view()

		# Redraw the lines
		plt.draw()
finally:
	m.close()
