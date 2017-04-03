from pymoku import Moku
from pymoku.instruments import *

# Can directly call the constructor with an IP address, or use
# get_by_name or get_by_serial for autodiscovery.
m = Moku.get_by_name('Moku')
i = Oscilloscope()
m.deploy_instrument(i)

try:
	# Span from -1s to 1s i.e. trigger point centred
	i.set_timebase(-1, 1)
	i.commit()

	# Get and print a single frame's worth of data (time series
	# of voltage per channel)
	print(i.get_frame())

finally:
	m.close()
