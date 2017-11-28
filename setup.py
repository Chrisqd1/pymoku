import subprocess, os, os.path, sys

from setuptools import setup, Extension

from Cython.Build import cythonize

from pkg_resources import resource_filename, resource_isdir
from tempfile import mkstemp
from zipfile import ZipFile
from glob import glob

version = open('pymoku/version.txt').read().strip()

# I thought this fixed a bug on Windows but I'm now not convinved, should
# check that this is required (rather than just using '/' as path sep.)
j = os.path.join

lr_ext = Extension(
	'lr',
	include_dirs=['liquidreader'],
	sources=[
		j('liquidreader','bitcpy.c'),
		j('liquidreader','lireader.c'),
		j('liquidreader','liparse.c'),
		j('liquidreader','liutility.c'),
		j('liquidreader','linumber.c'),
		j('liquidreader','capn.c'),
		j('liquidreader','capn-malloc.c'),
		j('liquidreader','capn-stream.c'),
		j('liquidreader','li.capnp.c'),
		j('lr_mod','lr_module.c'),
	],

	extra_compile_args=['-std=c99'],
)

# The canonical way to do this is to put this instruction in the extensions list below,
# but it only returns distutils.Extension, not setuptools.Extension, so we have to craft
# those objects ourselves below. TODO: Move to a build extension so it doesn't happen with
# every invocation
cythonize('pymoku/*.pyx')

setup(
	name='pymoku',
	version=version,
	author='Ben Nizette',
	author_email='ben.nizette@liquidinstruments.com',
	packages=['pymoku', 'pymoku.tools'],
	package_dir={'pymoku': 'pymoku'},
	package_data={
		'pymoku' : ['version.txt', '*.capnp', j('data', '*')]
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
		Extension('pymoku._bodeanalyzer_data', ['pymoku/_bodeanalyzer_data.c']),
		Extension('pymoku._oscilloscope_data', ['pymoku/_oscilloscope_data.c']),
		Extension('pymoku._specan_data', ['pymoku/_specan_data.c']),
	],

	zip_safe=False, # Due to bitstream download
)
