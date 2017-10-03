from pymoku.version import *

def firmware_is_compatible(build_id):
	if build_id == 65535:
		return None # Development build, unable to determine

	return build_id in compat_fw

def list_compatible_firmware():
	return compat_fw