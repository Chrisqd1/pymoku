from pymoku import Moku
from pymoku.instruments import *
from datetime import datetime

import time, logging

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s::%(message)s')
logging.getLogger('pymoku').setLevel(logging.DEBUG)

# Use Moku.get_by_serial() or get_by_name() if you don't know the IP

# m = Moku.get_by_name('Oil Rigs')
m = Moku('192.168.69.53')

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

i.set_defaults()

f_start = 1e6 # Hz
f_end = 1e8  # Hz
sweep_order = 9
sweep_length = 2**sweep_order
log_scale = True
single_sweep = False
amp_ch1 = 1.0 # Volts peak-to-peak (assuming 50 Ohm impedance)
amp_ch2 = 1.0 # Volts peak-to-peak (assuming 50 Ohm impedance)

averaging_time = 8e-3 # seconds
settling_time = 5e-3 # seconds

averaging_cycles = 100
settling_cycles = 100

i.set_dbscale(True)

i.set_sweep_parameters(f_start, f_end, sweep_length, log_scale, single_sweep, amp_ch1, amp_ch2, averaging_time, settling_time, averaging_cycles, settling_cycles) 

i.set_frontend(1, fiftyr=True, atten=False, ac=False)
i.set_frontend(2, fiftyr=True, atten=True, ac=False)

acq_filename = "../NetworkAnalyser_analysis/1_kHz_to_100_MHz_tests/BBP-21.4+/BBP-21.4+.csv"

#################################
# END Instrument Configuration
#################################

i.commit()


i.set_calibration()


# Set up basic plot configurations
line1, = plt.semilogx([])
line2, = plt.semilogx([])
plt.ion()
plt.show()

plt.grid(b=True)

try:
	# Get an initial frame to set any frame-specific plot parameters
	frame = i.get_frame()
	
	# print "frame", frame

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
		line2.set_ydata(frame.ch1.phase)

		print 'Magnitude: ', frame.ch1.magnitude
		print 'Phase: ', frame.ch1.phase


		file = open(acq_filename, "w")	

		time_string = datetime.now().strftime("%c")
		header =  "# Moku:NetworkAnalyser Acquisition\r\n"
		header += "# Time: {T} \r\n".format(T=time_string)

		header += "\n"	

		ch1_frontend = i.get_frontend(1)
		ch2_frontend = i.get_frontend(2)

		header += "# Ch1 - {} coupling, {} Ohm impedance, {} dB attenuation\r\n".format("AC" if ch1_frontend[2] else "DC", "50" if ch1_frontend[0] else "1M", "20" if ch1_frontend[1] else "0")
		header += "# Ch2 - {} coupling, {} Ohm impedance, {} dB attenuation\r\n".format("AC" if ch2_frontend[2] else "DC", "50" if ch2_frontend[0] else "1M", "20" if ch2_frontend[1] else "0")

		

		header += "# Sweep Parameters\n"
		header += "# Start Frequency: {:.4e} Hz\n".format(f_start)
		header += "# End Frequency: {:.4e} Hz\n".format(f_end)
		header += "# Sweep Length: {:}\n".format(sweep_length)
		header += "# Sweep Mode: {}\n".format("Logarithmic" if log_scale else "Linear")
		header += "# Averaging Time: {:.4e} seconds \n".format(averaging_time)
		header += "# Averaging Cycles: {:} cycles \n".format(averaging_cycles)
		header += "# Settling Time: {:.4e} seconds \n".format(settling_time)
		header += "# Settling Cycles: {:} cycles\n".format(settling_cycles)
		header += "# Sweep Amplitude (Ch1): {:} Volts\n".format(amp_ch1)
		header += "# Sweep Amplitude (Ch2): {:} Volts\n".format(amp_ch2)
		
		header += "\r\n"

		file.write(header)

		out_string = "Frequency (Hz), Magnitude (dB), Phase (Rad) \n"

		for j in range(len(frame.ch1.magnitude)):
			# out_string = ""
			out_string += "{:}, {:}, {:} \n".format(str(frame.ch1_fs[j]), str(frame.ch1.magnitude[j]), str(frame.ch1.phase[j]))
			# out_string += str(frame.ch1_fs[i])
			# out_string += "; "
			# out_string += str(frame.ch1.magnitude[i])
			# out_string += "; "
			# out_string += str(frame.ch1.phase[i])
			# out_string += "; "
			# out_string += "\n"

		file.write(out_string)
		file.close()

		


		# print 'Input frame: ', frame.ch1.input
		
		# Frequency axis shouldn't change, but to be sure
		line1.set_xdata(frame.ch1_fs)
		line2.set_xdata(frame.ch2_fs)
		
		print "Frequency: ", frame.ch1_fs
		# print "Sweep frequency delta: ", i.get_sweep_freq_delta()
		# print "Minimum frequency: ", i.get_sweep_freq_min()
		# print "Channel 1 Amplitude: ", i.sweep_amp_volts_ch1
		
		# Ensure the frequency axis is a tight fit
		ax.relim()
		ax.autoscale_view()

		# Redraw the lines
		plt.draw()



finally:
	m.close()
