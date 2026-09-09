#!/usr/bin/python3

import sys
import os
import shutil
import magic
import tempfile
import json
import subprocess
import grp,pwd
import airmanager.airmanager as installer

dbg=True
retCode=0

def _debug(msg):
	if dbg:
		print("Air installer: %s"%msg)
#def _debug

def _generate_install_dir():
	global retCode
	installDir=''
	try:
		installDir=tempfile.mkdtemp()
	except:
		_debug("Couldn't create temp dir")
		retCode=1
	os.chown(installDir,os.geteuid(),os.getgid())
	_debug("Install dir: %s"%installDir)
	return (installDir)
#def _generate_install_dir

def _get_air_info(air):
	global retCode
	airInfo={}
	airInfo=installer.AirManager().get_air_info(air)
	return (airInfo)
#def _get_deb_info

def _begin_install_package(air):
	global retCode
	mime=magic.Magic(mime=True)
	if ((os.path.isfile(air))):# and (mime.from_file(air)=='application/x-air-installer')):
		_generate_epi_file(air)
	else:
		_debug("%s is an invalid file %s"%(air,mime.from_file(air)))
		retCode=1
#def _begin_install_package

def _generate_epi_json(airInfo,air):
	global retCode
	tmpDir=os.path.dirname(air)
	airName=os.path.basename(air)
	epiJson=''
	#retCode controls the return code of the previous operations 
	if not retCode:
		_debug("Generating json at %s"%tmpDir)
		epiJson="%s/%s.epi"%(tmpDir,airInfo['name'].replace(" ","_"))
		epiFile={}
		epiFile["type"]="file"
		epiFile["pkg_list"]=[{"name":airInfo['name'],'url_download':tmpDir,'version':{'all':airName}}]
		epiFile["script"]={"name":"%s/install_script.sh"%tmpDir,'remove':True,'download':True}
		epiFile["required_root"]=False
		epiFile["required_dconf"]=True
		try:
			with open(epiJson,'w') as f:
				json.dump(epiFile,f,indent=4)
			_debug("OK")
		except Exception as e:
			_debug("Error %s"%e)
			retCode=1
	return(epiJson)
#def _generate_epi_json

def _generate_epi_script(airInfo,air):
	global retCode
	tmpDir=os.path.dirname(air)
	try:
		#Copy the icon to temp folder
		with open("%s/install_script.sh"%tmpDir,'w') as f:
			f.write("#!/bin/bash\n")
			f.write("DESTDOWNLOAD=\"/var/cache/epi-downloads\"\n")
			f.write("ACTION=\"$1\"\n")
			f.write("case $ACTION in\n")
			f.write("\tremove)\n")
			f.write("\t\tapt-get remove -y %s\n"%airInfo['name'])
			f.write("\t\tTEST=$( dpkg-query -s  %s 2> /dev/null| grep Status | cut -d \" \" -f 4 )\n"%airInfo['name'])
			f.write("\t\tif [ \"$TEST\" == 'installed' ];then\n")
			f.write("\t\t\texit 1\n")
			f.write("\t\tfi\n")
			f.write("\t\t;;\n")
			f.write("\ttestInstall)\n")
			f.write("\t\techo ""\n")
			f.write("\t\t;;\n")
			f.write("\tdownload)\n")
			f.write("\t\ttouch /tmp/abc\n")
			f.write("\t\t;;\n")
			f.write("\tinstallPackage)\n")
			f.write("\t\techo %s\n"%air)
			f.write("\t\tpkexec /usr/bin/air-helper-installer.py install %s\n"%(air))
			f.write("\t\techo \"$?\"\n")
			f.write("\t\t;;\n")
			f.write("\tgetInfo)\n")
			f.write("\t\techo \"%s\"\n"%airInfo.get('description',''))
			f.write("\t\t;;\n")
			f.write("esac\n")
			f.write("exit 0\n")
	except Exception as e:
		_debug("%s"%e)
		retCode=1
	os.chmod("%s/install_script.sh"%tmpDir,0o755)
#def _generate_epi_script

def _generate_epi_file(air):
	global retCode
	installDir=_generate_install_dir()
	if installDir:
		#copy air to installDir
		try:
			airName=os.path.basename(air)
			shutil.copyfile(air,"%s/%s"%(installDir,airName))
			air="%s/%s"%(installDir,airName)
			_debug("%s copied to %s"%(air,installDir))
		except Exception as e:
			_debug("%s couldn't be copied to %s: %s"%(air,installDir,e))
			retCode=1
		
		if not retCode:
			airInfo=_get_air_info(air)
			epiJson=_generate_epi_json(airInfo,air)
			_generate_epi_script(airInfo,air)
			if not retCode:
				_debug("Launching %s"%epiJson)
				subprocess.check_call(['/usr/bin/xhost','+'])
				subprocess.run(['epi-gtk',epiJson])
				subprocess.check_call(['/usr/bin/xhost','-'])
				subprocess.check_output(["xdg-mime","install","/usr/share/mime/packages/x-air-installer.xml"])
				subprocess.check_output(["xdg-mime","default","/usr/share/applications/air-installer.desktop","/usr/share/mime/packages/x-air-installer.xml"],input=b"")
			else:
				subprocess.run(['epi-gtk',"--error"])
		else:
			subprocess.run(['epi-gtk',"--error"])
	elif retCode:
		subprocess.run(['epi-gtk',"--error"])
installFile=sys.argv[1]
_begin_install_package(installFile)

