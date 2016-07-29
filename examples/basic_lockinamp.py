from pymoku import Moku
from pymoku.instruments import *
import time, logging

import matplotlib
import matplotlib.pyplot as plt

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s::%(message)s')
logging.getLogger('pymoku').setLevel(logging.DEBUG)

# Use Moku.get_by_serial() or get_by_name() if you don't know the IP
m = Moku('192.168.69.246')

i = m.discover_instrument()
print i
# if i is None or i.type != 'lockinamp':
	# print "No or wrong instrument deployed"
i = LockInAmp()
m.attach_instrument(i)
# else:
	# print "Attached to existing Lockin Amplifier"



line1, = plt.plot([])
line2, = plt.plot([])
plt.ion()
plt.show()
plt.grid(b=True)
plt.ylim([-10000, 10000])
plt.xlim([0,1024])

try:
	last = 0
	i.set_defaults()
	i.commit()

	# while True:

	# 	frame = i.get_frame()

	# 	print type(frame)

	# 	plt.pause(0.001)
	# 	line1.set_ydata(frame.ch1)
	# 	line2.set_ydata(frame.ch2)
	# 	line1.set_xdata(range(1024))
	# 	line2.set_xdata(range(1024))

	# 	plt.draw()

finally:
	m.close()
