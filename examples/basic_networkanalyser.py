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
m = Moku('192.168.69.50')

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

i.set_frontend(0, fiftyr=False, atten=False, ac=False)

f_start = 1e6 # Hz
f_end = 20e6  # Hz
sweep_length = 512
log_scale = False 
amp_ch1 = 1 # volts (assuming high impedance)
amp_ch2 = 1 # volts (assuming high impedance)
averaging_time = 1e-3 # seconds
settling_time = 1e-3 # seconds

i.set_dbscale(True)

i.set_defaults()

i.set_sweep_parameters(f_start, f_end, sweep_length, log_scale, amp_ch1, amp_ch2, averaging_time, settling_time) 
# i.set_sweep_parameters(f_start,1e2, 2e3, 512, False, 0.5, 1, 0.01, 0.01)

#################################
# END Instrument Configuration
#################################

#i.set_xmode(FULL_FRAME)

# Push all new configuration to the Moku device
i.commit()

#gain_scales = i.gain_correction()
#print 'GAIN: ', gain_scales

print "Sweep frequency delta: ", i.get_sweep_freq_delta()
print "Minimum frequency: ", i.get_sweep_freq_min()

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
		# print frame.ch1.phase
		# Frequency axis shouldn't change, but to be sure
		line1.set_xdata(frame.ch1_fs)
		line2.set_xdata(frame.ch2_fs)
		print "ch1_axis", frame.ch1_fs
		print "start freq", i.sweep_freq_min
		# if log_scale:
		# 	print "freq step", i.sweep_freq_delta/2.0**30
		# else :
		# 	print "freq step", i.sweep_freq_delta/2.0**48 * 1.0e9
		#line1.set_xdata(range(len(frame.ch1.magnitude)))
		#line2.set_xdata(range(len(frame.ch1.phase)))
		# Ensure the frequency axis is a tight fit
		ax.relim()
		ax.autoscale_view()

		# Redraw the lines
		plt.draw()

finally:
	m.close()
