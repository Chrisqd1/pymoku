from pymoku import Moku
from pymoku.instruments import IIRFilterBox

"""
Moku:DigitalFilterBox implements infinite impulse resposne (IIR) filters using 4 cascaded Direct Form 1 second-order stages
with a final output gain stage. The total transfer function can be written:

H(Z) = G * prod(k = 1,2,3,4) : sk * [b0,k + b1,k * z^-1 + b2,k * z^-2] / [1 + a1,k * z^-1 + a2,k * z^-2]

To specify a filter, you must supply an array containing the filter coefficients. The array should contain five rows and six columns. 
The first row has one column entry, corresponding to the overall gain factor G. The following four rows have six entries each, corresponding
to the s, b0, b1, b2, a1 and a2 coefficients of the four cascaded SOS filters. 

		Example array dimensions:

	 	[[G],
		[s1, b0.1, b1.1, b2.1, a1.1, a2.1],
		[s2, b0.2, b1.2, b2.2, a1.2, a2.2],
		[s3, b0.3, b1.3, b2.3, a1.3, a2.3],
		[s4, b0.4, b1.4, b2.4, a1.4, a2.4]]

Each coefficient must be in the range [-4.0, +4.0). Internally, these are represented as signed 48-bit fixed-point numbers, with 45 fractional bits.
The output scaling can be up to 8,000,000. Filter coefficients can be computed using signal processing toolboxes in e.g. MATLAB or SciPy.

Warning: some coefficients may result in overflow or underflow, which degrade filter performance. Filter responses should be checked prior to use.

An example coefficient array that was generated in MATLAB and exported according to the above array dimensions is given below. It produces an 8th order
Chebyshev type 2 filter with a normalized stopband frequency of 0.2 pi rad/sample and a stopband attenuation of 40 dB. Output gain is set to 1.0.

"""

filt_coeff = 	[[1.0],
				[1.0000000000,0.6413900006,-1.0290561741,0.6413900006,-1.6378425857,0.8915664128],
				[1.0000000000,0.5106751138,-0.7507394931,0.5106751138,-1.4000444473,0.6706551819],
				[1.0000000000,0.3173108134,-0.3111365531,0.3173108134,-1.0873085012,0.4107935750],
				[1.0000000000,0.1301131088,0.1223154629,0.1301131088,-0.7955572476,0.1780989281]]


m = Moku('192.168.69.245')
i = IIRFilterBox()
m.deploy_instrument(i)

try:

	i.set_frontend(1,fiftyr=True, atten=False, ac=False)
	i.set_frontend(2,fiftyr=True, atten=False, ac=False)

	i.set_filter_io(ch = 1, input_switch = True, output_switch = True)
	i.set_filter_io(ch = 2, input_switch = True, output_switch = True)
	i.set_filter_settings(ch = 1, sample_rate = 'high', filter_coefficients = filt_coeff)
	i.set_filter_settings(ch = 2, sample_rate = 'high', filter_coefficients = filt_coeff)
	i.set_instrument_gains(ch = 1, input_scale = 0, output_scale = 0, input_offset = 0, output_offset = 0, matrix_scalar_ch1 = 1, matrix_scalar_ch2 = 0)
	i.set_instrument_gains(ch = 2, input_scale = 0, output_scale = 0, input_offset = 0, output_offset = 0, matrix_scalar_ch1 = 0, matrix_scalar_ch2 = 1)
	i.set_monitor(ch = 1)

finally:
	m.close()
