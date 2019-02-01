#
# pymoku example: Plotting Oscilloscope with pyqtgraph
#
# This example demonstrates how you can configure the Oscilloscope instrument,
# and view triggered time-voltage data frames in real-time.
#
# pyqtgraph is used here as an alternative to matplotlib, it has more severe
# dependencies (i.e. Qt libraries), but is capable of significantly higher
# frame rates.
#
# (c) 2019 Liquid Instruments Pty. Ltd.
#
from pymoku import Moku
from pymoku.instruments import Oscilloscope
import time
import pyqtgraph as pg

from pyqtgraph.Qt import QtGui, QtCore

# Connect to your Moku by its device name
# Alternatively, use Moku.get_by_serial('#####') or Moku('192.168.###.###')
m = Moku.get_by_name('Moku')

app = QtGui.QApplication([])

try:
	i = m.deploy_or_connect(Oscilloscope)

	# Trigger on input Channel 1, rising edge, 0V with 0.1V hysteresis
	i.set_trigger('in1', 'rising', 0, hysteresis = 0.1)

	 # View +- 1 second, i.e. trigger in the centre
	i.set_timebase(-1, 1)

	# Generate an output sinewave on Channel 2, 500mVpp, 10Hz, 0V offset
	i.gen_sinewave(2, 0.5, 5, 0)

	# Set the data source of Channel 1 to be Input 1
	i.set_source(1, 'in')

	# Set the data source of Channel 2 to the generated output sinewave
	i.set_source(2, 'out')

	# Create one plot with two curves, drawn with two pens (different colours)
	p = pg.plot()
	line1 = p.plot(pen=(1,2))
	line2 = p.plot(pen=(2,2))

	# Called on an immediate-expiry timer from the QApplication main loop
	def update():
		global line1, line2
		data = i.get_realtime_data()

		# Update the plot
		line1.setData(data.time, data.ch1)
		line2.setData(data.time, data.ch2)

	timer = QtCore.QTimer()
	timer.timeout.connect(update)
	timer.start(0)

	QtGui.QApplication.instance().exec_()
finally:
	# Close the connection to the Moku device
	# This ensures network resources and released correctly
	m.close()
