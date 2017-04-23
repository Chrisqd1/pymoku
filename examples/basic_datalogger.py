from pymoku import Moku, StreamException
from pymoku.instruments import *
import time

# Find your Moku device by name
# Alternatively, if you know the IP address, use Moku('192.168.###.###') 
# or by serial, Moku.get_by_serial('#####')
m = Moku.get_by_name('Jet Fuel')

# Configure the Moku to run a DataLogger instrument
i = DataLogger()
m.deploy_instrument(i)

try:
	# 10 samples per second
	i.set_samplerate(100)

	# Stop an existing log, if any, then start a new one. 10 seconds of both channels to the
	# SD Card (rather than internal storage). Use the Moku's binary file format for better speed
	# and size performance.
	i.stop_data_log()
	i.start_data_log(duration=30, use_sd=True, ch1=True, ch2=True, filetype='bin')

	# Track progress percentage of the data logging session
	progress = 0
	while progress < 100:
		# Sleep for a half second 
		time.sleep(0.5)
		# Get current progress percentage and print it out
		progress = i.progress_data_log()
		print("Progress {}%".format(progress))

	# Upload the log file to the local directory
	i.upload_data_log()
	print("Uploaded log file to local directory.")

	# Denote that we are done with the data logging session so resources may be cleand up
	i.stop_data_log()

except StreamException as e:
	print("Error occured: %s" % e.message)
finally:
	# Close the connection to the Moku
	m.close()
