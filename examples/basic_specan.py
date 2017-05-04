from pymoku import Moku
from pymoku.instruments import *

# Connect to your Moku by its device name
# Alternatively, use Moku.get_by_serial('#####') or Moku('192.168.###.###')
m = Moku.get_by_name('Moku')

# Prepare the Spectrum Analyser instrument
i = SpectrumAnalyser()

# Deploy the Spectrum Analyser to your Moku
m.deploy_instrument(i)

try:
	# DC to 10MHz span, apply changes
	i.set_span(0, 10e6)

	# Get the scan results and print them out (power vs frequency, two channels)
	data = i.get_data()
	print(data.ch1, data.ch2, data.frequency)

finally:
	# Close the connection to the Moku.
	m.close()
