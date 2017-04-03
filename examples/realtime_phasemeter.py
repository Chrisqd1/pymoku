#
# pymoku example: Phasemeter networking streaming
#
# This example provides a network stream of Phasemeter
# data samples from Channel 1 and Channel 2. These samples
# are output in the form (I,Q,F,phi,counter) for each channel.
#
# (c) 2016 Liquid Instruments Pty. Ltd.
#
from pymoku import Moku, NoDataException, StreamException, FrameTimeout
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
m.deploy_instrument(i, use_external=False)

try:
	# Set the initial phase-lock loop frequency to 10MHz and measurement rate to ~120Hz
	i.set_initfreq(1, 10e6)
	i.set_samplerate(PM_LOGRATE_FAST)
	i.commit()

	# Stop previous recording session, if any, then start a new datalogging measurement
	# session, streaming to the network so we can look at it in real time.
	i.datalogger_stop()
	i.datalogger_start(duration=10, ch1=True, ch2=False, filetype='net')
	
	amplitudes = []

	while True:

		# Check for any errors in datalogging session
		i.datalogger_error()

		try:
			ch, idx, samples = i.datalogger_get_samples(timeout=10)
		except NoDataException as e:
			print("Data stream complete")
			break

		for s in samples:
			# s is of the form [fs, f, count, phase, I, Q]
			# Convert I,Q to amplitude and append to data
			amplitudes.append(math.sqrt(s[4]**2 + s[5]**2))

	print(amplitudes)

except StreamException as e:
	print("Error occured: %s" % e.message)
except FrameTimeout:
	print("Logging session timed out")
finally:
	# "stop" does have a purpose if the logging session has already completed: It signals that
	# we no longer care about error messages and so on.
	i.datalogger_stop()
	m.close()