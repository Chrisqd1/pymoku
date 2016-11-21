from pymoku import Moku
from pymoku.instruments import *
import time, logging

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s::%(message)s')
logging.getLogger('pymoku').setLevel(logging.DEBUG)

# Use Moku.get_by_serial() or get_by_name() if you don't know the IP
# m = Moku.get_by_name('Oil Rigs')
m = Moku('192.168.69.63')
# i = m.discover_instrument()
# if i is None or i.type != 'netan':
# 	print("No or wrong instrument deployed")
i = NetAn()
m.attach_instrument(i)
# else:
	# print("Attached to existing Spectrum Analyser")

#################################
# BEGIN Instrument Configuration
# ------------------------------
# Set these parameters
	# i.set_defaults()


# ch1 = True
# ch2 = False
# 
# i.set_frontend(0, fiftyr=True, atten=True, ac=False)
# i.set_frontend(1, fiftyr=True, atten=True, ac=False)
i.set_dbscale(False)
# i.calibration = None
i.set_defaults()
# i.sweep_freq_min = 1
# i.sweep_freq_delta = 1
# i.log_en = False
# i.hold_off_time = 1
# i.sweep_length = 1000
# i.sweep_amp_bitshift = 0
# i.sweep_amp_mult = 1

#################################
# END Instrument Configuration
#################################

#i.set_xmode(FULL_FRAME)

# Push all new configuration to the Moku device


# i.sweep_freq_min = 100
# i.sweep_freq_delta = 100
# i.hold_off_time = 125

i.set_dbscale(True)

i.set_sweep_parameters(1e3, 100e3, 512, False)

i.commit()

#frame = i.get_frame()
# i.sweep_freq_min = 10
# i.sweep_freq_delta = 10

# i.commit()
#print frame[0]
# Set up basic plot configurations
line1, = plt.plot([])
line2, = plt.plot([])
plt.ion()
plt.show()
plt.grid(b=True)
# if(dbm):
# plt.ylim([-200, 100])
# else:
#plt.ylim([-100,100])
# plt.autoscale(axis='x',tight=True)

try:
	# Get an initial frame to set any frame-specific plot parameters
	print "hello"
	frame = i.get_frame()
	print "frame", frame
	print "channel 1 mag", frame.ch1.magnitude
	print "channel 1 phase", frame.ch1.phase

	# Format the x-axis as a frequency scale 
	ax = plt.gca()
	# ax.xaxis.set_major_formatter(FuncFormatter(frame.get_xaxis_fmt))
	# ax.yaxis.set_major_formatter(FuncFormatter(frame.get_yaxis_fmt))
	# ax.fmt_xdata = frame.get_xcoord_fmt
	# ax.fmt_ydata = frame.get_ycoord_fmt


	# Start drawing new frames
	while True:
		frame = i.get_frame()
		plt.pause(0.001)

		# Set the frame data for each channel plot
		line1.set_ydata(frame.ch1.magnitude)
		print frame.ch1.magnitude
		line2.set_ydata(frame.ch1.phase)
		print frame.ch1.phase
		# Frequency axis shouldn't change, but to be sure
		line1.set_xdata(frame.ch1_fs)
		line2.set_xdata(frame.ch2_fs)
		print "ch1_axis", frame.ch1_fs
		print "start freq", i.sweep_freq_min
		print "freq step", i.sweep_freq_delta
		#line1.set_xdata(range(len(frame.ch1.magnitude)))
		#line2.set_xdata(range(len(frame.ch1.phase)))
		# Ensure the frequency axis is a tight fit
		ax.relim()
		ax.autoscale_view()

		# Redraw the lines
		plt.draw()

finally:
	m.close()
