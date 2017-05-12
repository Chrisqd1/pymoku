#
# pymoku example: Configuring your Moku
#
# This example demonstrates how you can search for Mokus on your network,
# connect to a specific Moku:Lab device and  
# device including:
# 	- Device Name
# 	- UFO light colour
#	- Finding all Mokus on the network
#
# (c) 2017 Liquid Instruments Pty. Ltd.
#
from pymoku import Moku

try:
	# Search for any Mokus on the current network
	mokus = Moku.list_mokus()

	# Connect to a single Moku
	m = Moku.get_by_name('Jet Fuel')

	# Register ownership of the device
	m.take_ownership()

	print("Connected to Moku:Lab device")
	print("Name: %s, Serial: %s" % (m.get_name(), m.get_serial()))
	print("LED Colour: %s" % m.get_led_colour())

finally:
	m.close()