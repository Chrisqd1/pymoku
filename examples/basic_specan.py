from pymoku import Moku
from pymoku.instruments import *

# Create our Moku object and configure it to be a Spectrum Analyser.
# The constructor can take an IP address directly, or you can use the
# get_by_* functions to perform auto-discovery.
m = Moku('192.168.69.224')
i = SpecAn()
m.deploy_instrument(i)

try:
	# DC to 100MHz span, apply changes
	i.set_span(0, 10000000)

	# Get the scan results and print them out (power vs frequency, two channels)
	print(i.get_frame())
	
finally:
	# Close the connection to the Moku.
	m.close()
