from pymoku import Moku
from pymoku.instruments import *
import time, logging

from natu.units import dB

import matplotlib
import matplotlib.pyplot as plt

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s::%(message)s')
logging.getLogger('pymoku').setLevel(logging.DEBUG)

# Use Moku.get_by_serial() or get_by_name() if you don't know the IP m = Moku('192.168.69.245')
m = Moku('192.168.69.235')


i = PIDController()
m.deploy_instrument(i)

# i.set_by_frequency(1, kp=0*dB)
i.set_by_frequency(1, kp=0*dB, i_xover = 1e4, ii_xover = 1e3, d_xover = 1e3, si = 10*dB)
# i.set_by_gain(1, 1, kp=0.01, ki = 10e3, kii = 0, si = 10, kd = 0, sd = None)
# i.set_by_frequency(2, kp=0*dB)

m.close()