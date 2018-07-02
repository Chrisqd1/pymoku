import pkg_resources as pkr

# List of compatible firmware builds
compat_fw = [474]

# List of compatible patches
compat_patch = [1]

# List of compatible packs
compat_packs = [('python-pymoku',	'898FEC789F1666B19FBC57DD384C79AEC5D2BB00'),
				('mercury',			'898FEC789F1666B19FBC57DD384C79AEC5D2BB00')]

# Compatible network protocol version
protocol_version = '7'

# Official release name
release = pkr.resource_stream(__name__, "version.txt").read().decode('utf-8')
