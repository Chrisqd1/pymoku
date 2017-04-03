from setuptools import setup
import subprocess, os

version = open('pymoku/version.txt').read()

setup(
	name='pymoku',
	version=version,
	author='Ben Nizette',
	author_email='ben.nizette@liquidinstruments.com',
	packages=['pymoku', 'pymoku.schema'],
	package_dir={'pymoku.schema': 'pymoku/schema'},
	package_data={
		'pymoku' : ['version.txt'],
		'pymoku.schema': ['*.capnp']
	},
	license='MIT',
	long_description="Python scripting interface to the Liquid Instruments Moku:Lab",

	url="https://github.com/liquidinstruments/pymoku",
	download_url="https://github.com/liquidinstruments/pymoku/archive/%s.tar.gz" % version,

	keywords=['moku', 'liquid instruments', 'test', 'measurement', 'lab', 'equipment'],

	entry_points={
		'console_scripts' : [
			'moku=pymoku.tools.moku:main',
			'moku_convert=pymoku.tools.moku_convert:main',
		]
	},

	install_requires=[
		'future',
		'pyzmq>=15.3.0',
		'six',
		'urllib3',
		'pyzmq',
		'rfc6266',
		'requests',
		'pycapnp',
	],
	zip_safe=False,
)
