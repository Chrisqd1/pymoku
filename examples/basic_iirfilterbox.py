from pymoku import Moku
from pymoku.instruments import IIRFilterBox

"""
This script provides a basic example showing how to load coefficients from an array into the IIRFilterBox. 

The following example array produces an 8th order Direct-form 1 Chebyshev type 2 IIR filter with a normalized stopband frequency of 0.2 pi rad/sample and a stopband attenuation
of 40 dB. Output gain is set to 1.0. See the IIRFilterBox documentation for array dimension specifics. 

"""

filt_coeff = 	[[1.0],
				[1.0000000000,0.6413900006,-1.0290561741,0.6413900006,-1.6378425857,0.8915664128],
				[1.0000000000,0.5106751138,-0.7507394931,0.5106751138,-1.4000444473,0.6706551819],
				[1.0000000000,0.3173108134,-0.3111365531,0.3173108134,-1.0873085012,0.4107935750],
				[1.0000000000,0.1301131088,0.1223154629,0.1301131088,-0.7955572476,0.1780989281]]


m = Moku.get_by_name('zappyreborn')
i = IIRFilterBox()
m.deploy_instrument(i)

try:

	i.set_frontend(1,fiftyr=True, atten=False, ac=False)
	i.set_frontend(2,fiftyr=True, atten=False, ac=False)

	i.set_filter_settings(ch = 1, sample_rate = 'high', filter_coefficients = filt_coeff, output_off = False)
	i.set_filter_settings(ch = 2, sample_rate = 'low', filter_coefficients = filt_coeff, output_off = False)
	i.set_instrument_gains(ch = 1, input_scale = 1, output_scale = 1, input_offset = 0, output_offset = 0, matrix_scalar_ch1 = 1, matrix_scalar_ch2 = 0)
	i.set_instrument_gains(ch = 2, input_scale = 1, output_scale = 1, input_offset = 0, output_offset = 0, matrix_scalar_ch1 = 0, matrix_scalar_ch2 = 1)
	i.set_monitor(ch = 1)

finally:
	m.close()
