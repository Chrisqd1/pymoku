import subprocess, os, os.path, sys

from setuptools import setup, Extension
from setuptools.command.install import install
from setuptools.command.develop import develop

from pkg_resources import resource_filename, resource_isdir
from tempfile import mkstemp
from zipfile import ZipFile

import requests

version = open('pymoku/version.txt').read().strip()
data_url = 'http://www.liquidinstruments.com/s/data-latest.zip'

try:
	sys.argv.remove("--no-fetch-data")
	fetch_bs = False
except:
	fetch_bs = True


def download_bitstreams():
	assert resource_isdir('pymoku', 'instr')
	base_path = resource_filename('pymoku', 'instr')

	data = mkstemp()

	try:
		r = requests.get(data_url)
		os.write(data[0], r.content)
		ZipFile(data[1]).extractall(base_path)

		os.close(data[0])
		os.remove(data[1])
	except:
		print("Failed to fetch updated instrument data, please re-run install with internet access or specify '--no-fetch-data' to disable this message.")
		raise


class InstallWithBitstreams(install):
	def run(self):
		install.run(self)
		if fetch_bs:
			download_bitstreams()

class DevelopWithBitstreams(develop):
	def run(self):
		develop.run(self)
		if fetch_bs:
			download_bitstreams()



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
		'pymoku' : ['version.txt', '*.capnp', 'instr/']
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

	cmdclass={
		'install': InstallWithBitstreams,
		'develop': DevelopWithBitstreams,
	},

	zip_safe=False, # Due to bitstream download
)
