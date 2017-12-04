from pymoku import Moku
from pymoku.instruments import FIRFilter
import numpy as np
from scipy import signal

import matplotlib
import matplotlib.pyplot as plt
from math import floor

FS = 125e6 / 500
length = 500000
amp = 2**12
f0 = 1e3
dec = 128

#filt1 = signal.firls(101, [0.0, 50.0e3, 50.0e3, 100.0e3, 100.0e3, FS/2.0], [0.1, 0.1, 1.0, 1.0, 0.1, 0.1], fs=FS)
#filt1 = [1.0, 0.0, 0.0, 0.0] + [0.0,0.0,0.0,0.0]*4

filt_coeff = []
with open('FIRKernal.csv', 'r') as csv:
	for l in csv:
		filt_coeff.append(map(float,  [x.strip() for x in l.split(',')] ))

#filt1 = [1.0] + [0.0]*(dec*44-1)
filt1 = filt_coeff[0]
print(len(filt1))

#filt2 = signal.firls(101, [0.0, 50.0e3, 50.0e3, 100.0e3, 100.0e3, FS/2.0], [0.1, 0.1, 1.0, 1.0, 0.1, 0.1], fs=FS)
#filt2 = [1.0, 0.0, 0.0, 0.0]
# filt2 = [-1.0] + [0.0]*20000 + [-1.0]
filt2 = [1e-5] * 404
# filt = [0.5**9]*8
# filt2 = filt2 * 2.0**2
# plt.plot(filt1)
# plt.plot(filt2)
# plt.show()
# print filt
# exit(0)

# Connect to your Moku by its device name
# Alternatively, use Moku.get_by_serial('#####') or Moku('192.168.###.###')
m = Moku('192.168.69.66', load_instruments=True, force = True)

# Prepare the ArbWaveformGenerator instrument
i = FIRFilter()
m.deploy_instrument(i)



# filt = [int(round(2.0**17 * x)) for x in filt]
# print filt
# plt.plot(filt)

# sig = np.random.random_integers(-amp, amp-1, length)
# sig_filt = signal.convolve(sig, filt, mode='same', method='direct')

# plt.plot(sig, 'b')
# plt.plot(sig_filt, 'r')

# psd = np.abs(np.fft.fft([x / 1.0 for x in sig_filt]))**2
# plt.loglog(psd[0:len(psd)/2], 'r')

# plt.loglog(psd[0], psd[1])
# print sig_filt[:100]
# plt.show()


try:

	i.set_defaults()
	i._set_frontend(1, fiftyr=False, atten=False, ac=False)
	i.set_trigger('in1', 'rising', 0.00, hysteresis=True)
	i.set_timebase(-25e-6,400e-6)

	i.set_source(1, 'in')
	i.set_source(2, 'out')

	i.set_offset_gain(ch = 1, output_scale = 0.5)
	i.set_samplerate(ch = 1, decimation_factor=dec)

	i.decimation2 = dec
	i.decimation1 = dec
	#i.upsampling1 = int(floor(2.0**17 / ((i.decimation1+1))))
	i.write_coeffs(1, filt1)
	#i.upsampling2 = int(floor(2.0**17 / ((i.decimation2+1))))
	i.write_coeffs(2, filt2)

	i.link = True
	i.commit()

	i._set_mmap_access(True)
	error = i._moku._receive_file('j', '.lutdata_moku.dat', 511 * 40 * 4 * 2)
	i._set_mmap_access(False)

	data = i.get_realtime_data()
	# Set up the plotting parameters
	plt.ion()
	plt.show()
	plt.grid(b=True)
	plt.ylim([-0.1,0.1])
	plt.xlim([data.time[0], data.time[-1]])

	line1, = plt.plot([])
	line2, = plt.plot([])

	# This loops continuously updates the plot with new data
	while True:
		# Get new data
		data = i.get_realtime_data()

		# Update the plot
		# psd = signal.welch(data.ch1, fs=FS)
		# line1.set_ydata(psd[1])
		# line1.set_xdata(psd[0])

		line1.set_ydata(data.ch1)
		line2.set_ydata(data.ch2)
		line1.set_xdata(data.time)
		line2.set_xdata(data.time)
		plt.pause(0.001)


finally:
	m.close()
