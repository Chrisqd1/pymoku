import os, os.path
import requests
import json

import pymoku.version

cache_dir = os.path.expanduser('~/.moku/')
compat_file = os.path.join(cache_dir, 'compat.json')

try:
	os.mkdir(cache_dir)
except OSError:
	pass # Already exists

def pymoku_updates(server, username, password):
	params = { 'build_id__gte' : pymoku.version.build }
	r = requests.get(server + '/versions/update/pymoku/', params=params, auth=(username, password))
	return r.json()

def compatable_configurations(server, username, password):
	params = { 'build_id' : pymoku.version.build }

	try:
		r = requests.get(server + '/versions/compat/pymoku/', params=params, auth=(username, password))
		ret = r.json()
	except:
		if os.path.exists(compat_file):
			ret = json.loads(open(compat_file).read())
		else:
			raise Exception("Can't download compatibility information and none has been cached locally.")

	open(compat_file, 'w').write(json.dumps(ret))

	return ret

def firmware_is_compatible(build_id, server=None, username=None, password=None):
	if build_id == 65535:
		return None # Development build, unable to determine

	try:
		configs = compatable_configurations(server, username, password)
		compat_fw = set([ c['firmware']['build_id'] for c in configs.values() ])
	except:
		return None
	return build_id in compat_fw
