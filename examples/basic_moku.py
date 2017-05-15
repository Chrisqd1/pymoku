#
# pymoku example: Configuring your Moku
#
# This example demonstrates how you can search for Mokus on your network,
# connect to a specific Moku:Lab device and retrieve settings such as:
# 	- Device Name
# 	- UFO light colour
# 	- Serial number
#	- IP address
#
# These and other Moku:Lab device settings can be configured using 
# Moku.set_* type functions on a connected Moku object (as opposed to 
# Moku.get_* used here)
#
# (c) 2017 Liquid Instruments Pty. Ltd.
#
from pymoku import Moku

# This will hold our connected Moku object
moku = None

try:
	# Search for any Mokus on the current network
	mokus = Moku.list_mokus()

	# Moku search failed
	if not any(mokus):
		print("Unable to find any Mokus! Check your Moku:Lab is connected to the network.")
	else:
		# Print details of all Moku:Labs found on the network
		print("Found Moku:Labs!")
		for i,m in enumerate(mokus):
			print("%d. %s, %s, %s" % (i+1,m[0],m[1],m[2]))

		# Extract the IP address of the first found Moku:Lab device on the network
		moku_ip = mokus[0][0]

		# Establish a connection to this Moku:Lab device using its IP address
		moku = Moku(moku_ip)

		# Print out configuration info of this Moku:Lab
		print("\nConnected to a Moku:Lab device!")
		print("Name: %s\nSerial: %s\nIP: %s" % (moku.get_name(), moku.get_serial(), moku.get_ip()))
		print("LED Colour: %s" % moku.get_led_colour())

finally:
	# Close off the network connection to the Moku:Lab device (if any)
	if moku:
		moku.close()