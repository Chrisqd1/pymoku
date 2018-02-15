# pymoku example: Basic IIR Filter Box
#
# This example demonstrates how you can configure the FIR Filter instrument.
#
# (c) 2018 Liquid Instruments Pty. Ltd.
#
from pymoku import Moku
from pymoku.instruments import FIRFilter
from scipy.signal import firwin
from scipy import fft
import math
import matplotlib.pyplot as plt

# This script provides an example showing how to generate an FIR filter kernel with specified parameters using scipy and how to access settings of the FIR instrument.
# FIR kernels should have a normalised power of <= 1.0. Scipy's firwin function conforms to this requirement. 

## Specify nyquist and cutoff (-3dB) frequencies
nyq_rate = 125e6 / 2**10 / 2.0
cutoff_hz = 1e3

## Calculate FIR kernel using 10,000 taps and a chebyshev window with -60dB stop-band attenuation
taps = firwin(1000, cutoff_hz/nyq_rate, window='hamming')

m = Moku('192.168.69.245', load_instruments=True, force = True)
i = FIRFilter()
m.deploy_instrument(i)

try:
	## Configure FIR instrument
	i._set_frontend(1, fiftyr=True, atten=False, ac=False)
	i._set_frontend(2, fiftyr=True, atten=False, ac=False)

	# Both filter channels are configured with the same FIR kernel. A decimation factor of 10 is used to achieve the desired nyquist rate and FIR kernel length of 10,000.
	i.set_filter(1, decimation_factor = 10, filter_coefficients = taps, enable = True)
	i.set_filter(2, decimation_factor = 10, filter_coefficients = taps, enable = True)

	# Channel 1 has default instrument settings and acts soley on ADC1. 
	# Channel 2 has an input scaling of 0.5, output scaling of 2.0, input offset of -0.1 V, ADC1 and ADC2 scale coefficients of 0.5 and an output scaling of 2.0.
	i.set_offset_gain(ch = 1, matrix_scalar_ch1 = 1.0, matrix_scalar_ch2 = 0.0)
	i.set_offset_gain(ch = 2, input_scale = 0.5, output_scale = 2.0, input_offset = -0.1, matrix_scalar_ch1 = 0.5, matrix_scalar_ch2 = 0.5)

	## Quantise FIR kernel for analysis, calculate filter transfer function and plot the results:
	taps_quantized = [round(taps[x]*2.0**24-1) / (2**24 - 1) for x in range(0,len(taps))]
	fft_taps = fft(taps_quantized)
	fft_mag = [abs(fft_taps[x]) for x in range(0,len(fft_taps[0:499]))]
	fft_db = [20*math.log10(fft_mag[x]) for x in range(0,len(fft_mag))]

	plt.figure(1)
	plt.plot(taps)
	plt.title('FIR Filter Kernel')
	plt.ylabel('Normalised Value')
	plt.grid(True,which = 'major')
	plt.xlabel('Kernel Tap Number')
	plt.figure(2)
	plt.semilogx(fft_db)
	plt.title('FIR Filter Transfer Function')
	plt.ylabel('Magnitude (dB)')
	plt.xlabel('Frequency (Hz)')
	plt.grid(True,which = 'major')
	plt.show()

finally:
	m.close()
