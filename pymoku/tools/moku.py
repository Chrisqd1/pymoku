#!/usr/bin/env python

from argparse import ArgumentParser
import os, os.path, shutil, tempfile, tarfile
import requests, pkg_resources

from pymoku import *
from pymoku.version import compat_fw
from pymoku.tools.compat import *

import logging
logging.basicConfig(format='%(message)s', level=logging.INFO)

data_path = os.path.expanduser(os.environ.get('PYMOKU_INSTR_PATH', None) or pkg_resources.resource_filename('pymoku', 'data'))
version = pkg_resources.get_distribution("pymoku").version
DATAURL = 'http://updates.liquidinstruments.com/static/mokudata-%d.tar.gz' % compat_fw[0]

parser = ArgumentParser()
subparsers = parser.add_subparsers(title="action", dest='action', description="Action to take")
subparsers.required = True

# Global arguments
parser.add_argument('--serial', default=None, help="Serial Number of the Moku to connect to")
parser.add_argument('--name', default=None, help="Name of the Moku to connect to")
parser.add_argument('--ip', default=None, help="IP Address of the Moku to connect to")

# View and load new instrument bitstreams
def fetchdata(args):
	url = args.url
	logging.info("Fetching data pack from: %s" % url)
	r = requests.get(url)
	with open(data_path + '/mokudata.tar.gz', 'wb') as f:
		f.write(r.content)
	try:
		logging.info("installing to %s" % data_path)
		tarfile.open(data_path + '/mokudata.tar.gz').extractall(path=data_path)
		with open(data_path + '/data_version', 'w') as f:
			f.write(version)
	except:
		logging.exception("Couldn't install data pack")
	os.remove(data_path + '/mokudata.tar.gz')

parser_fetchdata = subparsers.add_parser('fetchdata', help="Check and update instruments on the Moku.")
parser_fetchdata.add_argument('--url', help='Override location of data pack', default=DATAURL)
parser_fetchdata.set_defaults(func=fetchdata)

# View and load new instrument bitstreams
def instrument(args):
	moku = None
	try:
		moku = connect(args, force=True)
		if args.action == 'load':
			if not len(args.files):
				print("No instrument files specified for loading")
				return

			for file in args.files:
				fname = os.path.basename(file)
				chk = moku._load_bitstream(file)
				print("Successfully loaded new instrument {} version {}".format(fname, chk))
		else:
			exit(1)
	finally:
		if moku:
			moku.close()

parser_instruments = subparsers.add_parser('instrument', help="Check and update instruments on the Moku.")
parser_instruments.add_argument('action', help='Action to take', choices=['load'])
parser_instruments.add_argument('files', nargs='*', default=None, help="Path to local instrument file(s), if any")
parser_instruments.set_defaults(func=instrument)

# View and load new packages
def package(args):
	moku = None
	try:
		moku = connect(args)
		if args.action == 'load':
			if not args.file or not args.file.endswith('hgp'):
				print('Package load requires an HGP file to be specified')
				return

			fname = os.path.basename(args.file)
			moku._send_file('f', args.file)

			if os.path.exists(args.file + '.sha256'):
				moku._send_file('f', args.file + '.sha256')
			else:
				print("WARNING: No signing information found, this package might not run correctly on your Moku.")

			print("Successfully loaded new package {}".format(fname))
		else:
			exit(1)
	finally:
		if moku:
			moku.close()

parser_package = subparsers.add_parser('package', help="Check and load special feature packages on the Moku.")
parser_package.add_argument('action', help='Action to perform', choices=['load'])
parser_package.add_argument('file', nargs='?', default=None, help="Path to local package file, if any")
parser_package.set_defaults(func=package)


# View firmware version and load new versions.
def firmware(args):
	moku = None

	try:
		moku = connect(args, force=True)
		if args.action == 'version':
			print("Moku Firmware Version {}".format(moku.get_firmware_build()))
		elif args.action == 'load':
			if not args.file or not args.file.endswith('fw'):
				print('Package load requires an FW file to be specified')
				return
			moku._load_firmware(args.file)
			print("Successfully started firmware update. Your Moku will shut down automatically when complete.")
		elif args.action == 'check_compat':
			build = moku.get_firmware_build()
			compat = firmware_is_compatible(build)

			if compat is None:
				print("Unable to determine compatibility, perhaps you're running a development or pre-release build?")
			else:
				print("Compatible" if compat else "Firmware version %s incompatible with Pymoku v%s, please update firmware to one of versions: %s." % (moku.get_firmware_build(), str(moku.get_version()), list_compatible_firmware()))
		else:
			exit(1)
	finally:
		try:
			moku.close()
		except zmq.error.Again:
			pass # Firmware update can stop us being able to close

parser_firmware = subparsers.add_parser('firmware', help="Check and load new firmware for your Moku.")
parser_firmware.add_argument('action', help='Action to perform', choices=['version', 'load', 'check_compat'])
parser_firmware.add_argument('file', nargs='?', default=None, help="Path to local firmware file, if any")
parser_firmware.set_defaults(func=firmware)

def main():
	logging.info("PyMoku %s" % version)
	args = parser.parse_args()
	args.func(args)

def connect(args, force=False):
	if len([ x for x in (args.serial, args.name, args.ip) if x]) != 1:
		print("Please specify exactly one of serial, name or IP address of target Moku")
		exit(1)

	force = force or args.force
	if args.serial:
		moku = Moku.get_by_serial(args.serial, force=force)
		print(moku.get_name())
	elif args.name:
		moku = Moku.get_by_name(args.name, force=force)
	else:
		moku = Moku(args.ip, force=force)

	return moku


# Compatible with direct run and distutils binary packaging
if __name__ == '__main__':
	main()
