#
# pymoku example: Phasemeter networking streaming
#
# This example provides a network stream of Phasemeter
# data samples from Channel 1 and Channel 2. These samples
# are output in the form (I,Q,F,phi,counter) for each channel.
#
# (c) 2016 Liquid Instruments Pty. Ltd.
#
from pymoku import Moku
from pymoku.instruments import *
import math

# The phasemeter is a little more complex than some instruments as its native output
# is a stream of measurements, accessed through the datalogger; rather than a sequence
# of frames containing a range of data.  This simple example just records 10 seconds of
# measurements to a CSV file.

m = Moku('192.168.69.122')#.get_by_name('example')
i = PhaseMeter()
m.attach_instrument(i)

try:
	# Set the initial phase-lock loop frequency to 10MHz and a measurement rate of 10Hz
	i.set_initfreq(1, 10000000)
	i.set_samplerate(10)
	i.commit()

	# Stop any previous measurement and recording sessions if any and start a new CSV recording
	# session, single channel, 10 seconds long to the SD card.
	i.datalogger_stop()
	i.datalogger_start(start=0, duration=10, use_sd=True, ch1=True, ch2=False, filetype='csv')

	while True:
		if i.datalogger_completed():
			break

	# Check if there were any errors
	e = i.datalogger_error()
	if e:
		print("Error occured: %s" % e)

	i.datalogger_stop()
finally:
	m.close()