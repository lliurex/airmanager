#!/usr/bin/env python3
import  airmanager.airmanager as installer
import sys
import subprocess
import tempfile
import os

installer=installer.AirManager()
err=0
dbg=True

def _debug(msg):
	if dbg:
		print("Helper: %s"%msg)
#def _debug

if sys.argv[1]=='install':
	airFile=sys.argv[2]
	if (len(sys.argv))==4:
		iconFile=sys.argv[3]
	else:
		air_info=installer.get_air_info(airFile)
		if 'pb' in air_info.keys():
			if air_info['pb']:
				iconFile=tempfile.mkstemp()[1]
				iconFileTmp=air_info['pb']
				iconFileTmp.savev(iconFile,'png',[""],[""])

	_debug("Installing %s %s"%(airFile,iconFile))
	err=installer.install(airFile,iconFile)
	try:
		subprocess.check_call(['gtk-update-icon-cache','/usr/share/icons/hicolor/'])
	except:
		err=1
	if os.path.isfile(iconFile):
		try:
			os.remove(iconFile)
		except:
			_debug("%s not found for remove")
elif sys.argv[1]=='remove':
	airFile=sys.argv[2]
	air_pkg={}
	if (len(sys.argv))==4:
		deskFile=sys.argv[3]
		air_pkg={'desktop':deskFile,'air_id':airFile}
	else:
		for app,data in installer.get_installed_apps().items():
			if airFile.replace(".air","")==app:
				air_pkg=data
			break
	if air_pkg:
		_debug("Removing %s %s"%(air_pkg['air_id'],air_pkg['desktop']))
		err=installer.remove_air_app(air_pkg)
		try:
			subprocess.check_call(['gtk-update-icon-cache','/usr/share/icons/hicolor/'])
		except:
			err=1
	else:
		err=1

exit(err)

