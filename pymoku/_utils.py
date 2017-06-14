from . import ValueOutOfRangeException

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

def check_parameter_valid(check_type, v, allowed=None, desc="", units=""):
	if check_type == 'bool':
		if not isinstance(v, bool):
			raise ValueError("Invalid parameter \'%s\': %s. Expected boolean value [True,False]." % (desc, v))
	elif not isinstance(allowed, (list,tuple)):
		raise ValueError("Invalid parameter 'allowed': %s. Expected array or tuple." % allowed)
	elif check_type == 'set':
		if not (v in allowed):
			raise ValueError("Invalid \'%s\': %s. Valid set %s." % (desc, v, allowed))
	elif check_type == 'range':
		if not (len(allowed) == 2):
			raise ValueError("Invalid allowed range %s. Expected [MIN,MAX]." % allowed)
		elif isinstance(allowed, tuple) and not (v > allowed[0] and v < allowed[1]):
			raise ValueOutOfRangeException("Invalid %s: %s. Valid range (%s, %s) %s." % (desc, v, allowed[0], allowed[1], units))
		elif not ((v >= allowed[0]) and (v <= allowed[1])):
			raise ValueOutOfRangeException("Invalid %s: %s. Valid range [%s, %s] %s." % (desc, v, allowed[0], allowed[1], units))
	else:
		raise ValueError("Invalid parameter 'check_type': %s. Expected ['bool','set','range']." % check_type)

def formatted_timestamp():
	import time
	return time.strftime("%Y-%m-%d T %H:%M:%S %z")
