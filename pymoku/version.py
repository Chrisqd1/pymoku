import pkg_resources as pkr

# List of compatible firmware builds
compat_fw = [474]

# List of compatible patches
compat_patch = [1]

# List of compatible packs
compat_packs = [('python-pymoku',	'57BDBF1134457E20FCFCF3B89C17742CA3E6FB52'), 
				('mercury',			'57BDBF1134457E20FCFCF3B89C17742CA3E6FB52')]

# Compatible network protocol version
protocol_version = '7'

# Official release name
release = pkr.resource_stream(__name__, "version.txt").read().decode('utf-8')
