
from os.path import join, dirname

try:
	import os
	build = int(os.environ['BUILD_NUMBER'])
except:
	build = 65535

vpath = join(dirname(__file__), 'version.txt')

release = open(vpath).read()
