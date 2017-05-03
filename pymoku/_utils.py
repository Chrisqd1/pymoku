"""
	Global utility functions
"""
def str_to_val(valmap, key, param_description):
	"""
		Returns the mapped value of the input key string.

		If there is no such key, an error is raised with the given message.

		Helper function - enables mapping of client strings to bit/register values.
	"""
	try:
		return valmap[key.lower()]
	except KeyError:
		raise ValueError("Invalid %s : \'%s\'. Expected %s." % (param_description, key, valmap.keys()))


def formatted_timestamp():
	import time
	return time.strftime("%Y-%m-%d T %H:%M:%S %z")
