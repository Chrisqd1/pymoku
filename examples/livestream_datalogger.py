from pymoku import Moku, MokuException, NoDataException
from pymoku.instruments import *
import time

# Use Moku.get_by_serial() or get_by_name() if you don't know the IP
m = Moku.get_by_name('example')
i = Oscilloscope()
m.deploy_instrument(i)

try:
	# 10Hz sample rate. The datalogger is actually just a mode of the Oscilloscope
	# instrument in ROLL mode.
	i.set_samplerate(10)
	i.set_xmode('roll')

	# Stop a previous session, if any, then start a new single-channel log in real
	# time over the network.
	i.datalogger_stop()
	i.datalogger_start(start=0, duration=100, ch1=True, ch2=False, filetype='net')

	while True:
		ch, idx, samples = i.datalogger_get_samples()

		print("Received samples %d to %d from channel %d" % (idx, idx + len(samples) - 1, ch))
except NoDataException:
	print("Finished")
finally:
	i.datalogger_stop()
	m.close()
