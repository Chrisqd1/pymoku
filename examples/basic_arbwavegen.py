from pymoku import Moku
from pymoku.instruments import *
import struct, logging, math
import matplotlib
import matplotlib.pyplot as plt

import pickle, base64, zlib

LENGTH  = 8192 #32bit words

logging.getLogger().setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console = logging.StreamHandler()
console.setFormatter(formatter)
console.setLevel(logging.INFO)
logging.getLogger().addHandler(console)

xdata, ydata = pickle.loads(zlib.decompress(base64.b64decode(
'''eNpdVjmWXDEIzOckjvwAsekIPoZzBw58/2dUoP7dM8mntQFFUcyPH3/+0tcv
   cfJlX79/iW0lgZFMvRISDMODVxusCqP+Ngw1SxjLLGAIucMgEWxpOuG6hi2c
   Ud9mbeTS3iK2ORPet2bLSIVgsNG40OytVfc7njWHPVbHHJs7jHSdBOeMMymC
   95PvxnlOOkuL1llT8uNRPU4CFnaO+Jazl71XP87iTjq/mPbGlw1Ps7ifq7xy
   H5+sDnQqA6DNBZtgPwBNnQfUXAuOZ/n8TPfzCZNzyY3OnrVL4zgvqul5aG3c
   qyIgxa14bft53G7aVQgYT8lXNqAZ1hCneA58U8VknTMFQN9yj35n+PF60CnM
   vq2s1RXa2bcep9umeLUy8dgwb7vMdUJ6ZTDN4S38fr0QB6IkB/ii7Ml4M/JG
   2VC8zN1wA/UgJLlQG0nu0qOuSxh4Uicbze6FtLiq/eZR279IVxihcyIAIfQS
   Z3L7o+dCFSJ1ANScXC7IsZua5tuH0OrTe6uheDPCp1EvxbOKdAtxbjU3kZgI
   3lkMThdfwHBFue+HqUnEuKCExAzUCN4fsT8hF/PpIxtnQ805m7Qwm979WRTN
   SLxwvTI6cEKRWP6Eyb7Xk0LiYRpOXy4q+4fxwuIxQkYbUkbGXlAmjXq5ylXB
   YeerEpmx3lIvAeWv0/nd8cV4dG5sQ+eCpVGN3XxEbtlOdrNwVLG56NzyUob0
   erXXRVhkDTtG94JiwpVpJvOughm7fDOqeT4P+6BmbjJ0YxshNWkXups2j1FK
   M4jQnQs2iPhQpobBaHV1ss2AiP3NiPFeqt1nrMt8rg+RTamrqM3CMnwerNNt
   eGvrKd6IVlV6KhR0JWpfiWrEnBdSnt6nkX3IpipE1BdchiK5NPCppAlFI8XL
   TKkj/N7y0zTIBaHJ6j88AeRL+/BRTD/twaSB6WgNvIWiWxx7ERDEkd5UFGCe
   9h5KLtDnwpTePhtD1CcPB7nnQgqenk/s6MkCLL078Uhqx2lgK5ipPWLVUVjd
   GCaTSk1SeNjagKGu0cjUQOXH3416QVZvuI7Oqmr1Xo/ZIHsuFGNHo7uMPcFK
   iKFMXcm4441zap70bbyt7dNAe8ZbXMH121Ivo8M5ty6bWjPPMIP/nv/oem+5
   11btwNgt9+st9I65KTB58HRb9j8BNTRwEOq00Um8AcbjCfkNpxtuhCMfAdbc
   pPWZRJ2lz/y2yoAR+87WadoLT2kJ8+2oOWNsH+iWTqGF6I6ZrsYICpL+91e+
   fv4HtdVAJw=='''
)))

m = Moku('192.168.1.99')
i = ArbWaveGen()
m.deploy_instrument(i)

try:
	i.set_defaults()
	i.interpolation1 = True
	i.interpolation2 = True
	i.phase_modulo1 = 2**30 * len(xdata)
	i.phase_modulo2 = 2**30 * len(ydata)
	i.dead_value1 = 0x0000
	i.dead_value2 = 0x0000
	i.phase_step1 = 2**27
	i.phase_step2 = 2**27

	i.write_lut(1, xdata, 3)
	i.write_lut(2, ydata, 3)

	i.enable1 = True
	i.enable2 = True
	i.phase_rst1 = True
	i.phase_rst2 = True
	i.offset2 = 0.1
	i.amplitude1 = 1.0
	i.amplitude2 = 1.0
	i.commit()

	i.set_source(1, 'out', lmode='round')
	i.set_source(2, 'out', lmode='round')
	i.set_trigger('out1', 'rising', 0.0, hysteresis=0.05, mode='auto')
	i.set_timebase(0.0, 5e-5)
	data = i.get_realtime_data(wait=True, timeout=10)
	plt.plot(data.ch1, data.ch2)
	plt.show()

finally:
	m.close()
