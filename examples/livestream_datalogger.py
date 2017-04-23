from pymoku import Moku, MokuException, StreamException
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
	# 10Hz sample rate
	i.set_samplerate(10)

	# Stop a previous session, if any, then start a new single-channel log in real
	# time over the network.
	i.stop_stream_data()
	i.start_stream_data(duration=10, ch1=False, ch2=True)

	while True:
		samples = i.get_stream_data(n=10)
		if not any(samples): break
		print("Received: Channel 1 (%d smps), Channel 2 (%d smps)" % (len(samples[0]),len(samples[1])))
	
	# Denote that we are done with the data streaming session so resources may be cleand up
	i.stop_stream_data()

except StreamException as e:
	print("Error occured: %s" % e.message)

finally:
	m.close()
