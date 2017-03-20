from distutils.core import setup
import subprocess, os

from pymoku import version

setup(
	name='pymoku',
	version=version.release,
	author='Ben Nizette',
	author_email='ben.nizette@liquidinstruments.com',
	packages=['pymoku', 'pymoku.schema'],
	package_dir={'pymoku.schema': 'pymoku/schema'},
	package_data={'pymoku.schema': ['*.capnp']},
	license='MIT',
	long_description=open('README.md').read(),

	url="https://github.com/liquidinstruments/pymoku",
	download_url="https://github.com/liquidinstruments/pymoku/archive/%s.tar.gz" % version.release,

	keywords=['moku', 'liquid instruments', 'test', 'measurement', 'lab', 'equipment'],

	entry_points={
		'console_scripts' : [
			'moku=pymoku.tools.moku:main',
			'moku_convert=pymoku.tools.moku_convert:main',
		]
	}
)
