# pymoku example: Basic IIR Filter Box
#
# This example demonstrates how you can configure the FIR Filter instrument.
#
# (c) 2018 Liquid Instruments Pty. Ltd.
#
from pymoku import Moku
from pymoku.instruments import FIRFilter
import time

# This script provides a basic example showing how to load coefficients from an array into the FIRFilterBox.

# The following two example arrays are simple rectangular FIR kernels with 50 and 400 taps respectively. A rectangular kernel produces a sinc shaped transfer function with width
# inversely  proportional to the length of the kernel. FIR kernels must have a normalised power of <= 1.0, so the value of each tap is the inverse of the total number of taps. 

filt_coeff1 = [1.0 / 50] * 50
filt_coeff2 = [1.0 / 400] * 400

m = Moku('192.168.69.245', load_instruments=True, force = True)
i = FIRFilter()
m.deploy_instrument(i)

try:
	i._set_frontend(1, fiftyr=True, atten=False, ac=False)
	i._set_frontend(2, fiftyr=True, atten=False, ac=False)

	# To implement 50 FIR taps we need a sample rate of 125 MHz / 2. To implement 400 FIR taps we need a sample rate of 125 MHz / 16.
	# Sample rate is configured according to: Fs = 125 MHz / 2^decimation_factor.
	i.set_filter(1, decimation_factor = 1, filter_coefficients = filt_coeff1, enable = True)
	i.set_filter(2, decimation_factor = 4, filter_coefficients = filt_coeff2, enable = True)

	i._set_mmap_access(True)
	error = i._moku._receive_file('j', '.lutdata_moku.dat', 511 * 29 * 4 * 2)	
	i._set_mmap_access(False)

	# Both channels have unity I/O scalars and no offsets. Channel 1 acts on ADC1 and channel 2 acts on ADC2.
	i.set_offset_gain(ch = 1, input_scale = 1.0, output_scale = 1.0, matrix_scalar_ch1 = 1.0, matrix_scalar_ch2 = 0.0)
	i.set_offset_gain(ch = 2, input_scale = 1.0, output_scale = 1.0, matrix_scalar_ch1 = 0.0, matrix_scalar_ch2 = 1.0)
finally:
	m.close()
