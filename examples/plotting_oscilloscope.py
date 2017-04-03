from pymoku import Moku
from pymoku.instruments import *
import time, logging

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s::%(message)s')
logging.getLogger('pymoku').setLevel(logging.DEBUG)

m = Moku.get_by_name('Moku')

# See whether there's already an Oscilloscope running. If there is, take
# control of it; if not, attach a new Oscilloscope instrument
i = m.discover_instrument()
if i is None or i.type != 'oscilloscope':
	print("No or wrong instrument deployed")
	i = Oscilloscope()
	m.deploy_instrument(i)
else:
	print("Attached to existing Oscilloscope")
	m.take_ownership()


try:
	i.set_trigger(OSC_TRIG_CH1, OSC_EDGE_RISING, 0)

	i.synth_sinewave(2, 0.5, 10, 0) # Channel 2, 500mVpp, 10Hz, 0V offset
	i.set_source(2, OSC_SOURCE_DAC) # View this generated waveform on CH2

	i.set_timebase(-1, 1) # View +- 1 second, i.e. trigger in the centre

	i.commit() # Apply all changes.

	# Get initial frame to set up plotting parameters. This can be done once
	# if we know that the axes aren't going to change (otherwise we'd do
	# this in the loop)
	frame = i.get_frame()

	plt.ion()
	plt.show()
	plt.grid(b=True)
	plt.ylim([-1,1])
	plt.xlim([frame.xs[0], frame.xs[-1]])

	line1, = plt.plot([])
	line2, = plt.plot([])

	ax = plt.gca()
	ax.xaxis.set_major_formatter(FuncFormatter(frame.get_xaxis_fmt))
	ax.yaxis.set_major_formatter(FuncFormatter(frame.get_yaxis_fmt))
	ax.fmt_xdata = frame.get_xcoord_fmt
	ax.fmt_ydata = frame.get_ycoord_fmt

	while True:
		frame = i.get_frame()
		plt.pause(0.001)
		line1.set_ydata(frame.ch1)
		line2.set_ydata(frame.ch2)
		line1.set_xdata(frame.xs[0:len(frame.ch1)])
		line2.set_xdata(frame.xs[0:len(frame.ch2)])

finally:
	m.close()
