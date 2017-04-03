from pymoku import Moku, StreamException
from pymoku.instruments import *
import time

m = Moku.get_by_name('example')

# Data logger is actually a mode of the Oscilloscope instrument
i = Oscilloscope()
m.deploy_instrument(i)

try:
	# 10 samples per second. Data logging must use the Oscilloscope's ROLL mode.
	i.set_samplerate(10)
	i.set_xmode(OSC_ROLL)
	i.commit()

	# Stop an existing log, if any, then start a new one. 10 seconds of both channels to the
	# SD Card (rather than internal storage). Use the Moku's binary file format for better speed
	# and size performance.
	i.datalogger_stop()
	i.datalogger_start(duration=10, use_sd=True, ch1=True, ch2=True, filetype='csv')

	# Wait until logging session has completed and upload file to current directory
	# Implicitly checks for logging session errors
	i.datalogger_wait(upload=True)

except StreamException as e:
	print("Error occured: %s" % e.message)
finally:
	# "stop" does have a purpose if the logging session has already completed: It signals that
	# we no longer care about error messages and so on.
	i.datalogger_stop()
	m.close()
