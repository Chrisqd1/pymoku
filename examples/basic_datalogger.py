from pymoku import Moku
from pymoku.instruments import *
import time

m = Moku.get_by_name('example')

# Data logger is actually a mode of the Oscilloscope instrument
i = Oscilloscope()
m.attach_instrument(i)

try:
	# 10 samples per second. Data logging must use the Oscilloscope's ROLL mode.
	i.set_samplerate(10)
	i.set_xmode(OSC_ROLL)
	i.commit()

	# Stop an existing log, if any, then start a new one. 10 seconds of both channels to the
	# SD Card (rather than internal storage). Use the Moku's binary file format for better speed
	# and size performance.
	i.datalogger_stop()
	i.datalogger_start(start=0, duration=10, use_sd=True, ch1=True, ch2=True, filetype='bin')

	# Poll to see how the log is progressing. Note that the "time to end" might become negative
	# as the log will take a bit of time to finalise things once the duration has expired.
	while True:
		time.sleep(1)
		trems, treme = i.datalogger_remaining()
		samples = i.datalogger_samples()
		print("Captured (%d samples); %d seconds from start, %d from end" % (samples, trems, treme))

		if i.datalogger_completed():
			break

	e = i.datalogger_error()
	if e:
		print("Error occured: %s" % e)

	# "stop" does have a purpose if the logging session has already completed: It signals that
	# we no longer care about error messages and so on.
	i.datalogger_stop()

	# Upload the recorded file off the SD Card to our current directory.
	i.datalogger_upload()
except Exception as e:
	print(e)
finally:
	m.close()
