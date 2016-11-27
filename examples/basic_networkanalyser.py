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
m = Moku('192.168.69.170')

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

start_frequency = 20e6
end_frequency = 50e6
sweep_points = 512
logarithmic = True
amp_ch1 = 0.5
amp_ch2 = 0

ch1 = True
ch2 = False

i.set_sweep(start_frequency, end_frequency, sweep_points, logarithmic, amp_ch1, amp_ch2)
i.set_dbscale(False)

print "Sweep frequency delta: ", i.get_sweep_freq_delta()
print "Minimum frequency: ", i.get_sweep_freq_min()

i.set_frontend(0, fiftyr=True, atten=True, ac=False)
i.set_frontend(1, fiftyr=True, atten=True, ac=False)

i.calibration = None


#################################
# END Instrument Configuration
#################################

#i.set_xmode(FULL_FRAME)

# Push all new configuration to the Moku device

i.commit()

#frame = i.get_frame()

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
		print "freq step", i.get_sweep_freq_delta()
		print "length", i.sweep_length
		
		#line1.set_xdata(range(len(frame.ch1.magnitude)))
		#line2.set_xdata(range(len(frame.ch1.phase)))
		# Ensure the frequency axis is a tight fit
		ax.relim()
		ax.autoscale_view()

		# Redraw the lines
		plt.draw()

finally:
	m.close()
