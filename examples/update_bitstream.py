from pymoku import Moku
import sys, logging

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s::%(message)s')
log = logging.getLogger()
log.setLevel(logging.DEBUG)

if len(sys.argv) not in [3, 4]:
	print "Usage: %s ip bitstream [rename-to]" % sys.argv[0]
	exit(1)

m = Moku(sys.argv[1])

try:
	rename = sys.argv[3]
except IndexError:
	rename = None

try:
	m.load_bitstream(sys.argv[2], rename)
except:
	log.exception("Update Failed")
finally:
	m.close()
