#
# pymoku example: Phasemeter networking streaming
#
# This example provides a 10-second network stream of Phasemeter data 
# samples from Channel 1. These samples are in the form [fs, f, count, phase, I, Q].
# Real-time processing of instrument data is demonstrated by calculating the 
# signal amplitude of each sample (A = I^2 + Q^2) and printing the results
# at the end of the streaming session. 
#
# (c) 2017 Liquid Instruments Pty. Ltd.
#
from pymoku import Moku, NoDataException, StreamException, FrameTimeout
from pymoku.instruments import *
import math

# Connect to your Moku by its device name
# Alternatively, use Moku.get_by_serial('#####') or Moku('192.168.###.###')
m = Moku.get_by_name('Moku')

# See whether there's already a Phasemeter running. If there is, take
# control of it; if not, deploy a new Phasemeter instrument
i = m.discover_instrument()

if i is None or i.type != 'phasemeter':
	print("No or wrong instrument deployed")
	# Create a new Phasemeter instrument ready for deploy
	i = Phasemeter()
	# Deploy it with external reference clock input disabled
	# Do this when you don't need to lock your Moku:Lab to an external 10MHz reference clock
	m.deploy_instrument(i, use_external=False)
else:
	print("Attached to existing Phasemeter")
	# Taking ownership after discovering a running instrument is necessary so the
	# Moku:Lab knows to listen to your commands, and not another client's
	m.take_ownership()

try:
	# Set the initial phase-lock loop frequency to 10MHz and measurement rate to ~120Hz
	i.set_initfreq(1, 10e6)
	i.set_samplerate('fast')

	# Stop previous recording session, if any, then start a new datalogging measurement
	# session, streaming to the network so we can look at it in real time.
	i.stop_stream_data()
	i.start_stream_data(duration=10, ch1=True, ch2=False)

	amplitudes = []

	while True:
		# Get 10 samples off the network at a time
		samples = i.get_stream_data(n=10)

		# Break out of this loop if we received no samples
		# This denotes the end of the streaming session
		if not any(samples): break

		for s in samples[0]:
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
	i.stop_stream_data()
	
	m.close()