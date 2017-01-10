from pymoku import Moku
from pymoku.instruments import *

# Create our Moku object and configure it to be a Spectrum Analyser.
# The constructor can take an IP address directly, or you can use the
# get_by_* functions to perform auto-discovery.
m = Moku.get_by_name('example')
i = SpecAn()
m.attach_instrument(i)

# DC to 100MHz span, apply changes
i.set_span(0, 100000)
i.commit()

# Get the scan results and print them out (power vs frequency, two channels)
print(i.get_frame())

# Close the connection to the Moku.
m.close()
