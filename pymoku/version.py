
try:
	import os
	build = int(os.environ['BUILD_NUMBER'])
except:
	build = 65535

release =  "0.1"
