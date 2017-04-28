
import pkg_resources as pkr

release = pkr.resource_stream(__name__, "version.txt").read().strip()
