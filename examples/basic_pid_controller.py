from pymoku import Moku
from pymoku.instruments import *
import time, logging

from natu.units import dB

import matplotlib
import matplotlib.pyplot as plt

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s::%(message)s')
logging.getLogger('pymoku').setLevel(logging.DEBUG)

# Use Moku.get_by_serial() or get_by_name() if you don't know the IP m = Moku('192.168.69.245')
m = Moku('192.168.69.224')


i = PIDController()
m.deploy_instrument(i)

# i.set_by_frequency(1, kp=0*dB)
#i.set_by_frequency(1, kp=-10*dB, i_xover = 10000, si = 20*dB)
i.set_by_gain(1, 1,kp=0.3, ki = 1e3, kii = 1e3, si = 10)
# i.set_by_frequency(2, kp=0*dB)

m.close()
 