#
# pymoku example: Phasemeter data logging
#
# This example demonstrates how you can configure the Phasemeter instrument
# and log single-channel phase and [I,Q] data to a CSV file for a 10 
# second duration.
#
# (c) 2017 Liquid Instruments Pty. Ltd.
#
from pymoku import Moku, StreamException
from pymoku.instruments import *
import math, time

# Connect to your Moku by its device name
# Alternatively, use Moku.get_by_serial('#####') or Moku('192.168.###.###')
m = Moku.get_by_name('Moku')

# Prepare a new Phasemeter instrument to be deployed
i = Phasemeter()

# Deploy the new Phasemeter instrument to the Moku:Lab
# Also, try to synchronise the Moku:Lab to an external 10MHz reference
m.deploy_instrument(i, use_external=True)

try:
	# Set the Channel 1 seed frequency to 10MHz and a sample rate of ~30Hz
	i.set_initfreq(1, 10e6)
	i.set_samplerate('slow')

	# Restart the frequency-tracking loop on Channel 1
	i.reacquire(ch=1)

	# Stop an existing log, if any, then start a new one. 10 seconds of both channels to the
	# SD Card (rather than internal storage). Using CSV format.
	i.stop_data_log()
	i.start_data_log(duration=10, use_sd=True, ch1=True, ch2=False, filetype='csv')

	# Track progress percentage of the data logging session
	print("Waiting for completion.")
	while i.progress_data_log() < 100:
		time.sleep(1)

	# Upload the log file to the local directory
	i.upload_data_log()
	print("Uploaded log file to local directory.")

except StreamException as e:
	print("Error occured: %s" % e.message)
finally:
	# Denote that we are done with the data logging session so resources may be cleand up
	i.stop_data_log()
	m.close()