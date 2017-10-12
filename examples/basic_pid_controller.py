from pymoku import Moku  
from pymoku.instruments import PIDController
import time, logging

from natu.units import dB

import matplotlib
import matplotlib.pyplot as plt

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s::%(message)s')
logging.getLogger('pymoku').setLevel(logging.DEBUG)

# Use Moku.get_by_serial() or get_by_name() if you don't know the IP m = Moku('192.168.69.245')
m = Moku('192.168.69.224')

try:
	i = PIDController()
	m.deploy_instrument(i)

	i.set_by_frequency(1, kp=-10*dB, i_xover=1e2, ii_xover=None, d_xover =1e4, si=10*dB, sd=10*dB)
	#i.set_by_gain(1, g, kp=0, ki=0, kd=0, kii=0, si=None, sd=None, in_offset=0, out_offset=0)

finally:
	m.close()