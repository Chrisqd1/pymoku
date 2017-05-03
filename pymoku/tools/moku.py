#!/usr/bin/env python

from argparse import ArgumentParser
import os, os.path, shutil, tempfile
import requests

from pymoku import *
from pymoku.tools.compat import *

import logging
logging.basicConfig(level=logging.WARNING)

parser = ArgumentParser()
subparsers = parser.add_subparsers(title="action", description="Action to take")

# Global arguments
parser.add_argument('--serial', default=None, help="Serial Number of the Moku to connect to")
parser.add_argument('--name', default=None, help="Name of the Moku to connect to")
parser.add_argument('--ip', default=None, help="IP Address of the Moku to connect to")

parser.add_argument('--server', help='Override update server', default='http://updates.liquidinstruments.com:8000')
parser.add_argument('--username', help='Update Server username, if any', default=None)
parser.add_argument('--password', help='Update Server password, if any', default=None)

def _download_request(url, local_dir, local_fname=None, **params):
	import rfc6266, posixpath
	request = requests.get(url, stream=True, params=params)

	fname = local_fname or rfc6266.parse_requests_response(request).filename_unsafe
	if fname is None:
		raise Exception("Unknown download name")

	# Don't use the rfc6566 filename_sanitized as that requires that we know the extension
	# up front (and this function is generic enough not to know that). The following sanitation
	# is ^C^V'd from that function, without the extension check.
	fname = posixpath.basename(fname)
	fname = os.path.basename(fname)
	fname = fname.lstrip('.')

	if not fname:
		raise Exception("Invalid download name")

	fname = os.path.join(local_dir, fname)

	with open(fname, 'wb') as f:
		for chunk in request.iter_content(chunk_size=1024):
			if chunk:
				f.write(chunk)

	return fname


# View and load new instrument bitstreams
def instrument(moku, args):
	if args.action == 'list':
		instrs = moku._list_bitstreams(include_version=True)

		if len(instrs):
			print("The following instruments are available on your Moku:")
			for i in instrs:
				print('\t{}-{}'.format(i[0], i[1][:8]))
		else:
			print("No instruments found on your Moku.")
	elif args.action == 'load':
		if not args.file or not args.file.endswith('bit'):
			print('Package load requires a BIT file to be specified')
			return

		fname = os.path.basename(args.file)
		chk = moku._load_bitstream(args.file)
		print("Successfully loaded new instrument {} version {:X}".format(fname, chk))
	elif args.action == 'check_compat':
		instrs = moku._list_bitstreams(include_version=True)
		compat_configs = compatible_configurations(args.server, args.username, args.password)
		compat_hashes = [ c['bitstream']['hash'] for c in compat_configs.values() ]

		for i, v in instrs:
			print("\t{:<20}{}".format(i, "COMPATIBLE" if v in compat_hashes else "INCOMPATIBLE"))
	elif args.action == 'update':
		compat_configs = compatible_configurations(args.server, args.username, args.password)
		types = set(( c['bitstream']['type'] for c in compat_configs.values()))
		tmpdir = tempfile.mkdtemp()

		for t in types:
			newest = max((c['bitstream'] for c in compat_configs.values() if c['bitstream']['type'] == t), key=lambda b: b['build_id'])
			fpath = _download_request(args.server + '/versions/artefact/' + newest['hash'], tmpdir)
			fname = os.path.basename(fpath)
			moku._load_bitstream(fpath)

			print("Loaded {:s}".format(fname.split('_')[0]))

		shutil.rmtree(tmpdir)


	else:
		exit(1)

parser_instruments = subparsers.add_parser('instrument', help="Check and update instruments on the Moku.")
parser_instruments.add_argument('action', help='Action to take', choices=['list', 'load', 'check_compat', 'update'])
parser_instruments.add_argument('file', nargs='?', default=None, help="Path to local instrument file, if any")
parser_instruments.set_defaults(func=instrument)


# View and load new packages
def package(moku, args):
	if args.action == 'list':
		packs = moku._list_package(include_version=True)

		if len(packs):
			print("The following packages are available on your Moku:")
			for i in packs:
				print('\t{}'.format(i))
		else:
			print("No packages found on your Moku.")
	elif args.action == 'load':
		if not args.file or not args.file.endswith('hgp'):
			print('Package load requires an HGP file to be specified')
			return

		fname = os.path.basename(args.file)
		chk = moku._load_persistent(args.file)

		if os.path.exists(args.file + '.sha256'):
			moku._load_persistent(args.file + '.sha256')
		else:
			print("WARNING: No signing information found, this package might not run correctly on your Moku.")

		print("Successfully loaded new instrument {} version {:X}".format(fname, chk))
	else:
		exit(1)

parser_package = subparsers.add_parser('package', help="Check and update special feature packages on the Moku.")
parser_package.add_argument('action', help='Action to perform', choices=['list', 'load'])
parser_package.add_argument('file', nargs='?', default=None, help="Path to local package file, if any")
parser_package.set_defaults(func=package)


# View firmware version and load new versions.
def firmware(moku, args):
	if args.action == 'list':
		print("Moku Firmware Version {}".format(moku.get_version()))
	elif args.action == 'load':
		if not args.file or not args.file.endswith('fw'):
			print('Package load requires an FW file to be specified')
			return

		moku._load_firmware(args.file)
		print("Successfully started firmware update. Your Moku will shut down automatically when complete.")
	elif args.action == 'update':
		build = moku.get_version()
		compat_configs = compatible_configurations(args.server, args.username, args.password)
		fws = [ c['firmware'] for c in compat_configs.values() ]
		newest = max(fws, key=lambda f: int(f['build_id']))

		if int(newest['build_id']) > build:
			print("New Firmware available, build {build_id:d}.".format(**newest))
		else:
			print("No new Firmware available, {build_id:d} on the server and {build:d} on the device.".format(build=build, **newest))
			return

		print("Downloading...")
		tempdir = tempfile.mkdtemp()
		fpath = _download_request(args.server + '/versions/artefact/' + newest['hash'], tempdir)
		fname = os.path.basename(fpath)
		print("Installing...")
		moku._load_firmware(fpath)
		print("Your Moku will shut down automatically when complete.")

		shutil.rmtree(tempdir)
	elif args.action == 'check_compat':
		build = moku.get_version()

		compat = firmware_is_compatible(build, args.server, args.username, args.password)

		if compat is None:
			print("Unable to determine compatibility, perhaps you're running a development or pre-release build?")
		else:
			print("Compatible" if compat else "Incompatible, please run 'moku update' and 'moku firmware update' to get the latest firmware and libraries.")
	else:
		exit(1)

parser_firmware = subparsers.add_parser('firmware', help="Check and update new firmware for your Moku.")
parser_firmware.add_argument('action', help='Action to perform', choices=['version', 'load', 'update', 'check_compat'])
parser_firmware.add_argument('file', nargs='?', default=None, help="Path to local firmware file, if any")
parser_firmware.set_defaults(func=firmware)


def main():
	args = parser.parse_args()

	if len([ x for x in (args.serial, args.name, args.ip) if x]) != 1:
		print("Please specify exactly one of serial, name or IP address of target Moku")
		exit(1)

	if args.serial:
		moku = Moku.get_by_serial(args.serial)
	elif args.name:
		moku = Moku.get_by_name(args.name)
	else:
		moku = Moku(args.ip)

	try:
		args.func(moku, args)
	finally:
		moku.close()

# Compatible with direct run and distutils binary packaging
if __name__ == '__main__':
	main()
