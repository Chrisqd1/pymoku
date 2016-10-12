#!/usr/bin/env python

from pymoku import Moku
import sys, logging

logging.basicConfig(format='%(asctime)s:%(name)s:%(levelname)s::%(message)s')
log = logging.getLogger()
log.setLevel(logging.DEBUG)

if len(sys.argv) != 3:
	print "Usage %s <ip> <packname>" % sys.argv[0]
	exit(1)

m = Moku(sys.argv[1])

pack = sys.argv[2]
sha = pack + '.sha256'

try:
	m._send_file('p', pack)
except IOError:
	log.exception("Can't load pack")
	m.close()
	exit(1)


try:
	m._send_file('p', sha)
except IOError:
	log.warning("Can't load signature, this will not be deployable in release mode")
finally:
	m.close()
