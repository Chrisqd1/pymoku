import pkg_resources as pkr

# List of compatible firmware builds
compat_fw = [474]

# List of compatible patches
compat_patch = [1]

# List of compatible packs
compat_packs = [('python-pymoku',	'28D72BBEFCB076F772ACCB25C7D698A2DA843054'),
				('mercury',			'28D72BBEFCB076F772ACCB25C7D698A2DA843054')]

# Compatible network protocol version
protocol_version = '7'

# Official release name
release = pkr.resource_stream(__name__, "version.txt").read().decode('utf-8')
