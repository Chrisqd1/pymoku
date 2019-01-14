import pkg_resources as pkr

# List of compatible firmware builds
compat_fw = [501]

# List of compatible patches
compat_patch = [0]

# List of compatible packs
compat_packs = []

# Compatible network protocol version
protocol_version = '7'

# Official release name
release = pkr.resource_stream(__name__, "version.txt").read().decode('utf-8')
