#
# pymoku example: Phasemeter networking streaming
#
# This example starts a 10-second network stream of Channel 1 Phasemeter data and processes
# it live. The contents of each data sample are printed out, along with the signal amplitude
# which may be calculated as A = (I^2 + Q^2).
#
# (c) 2017 Liquid Instruments Pty. Ltd.
#
from pymoku import *
from pymoku.instruments import Phasemeter
import math

# Connect to your Moku by its device name
# Alternatively, use Moku.get_by_serial('#####') or Moku('192.168.###.###')
m = Moku.get_by_name('Moku')

# Phasemeter deploy/discovery
# ---------------------------
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
	# Phasemeter configuration
	# -------------------------
	# Set the measurement rate to ~120Hz
	i.set_samplerate('fast')

	# Automatically acquire a PLL seed frequency for both channels
	i.auto_acquire()

	# Network stream configuration
	# -------------------------
	# Stop previous network session, if any
	i.stop_stream_data()

	# Start a new Phasemeter network stream
	# Channel 1 enabled, Duration 10 seconds
	i.start_stream_data(duration=10, ch1=True, ch2=False)

	# Handle network stream samples
	# -------------------------
	# This loop continuously retrieves Phasemeter Channel 1 data samples off the network
	# and prints out their contents. It breaks out of the loop when there are no samples
	# received, indicating the end of the streaming session.
	while True:
		# Get 10 samples off the network at a time
		samples = i.get_stream_data(n=10)

		# No samples indicates end of stream
		if not any(samples): break

		# Process the received samples
		# Here we just print the contents of Channel 1 samples
		# Along with signal amplitude (I^2 + Q^2)
		ch1_samples = samples[0]
		for s in ch1_samples:
			# s is of the form [fs, f, count, phase, I, Q]
			print("Ch1 - fs: %f, f: %f, phase: %f, amplitude: %f" % (s[0],s[1],s[3],math.sqrt(s[4]**2 + s[5]**2)))

except StreamException as e:
	print("Error occured: %s" % e)
except FrameTimeout:
	print("Logging session timed out")
finally:
	# Make sure you stop a network stream to release network resources and
	# clean up session metadata
	i.stop_stream_data()

	# Close the connection to the Moku:Lab
	m.close()