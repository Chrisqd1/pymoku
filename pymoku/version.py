
import pkg_resources as pkr

# List of compatible firmware builds
compat_fw = []

release = pkr.resource_stream(__name__, "version.txt").read().decode('utf-8')
