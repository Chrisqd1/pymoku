
from os.path import join, dirname

vpath = join(dirname(__file__), 'version.txt')
bpath = join(dirname(__file__), 'build.txt')

try:
	import os
	build = int(os.environ['BUILD_NUMBER'])
	with open(bpath, 'w') as f:
		f.write(build)
except:
	build = int(open(bpath).read())

release = open(vpath).read()
