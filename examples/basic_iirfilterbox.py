from pymoku import Moku
from pymoku.instruments import *
import struct
import csv
import logging
from scipy import io
import numpy as np
import time

filt_coeff = []

with open('2ChannelChebPass.csv', 'r') as csv:
	for l in csv:
		filt_coeff.append(map(float,  [x.strip() for x in l.split(',')] ))

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s::%(message)s')
logging.getLogger('pymoku').setLevel(logging.DEBUG)

m = Moku('192.168.69.245')
i = IIRFilterBox()
m.deploy_instrument(i)

i.set_filter_io(ch = 1, input_switch = 'on', output_switch = 'on')
i.set_filter_io(ch = 2, input_switch = 'on', output_switch = 'on')
i.set_filter_settings(ch = 1, sample_rate = 'high', filter_array = filt_coeff)
i.set_filter_settings(ch = 2, sample_rate = 'low', filter_array = filt_coeff)
i.set_instrument_gains(ch = 1, input_scale = 0, output_scale = 0, input_offset = 0, output_offset = 0, matrix_scalar_ch1 = 1, matrix_scalar_ch2 = 0)
i.set_instrument_gains(ch = 2, input_scale = 0, output_scale = 0, input_offset = 0, output_offset = 0, matrix_scalar_ch1 = 0, matrix_scalar_ch2 = 1)
i.set_monitor(ch = 1)
i.commit()

m._receive_file('j', 'otherdata_temp.dat', length=96*4*2)

try:
	# Span from -1s to 1s i.e. trigger point centred
	#i.set_timebase(-1, 1)
	#i.commit()
	# Get and print a single frame's worth of data (time series
	# of voltage per channel)
	#print(i.get_frame())
	print("5")

finally:
	print("6")
	m.close()
