#
# pymoku example: Phasemeter networking streaming
#
# This example provides a network stream of Phasemeter
# data samples from Channel 1 and Channel 2. These samples
# are output in the form (I,Q,F,phi,counter) for each channel.
#
# (c) 2016 Liquid Instruments Pty. Ltd.
#
from pymoku import Moku, NoDataException
from pymoku.instruments import *
import math

# The phasemeter is a little more complex than some instruments as its native output
# is a stream of measurements, accessed through the datalogger; rather than a sequence
# of frames containing a range of data.  One can record this stream to a CSV or binary
# file, but this example streams the samples over the network so they can be accessed
# and prcessed in real time.  In this particular case, the only processing we do is
# to convert I and Q to amplitude and record that.

m = Moku.get_by_name('example')
i = PhaseMeter()
m.attach_instrument(i)

try:
	# Set the initial phase-lock loop frequency to 10MHz and measurement rate to 10Hz
	i.set_initfreq(1, 10000000)
	i.set_samplerate(10)
	i.commit()

	# Stop previous recording session, if any, then start a new datalogging measurement
	# session, streaming to the network so we can look at it in real time.
	i.datalogger_stop()
	i.datalogger_start(start=0, duration=10, ch1=True, ch2=False, filetype='net')
	
	amplitudes = []

	while True:
		try:
			ch, idx, samples = i.datalogger_get_samples()
		except NoDataException as e:
			print("Data stream complete")
			break

		for s in samples:
			# s is of the form [fs, f, count, phase, I, Q]
			# Convert I,Q to amplitude and append to data
			amplitudes.append(math.sqrt(s[4]**2 + s[5]**2))

	# Check if there were any errors
	e = i.datalogger_error()
	if e:
		print("Error occured: %s" % e)

	i.datalogger_stop()

	print(amplitudes)
except Exception as e:
	print(e)
finally:
	m.close()