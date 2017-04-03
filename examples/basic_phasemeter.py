#
# pymoku example: Phasemeter networking streaming
#
# This example provides a network stream of Phasemeter
# data samples from Channel 1 and Channel 2. These samples
# are output in the form (I,Q,F,phi,counter) for each channel.
#
# (c) 2016 Liquid Instruments Pty. Ltd.
#
from pymoku import Moku, StreamException
from pymoku.instruments import *
import math

# The phasemeter is a little more complex than some instruments as its native output
# is a stream of measurements, accessed through the datalogger; rather than a sequence
# of frames containing a range of data.  This simple example just records 10 seconds of
# measurements to a CSV file.

m = Moku.get_by_name('example')
i = PhaseMeter()
# Set up Moku as a Phasemeter, and use the external 10MHz reference clock
m.deploy_instrument(i, use_external=True)

try:
	# Set the initial phase-lock loop frequency to 10MHz and a measurement rate of ~30Hz
	i.set_initfreq(1, 10e6)
	i.set_samplerate(PM_LOGRATE_SLOW)
	i.commit()

	# Stop an existing log, if any, then start a new one. 10 seconds of both channels to the
	# SD Card (rather than internal storage). Using CSV format.
	i.datalogger_stop()
	i.datalogger_start(duration=10, use_sd=False, ch1=True, ch2=False, filetype='csv')

	# Wait for log, and upload on completion. Also checks for any session errors
	i.datalogger_wait(upload=True)

except StreamException as e:
	print("Error occured: %s" % e.message)
finally:
	# "stop" does have a purpose if the logging session has already completed: It signals that
	# we no longer care about error messages and so on.
	i.datalogger_stop()
	m.close()