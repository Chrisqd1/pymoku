from setuptools import setup, Extension
import subprocess, os

version = open('pymoku/version.txt').read().strip()

lr_ext = Extension(
	'lr',
	include_dirs=['liquidreader'],
	sources=[
		'liquidreader/lireader.c',
		'liquidreader/liparse.c',
		'liquidreader/liutility.c',
		'liquidreader/linumber.c',
		'liquidreader/capn.c',
		'liquidreader/capn-malloc.c',
		'liquidreader/capn-stream.c',
		'liquidreader/li.capnp.c',
		'lr_mod/lr_module.c',
	],
	extra_compile_args=['-std=c99'],
)

setup(
	name='pymoku',
	version=version,
	author='Ben Nizette',
	author_email='ben.nizette@liquidinstruments.com',
	packages=['pymoku', 'pymoku.tools'],
	package_dir={'pymoku': 'pymoku'},
	package_data={
		'pymoku' : ['version.txt', '*.capnp']
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
		'decorator',
	],

	ext_modules=[
		lr_ext,
	],

	zip_safe=False, # This isn't strictly true, but makes debugging easier on the device
)
