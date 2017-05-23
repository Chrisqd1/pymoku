from pymoku import Moku
from pymoku.instruments import *
import struct, logging, math
import matplotlib
import matplotlib.pyplot as plt

LENGTH  = 8192*8 #32bit words

logging.getLogger().setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console = logging.StreamHandler()
console.setFormatter(formatter)
console.setLevel(logging.INFO)
logging.getLogger().addHandler(console)

data = [0x0000, 0x1000, 0x2000, 0x3000, 0x4000,
        0x4000, 0x3000, 0x2000, 0x1000, 0x0000,
        (-0x1000) & 0xFFFF, (-0x1000) & 0xFFFF]

with open('data.dat', 'wb') as f:
	for d in data:
		f.write(struct.pack('<i', d))
	for i in range(LENGTH - len(data)):
		f.write(struct.pack('<i', 0))

	#channel 2
	for i in range(LENGTH):
		f.write(struct.pack('<i', 0))

m = Moku('192.168.1.99')
i = ArbWaveGen()
m.deploy_instrument(i)

try:
	i.set_defaults()
	i.mode1 = 3
	i.interpolation1 = True
	i.lut_length1 = len(data)-1
	i.phase_modulo1 = 2**17 * (len(data) + 50) - 1
	i.dead_value1 = -0x1000
	i.phase_step1 = 2**15

	i.mmap_access = True
	i.commit()

	m._send_file('j', 'data.dat')

	i.mmap_access = False
	i.enable1 = True
	i.commit()

	i.set_source(1, 'out', lmode='round')
	i.set_trigger('out1', 'rising', 0.0, hysteresis=0.05, mode='normal')
	i.set_timebase(-5e-8, 10e-8)
	i.commit()
	data = i.get_realtime_data(wait=True, timeout=10)
	plt.plot(data.time, data.ch1)
	plt.plot(data.time, data.ch2)
	plt.show()

finally:
	m.close()
