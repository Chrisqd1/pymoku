#!/usr/bin/env python

from argparse import ArgumentParser
import os, os.path, shutil, tempfile
import requests

from pymoku import *
import pymoku.version

parser = ArgumentParser()
subparsers = parser.add_subparsers()

# Global arguments
parser.add_argument('--serial', default=None, help="Serial Number of the Moku to connect to")
parser.add_argument('--name', default=None, help="Name of the Moku to connect to")
parser.add_argument('--ip', default=None, help="IP Address of the Moku to connect to")

parser.add_argument('--server', help='Override update server', default='http://updates.liquidinstruments.com:8000')
parser.add_argument('--username', help='Update Server username, if any', default=None)
parser.add_argument('--password', help='Update Server password, if any', default=None)


def _hgdep_pm_updates(server, username, password):
	params = { 'build_id__gte' : pymoku.version.build }
	r = requests.get(server + '/versions/update/pymoku/', params=params, auth=(username, password))
	return r.json()

def _hgdep_compat_configs(server, username, password):
	params = { 'build_id' : pymoku.version.build }
	r = requests.get(server + '/versions/compat/pymoku/', params=params, auth=(username, password))
	return r.json()

def _download_request(url, local_dir, local_fname=None, **params):
	import rfc6266
	request = requests.get(url, params=params)

	fname = local_fname or rfc6266.parse_requests_response(request).filename_sanitized
	fname = os.path.join(local_dir, fname)

	with open(fname, 'wb') as f:
		for chunk in request.iter_content(chunk=1024):
			if chunk:
				f.write(chunk)

	return fname


# View and download updates from a remote server
def update(moku, args):
	d = _hgdep_pm_updates(args.server, args.username, args.password)
	if not len(d):
		print("No Pymoku updates available")
	else:
		build, date = max([(d['build_id'], d['release']) for d in builds.items()])
		print("Pymoku can be updated from {} to {}, released on {}. Please refer to the Pymoku documentation for installation procedures.".format(versions.build_id, build, date))

parser_updates = subparsers.add_parser('update')
parser_updates.set_defaults(func=update)


# View and load new instrument bitstreams
def instrument(moku, args):
	if args.action == 'list':
		instrs = moku.list_bitstreams(include_version=True)

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
		chk = moku.load_bitstream(args.file)
		print("Successfully loaded new instrument {} version {:X}".format(fname, chk))
	elif args.action == 'check_compat':
		instrs = moku.list_bitstreams(include_version=True)
		compat_configs = _hgdep_compat_configs(args.server, args.username, args.password)
		compat_hashes = [ c['bitstream']['hash'] for c in compat_configs.values() ]

		for i, v in instrs:
			print("\t{}: {}".format(i, "COMPATIBLE" if v in compat_hashes else "INCOMPATIBLE"))
	elif args.action == 'update':
		compat_configs = _hgdep_compat_configs(args.server, args.username, args.password)
		types = set(( c['bitstream']['type'] for c in compat_configs.values()))
		tmpdir = tempfile.mkdtemp()

		for t in types:
			newest = max((c['bitstream'] for c in compat_configs if c['bitstream']['type'] == t), key=lambda b: b['build_id'])
			fpath = _download_request(server + '/versions/artefact/' + newest['hash'])
			fname = os.path.basename(fpath)
			moku.load_bitstream(fpath)

			print("Loaded {:s}-t{:s}".format(fname, newest['hash'][:8]))

		shutil.rmtree(tmpdir)


	else:
		exit(1)

parser_instruments = subparsers.add_parser('instrument')
parser_instruments.add_argument('action', help='list load')
parser_instruments.add_argument('file', nargs='?', default=None)
parser_instruments.set_defaults(func=instrument)


# View and load new packages
def package(moku, args):
	if args.action == 'list':
		packs = moku.list_package(include_version=True)

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
		chk = moku.load_persistent(args.file)

		if os.path.exists(args.file + '.sha256'):
			moku.load_persistent(args.file + '.sha256')
		else:
			print("WARNING: No signing information found, this package might not run correctly on your Moku.")

		print("Successfully loaded new instrument {} version {:X}".format(fname, chk))
	else:
		exit(1)

parser_package = subparsers.add_parser('package')
parser_package.add_argument('action', help='list load')
parser_package.add_argument('file', nargs='?', default=None)
parser_package.set_defaults(func=package)


# View firmware version and load new versions.
def firmware(moku, args):
	if args.action == 'list':
		print("Moku Firmware Version {}".format(moku.get_version()))
	elif args.action == 'load':
		if not args.file or not args.file.endswith('fw'):
			print('Package load requires an FW file to be specified')
			return

		moku.load_firmware(args.file)
		print("Successfully started firmware update. Your Moku will shut down automatically when complete.")
	else:
		exit(1)

parser_firmware = subparsers.add_parser('firmware')
parser_firmware.add_argument('action', help='version load')
parser_firmware.add_argument('file', nargs='?', default=None)
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
