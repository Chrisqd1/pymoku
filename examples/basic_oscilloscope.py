from pymoku import Moku
from pymoku.instruments import *

# Connect to your Moku device by using the device name
# Alternatively, if you know the IP address or serial number use 
# Moku('192.168.###.###') or Moku.get_by_serial('#####'), respectively
m = Moku.get_by_name('Jet Fuel')
i = m.discover_instrument()

if i is None or i.type != 'Oscilloscope':
	print("No or wrong instrument deployed")
	i = Oscilloscope()
	m.deploy_instrument(i)
else:
	print("Attached to existing Phasemeter")
	m.take_ownership()


try:
	# Span from -1s to 1s i.e. trigger point centred
	i.set_timebase(-1,1)

	# Get and print a single frame worth of data (time series
	# of voltage per channel)
	data = i.get_realtime_data(timeout=10)
	print(data.ch1,data.ch2,data.time)

finally:
	m.close()
