from pymoku import Moku, NoDataException
from pymoku.instruments import *
import time

# Use Moku.get_by_serial() or get_by_name() if you don't know the IP
m = Moku.get_by_name('example')
i = Oscilloscope()
m.attach_instrument(i)

try:
	# In this case, we set the underlying oscilloscope in to Roll mode then wait a bit to
	# acquire samples. One could also leave the oscilloscope in whatever other X Mode they
	# wished, pause the acquisition then stream from there to retrieve the high-res version
	# of a normal oscilloscope frame.
	i.set_samplerate(10)
	i.set_xmode(OSC_ROLL)
	i.commit()
	i.datalogger_stop()

	time.sleep(5)

	# Could also save to a file then use datalogger_upload(), but grabbing the data directly
	# from the network directly means the user can immediately process the data
	i.datalogger_start_single(filetype='net')

	while True:
		ch, idx, samples = i.datalogger_get_samples(timeout=5)

		print("Received samples %d to %d from channel %d" % (idx, idx + len(samples), ch))
except NoDataException as e:
	# This will be raised if we try and get samples but the session has finished.
	print("Finished")
finally:
	i.datalogger_stop()
	m.close()
