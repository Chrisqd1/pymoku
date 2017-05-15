from pymoku import Moku
from pymoku.instruments import *
import struct, logging
import matplotlib
import matplotlib.pyplot as plt

LENGTH  = 8192*8 #32bit words

logging.getLogger().setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console = logging.StreamHandler()
console.setFormatter(formatter)
console.setLevel(logging.INFO)
logging.getLogger().addHandler(console)

with open('data.dat', 'wb') as f:
	for i in range(LENGTH*2):
		f.write(struct.pack('<i', i))

m = Moku('192.168.1.99')
i = ArbWaveGen()
m.deploy_instrument(i)

try:
	i.set_defaults()
	i.set_timebase(-1e-6, 3e-6)
	i.mode = 0
	i.interpolation = True
	i.out1_frequency = 1.532e2
	i.out1_enable = True
	i.set_source(1, 'out', lmode='round')
	i.set_trigger('out1', 'rising', 0.1, hysteresis=0.05, mode='normal')
	i.set_xmode('fullframe')
	i.commit()

	# m._send_file('j', 'data.dat')
	from subprocess import check_output
	for n in range(8):
		offset = 0x48000000 + (0x2000 * 4 * n)
		# check_output('ssh root@192.168.1.99 \"/sbin/devmem 0x%08X 32 0x0C00\"' % (offset + 0x7FF8), shell=True)

		check_output('ssh root@192.168.1.99 \"/sbin/devmem 0x%08X 32 0x0400\"' % (offset + 0x00), shell=True)
		check_output('ssh root@192.168.1.99 \"/sbin/devmem 0x%08X 32 0x0800\"' % (offset + 0x04), shell=True)
		check_output('ssh root@192.168.1.99 \"/sbin/devmem 0x%08X 32 0x0C00\"' % (offset + 0x08), shell=True)
		check_output('ssh root@192.168.1.99 \"/sbin/devmem 0x%08X 32 0x1000\"' % (offset + 0x0C), shell=True)
		check_output('ssh root@192.168.1.99 \"/sbin/devmem 0x%08X 32 0x1400\"' % (offset + 0x10), shell=True)
		check_output('ssh root@192.168.1.99 \"/sbin/devmem 0x%08X 32 0x1800\"' % (offset + 0x14), shell=True)
		check_output('ssh root@192.168.1.99 \"/sbin/devmem 0x%08X 32 0x1C00\"' % (offset + 0x18), shell=True)
		check_output('ssh root@192.168.1.99 \"/sbin/devmem 0x%08X 32 0x2000\"' % (offset + 0x1C), shell=True)

		check_output('ssh root@192.168.1.99 \"/sbin/devmem 0x%08X 32 0x1000\"' % (offset + 0x40), shell=True)
		check_output('ssh root@192.168.1.99 \"/sbin/devmem 0x%08X 32 0x1000\"' % (offset + 0x44), shell=True)
		check_output('ssh root@192.168.1.99 \"/sbin/devmem 0x%08X 32 0x1000\"' % (offset + 0x48), shell=True)

		check_output('ssh root@192.168.1.99 \"/sbin/devmem 0x%08X 32 0x1000\"' % (offset + 0x50), shell=True)
		check_output('ssh root@192.168.1.99 \"/sbin/devmem 0x%08X 32 0x0C00\"' % (offset + 0x54), shell=True)
		check_output('ssh root@192.168.1.99 \"/sbin/devmem 0x%08X 32 0x0800\"' % (offset + 0x58), shell=True)
		check_output('ssh root@192.168.1.99 \"/sbin/devmem 0x%08X 32 0x0400\"' % (offset + 0x5C), shell=True)

	i.set_trigger('out1', 'rising', 0.1, hysteresis=0.05, mode='normal')
	i.set_xmode('fullframe')
	i.commit()
	data = i.get_realtime_data(wait=True, timeout=10)

	plt.plot(data.time, data.ch1)
	plt.plot(data.time, data.ch2)
	plt.show()

finally:
	m.close()
