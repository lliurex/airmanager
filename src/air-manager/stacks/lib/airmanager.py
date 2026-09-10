#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import stat
import time
import subprocess
import shutil
import tempfile
import zipfile
import glob
import json
import re
import urllib.request as url

LOG='/tmp/air_manager.log'

class AirManager():
	def __init__(self):
		self.dbg=True
		self.defaultIcon="/usr/share/air-installer/rsrc/air-installer_icon.png"
		self.adobeAirInstallFolder="/opt/AdobeAirApp/"
		self.adobeAirSdkFolder="/opt/adobe-air-sdk/"
		self.airPkgname="adobeair"
		self.confDir="/usr/share/air-manager/config.d"
		self.rebuild=False
		self.pkgConfig={}
	#def __init__

	def _debug(self,msg):
		if self.dbg:
			print("airinstaller: %s"%msg)
			self._log(msg)
	#def _debug

	def _log(self,msg):
		try:
			with open(LOG,'a'):
				f.write("%s"%msg)
		except:
			LOG='/tmp/air_manager.log.1'
			try:
				with open(LOG,'a'):
					f.write("%s"%msg)
			except:
				print("Can't write log")
	#def _log

	def set_defaultIcon(self,icon):
		self.defaultIcon=icon
	#def set_defaultIcon

	def install(self,airInfo):
		sw_err=0
		self.rebuild=False
		sdkInstalled=False
		self._checkAdobeAir()
		airFile=airInfo["file"]
		self._debug("Validating {}".format(airFile))
		icon=airInfo.get("icon",self.defaultIcon)
		if self._checkIsValid(airFile):
			self._debug("Installing {}".format(airFile))
			config=self._checkConfigFile(airFile)
			if 'preinstall' in config.keys():
				airFile=self._recompileForPreinstall(airFile,config['preinstall'])
			err=self._installAirApp(airFile)
			if err and not self.rebuild:
				self._debug("Fixing certificate...")
				airFile=self._recompileForCertIssue(airFile)
				err=self._installAirApp(airFile)
			if err:
				self._debug("Failed to install code: {}".format(err))
				self._debug("Going with sdk installation")
				sw_err=self._installAirSDK(airFile,icon)
				sdkInstalled=True
	#def install

	def install2(self,airFile,icon=None):
		sw_err=0
		self.rebuild=False
		sdkInstalled=False
		self._checkAdobeAir()
		if not icon:
			icon=self.defaultIcon
		self._debug("Procced with file: %s"%airFile)
		file_name=os.path.basename(airFile)
		if self._checkIsValid(airFile):
			basedir_name=file_name.replace(".air","")
			self._debug("Installing %s"%airFile)
			config=self._checkConfigFile(airFile)
			if 'preinstall' in config.keys():
				airFile=self._recompileForPreinstall(airFile,config['preinstall'])
			sw_err=self._installAirApp(airFile)
			if sw_err and not self.rebuild:
				self._debug("Trying rebuild...")
				modified_airFile=self._recompileForCertIssue(airFile)
				self._debug("Installing %s"%modified_airFile)
				sw_err=self._installAirApp(modified_airFile)
			if sw_err:
				self._debug("Failed to install code: %s"%sw_err)
				self._debug("Going with sdk installation")
				sw_err=self._installAirSDK(airFile,icon)
				sdkInstalled=True

			sw_desktop=True
			if 'generate-desktop' in config.keys():
				sw_desktop=config['generate-desktop']

			if not sw_err and sdkInstalled:
				#Copy icon to hicolor
				if sw_desktop:
					sw_installed=self._generate_desktop(file_name)
					if sw_installed:
						hicolor_icon='/usr/share/icons/hicolor/48x48/apps/%s.png'%basedir_name
						shutil.copyfile (icon,hicolor_icon)
						self._debug("Installed in %s"%(basedir_name))
					else:
						self._debug("%s Not Installed!!!"%(basedir_name))
#			elif not sw_err and icon!=self.defaultIcon:
			elif not sw_err and sw_desktop:
				#Modify desktop with icon
				hicolor_icon='/usr/share/icons/hicolor/48x48/apps/%s.png'%basedir_name
				shutil.copyfile (icon,hicolor_icon)
				icon_new=os.path.basename(hicolor_icon)
				self._modify_desktop(airFile,icon_name=icon_new)
		
			if 'postinst' in config.keys() and not sw_err:
				self._execute_postinstall(config['postinst'])

		#Remove adobeair mime association
		time.sleep(1)
		my_env=os.environ.copy()
		my_env["DISPLAY"]=":0"
		a=subprocess.check_output(["xdg-mime","install","--mode","system","/usr/share/mime/packages/x-air-installer.xml"],env=my_env)
		self._debug("Remove result: %s"%a)
		if os.path.isfile('/usr/share/mime/application/vnd.adobe.air-application-installer-package+zip.xml'):
			self._debug("Remove air mime")
			os.remove('/usr/share/mime/application/vnd.adobe.air-application-installer-package+zip.xml')
		self._debug("Fixing mime")
		a=subprocess.check_output(["xdg-mime","default","/usr/share/applications/air-installer.desktop","/usr/share/mime/packages/x-air-installer.xml"],input=b"",env=my_env)
		self._debug("Default result: %s"%a)
	#def install

	def _checkConfigFile(self,airFile):
		pkgConfig={}
		airName=os.path.basename(airFile).replace(".air","")
		self._debug("Name: %s"%airName)
		if os.path.isdir(self.confDir):
			for conf in glob.glob("%s/*"%self.confDir):
				if os.path.basename(conf).replace(".json","").lower() in airName.lower():
					self._debug("Conf file: %s"%conf)
					try:
						with open(conf,'r') as f:
							pkgConfig=json.load(f)
					except Exception as e:
						self._debug("Error reading %s"%conf)
						self._debug("Reason: %s"%e)
		return(pkgConfig)

	def _recompileForPreinstall(self,airFile,conf):
		self._debug("Modifying package %s"%airFile)
		sw_ok=True
		newAir=airFile
		tmpdir=self._unzipAir(airFile)
		cwd=os.getcwd()
		os.chdir(tmpdir)
		for targetFile,values in conf.items():
			self._debug("Searching for %s"%targetFile)
			if os.path.isfile(targetFile):
				self._debug("File: %s"%targetFile)
				f=open(targetFile,'r')
				fcontents=f.readlines()
				f.close()
				newContents=[]
				for line in fcontents:
					for regTarget,regReplace in values.items():
						if re.search(regTarget,line):
							line=re.sub(regTarget,regReplace,line)
						newContents.append(line)
				f=open(targetFile,'w')
				f.writelines(newContents)
				f.close()

		for xml_file in os.listdir("META-INF/AIR"):
			if xml_file.endswith(".xml"):
				air_xml=xml_file
				break
		if air_xml:
			shutil.move("META-INF/AIR/"+air_xml,air_xml)
			shutil.rmtree("META-INF/",ignore_errors=True)
			os.remove("mimetype")
			self._debug("Generating new cert")
			subprocess.call(["/opt/adobe-air-sdk/bin/adt","-certificate","-cn","lliurex","2048-RSA","lliurex.p12","lliurex"])
			newAir=os.path.basename(airFile)
			my_env=os.environ.copy()
			my_env["DISPLAY"]=":0"
			try:
				subprocess.check_output(["/opt/adobe-air-sdk/bin/adt","-package","-tsa","none","-storetype","pkcs12","-keystore","lliurex.p12",newAir,air_xml,"."],input=b"lliurex",env=my_env)
				newAir="%s/%s"%(tmpdir,newAir)
			except Exception as e:
				self._debug(e)
		os.chdir(cwd)
		self.rebuild=True
		return (newAir)
	#def _recompileForCertIssue

	def _execute_postinstall(self,conf):
		self._debug("Postinstall %s"%conf)
		sw_ok=True
		for targetFile,values in conf.items():
			self._debug("Searching for %s"%targetFile)
			if os.path.isfile(targetFile):
				self._debug("File: %s"%targetFile)
				with open(targetFile,'r') as f:
					fcontents=f.readlines()
				newContents=[]
				for line in fcontents:
					deleteKey=""
					for regTarget,regReplace in values.items():
						if regTarget=='--append':
							newContents.extend(regReplace)
							deleteKey=regTarget
						else:
							line=re.sub(regTarget,regReplace,line)
						newContents.append(line)
					if deleteKey:
						values.pop(deleteKey,None)
				f=open(targetFile,'w')
				f.writelines(newContents)
				f.close()

	def _modify_desktop(self,airFile,icon_name=None):
		self._debug("Modify desktop %s"%airFile)
		air_info=self.getAirInfo(airFile)
		sw_modify_icon=False
		if 'name' in air_info.keys():
			cwd=os.getcwd()
			os.chdir('/usr/share/applications')
			desktop_list=glob.glob(air_info['name']+"*desktop")
			if desktop_list==[]:
				desktop_list=glob.glob(air_info['name'].lower()+"*desktop")
			if desktop_list:
				#First file must be the desktop but for sure...
				sw_modify_icon=False
				for desktop_file in desktop_list:
					self._debug("Testing file %s"%desktop_file)
					f=open(desktop_file,'r')
					flines=f.readlines()
					self._debug("Looking for %s"%self.adobeAirInstallFolder)
					for fline in flines:
						self._debug(fline)
						self._debug(type(fline))
						if '/opt/AdobeAirApp' in fline:
							self._debug("Match")
							sw_modify_icon=True
					f.close()
			if sw_modify_icon:
				self._debug("Setting icon")
				new_desktop=[]
				for fline in flines:
					if fline.startswith('Icon'):
						self._debug("Before: %s"%fline)
						nline='Icon=%s\n'%icon_name
						self._debug("After: %s"%nline)
						new_desktop.append(nline)
					else:
						new_desktop.append(fline)
				self._debug("Writing desktop %s"%desktop_file)
				f=open(desktop_file,'w')
				f.writelines(new_desktop)
				f.close()
			os.chdir(cwd)
	#def _modify_desktop

	def _checkPkgInstalled(self):
		installed=True
		try:
			res=subprocess.check_output(["dpkg-query","-W","-f='${Status}'",self.airPkgname])
			if "not" in str(res):
				self._debug("adobeair not installed")
				installed=False
		except Exception as e:
			self._debug("dpkg-query failed: %s"%e)
			installed=False
		return installed
	#def _checkPkgInstalled

	def _installAdobeAir(self):
		if self._installPackageDepends():
			self._debug("Installing Adobe Air")
#			adobeair_url="http://airdownload.adobe.com/air/lin/download/2.6/AdobeAIRInstaller.bin"
#			subprocess.call([tmpfile_name,"-silent","-eulaAccepted","-pingbackAllowed"])
#			os.system("DISPLAY=:0 LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu " + tmpfile_name + " -silent -eulaAccepted -pingbackAllowed")
			pkg=self._downloadAdobeAir()
			os.system("dpkg -i {}".format(pkg))
			os.remove(pkg)
			#Remove symlinks
			if os.path.isfile("/usr/lib/libgnome-keyring.so.0"):
				os.remove("/usr/lib/libgnome-keyring.so.0")
			if os.path.isfile("/usr/lib/libgnome-keyring.so.0.2.0"):
				os.remove("/usr/lib/libgnome-keyring.so.0.2.0")
			#Set the zomando as configured
			try:
				subprocess.call(["zero-center","set-configured","zero-lliurex-adobeair"])
			except:
				self._debug("Failed to set configured on adobeair zomando")
			return True
		else:
			return False
	#def _installAdobeAir

	def _checkAdobeAir(self):
		installed=self._checkPkgInstalled()
		if installed==False:
			installed=self._installAdobeAir()
		if installed==False:
			self._debug("Adobeair failed to install")
		#Now install the sdk
		self.installAdobeSDK()
	#def _checkAdobeAir

	def _installAirApp(self,airFile):
		sw_err=1
		my_env=os.environ.copy()
		my_env["PATH"]="/usr/share/air-installer/src/bin:%s"%my_env["PATH"]
		self._debug("PATH: %s"%my_env)
		my_env["DISPLAY"]=":0"
		try:
			subprocess.check_output(["/usr/bin/Adobe AIR Application Installer","-silent","-eulaAccepted","-location","/opt/AdobeAirApp",airFile],env=my_env)
			sw_err=0
		except Exception as e:
			self._debug("Install Error: %s"%e)
		return sw_err
	#def _installAirApp

	def _installAirSDK(self,airFile,icon=None):
		sw_err=0
		if not icon:
			icon=self.defaultIcon
		file_name=os.path.basename(airFile)
		basedir_name=file_name.replace('.air','')
		wrkdir=self.adobeAirInstallFolder+basedir_name
		if os.path.isdir(wrkdir):
			try:
				shutil.rmtree(wrkdir)
			except Exception as e:
				sw_err=3
				self._debug(e)
		try:
			os.makedirs(wrkdir)
		except Exception as e:
			sw_err=4
			self._debug(e)
		if sw_err==0:
			try:
				shutil.copyfile (airFile,wrkdir+"/"+file_name)
			except Exception as e:
				sw_err=1
				self._debug("SDK Install Fail: %s"%e)
		#Copy icon to hicolor
		if sw_err==0:
			hicolor_icon='/usr/share/icons/hicolor/48x48/apps/%s.png'%basedir_name
			try:
				shutil.copyfile (icon,hicolor_icon)
			except:
				sw_err=2

		self._generate_desktop_sdk(file_name)
		self._debug("Installed in %s/%s"%(wrkdir,airFile))
		return (sw_err)
	#def _installAirSDK

	def _generate_desktop(self,file_name):
		basedir_name=file_name.replace('.air','')
		desktop="/usr/share/applications/%s.desktop"%basedir_name
		exec_file=self._get_air_bin_file(basedir_name)
		self._debug("Exec: %s"%exec_file)
		if exec_file:
			f=open(desktop,'w')
			f.write("[Desktop Entry]\n\
Encoding=UTF-8\n\
Version=1.0\n\
Type=Application\n\
Exec=\""+exec_file+"\"\n\
Icon="+basedir_name+".png\n\
Terminal=false\n\
Name="+basedir_name+"\n\
Comment=Application from AdobeAir "+basedir_name+"\n\
MimeType=application/x-scratch-project\n\
Categories=Application;Education;Development;ComputerScience;\n\
")
			f.close()
			return True
		else:
			return False
#chmod +x $NEW_ICON_FILE
	#def _generate_desktop

	def _get_air_bin_file(self,basedir_name):
		target_bin=''
		for folder in os.listdir(self.adobeAirInstallFolder):
			target_folder=''
			if basedir_name.lower() in folder.lower() or basedir_name.lower==folder.lower():
				target_folder=os.listdir(self.adobeAirInstallFolder+folder)
			else:
				split_name=''
				if '-' in basedir_name.lower():
					split_name=basedir_name.lower().split('-')[0]
				elif ' ' in basedir_name.lower():
					split_name=basedir_name.lower().split(' ')[0]
				elif '.' in basedir_name.lower():
					split_name=basedir_name.lower().split('.')[0]
				if split_name!='' and split_name in folder.lower():
					target_folder=os.listdir(self.adobeAirInstallFolder+folder)
			if target_folder:
				if 'bin' in target_folder:
					candidate_list=os.listdir(self.adobeAirInstallFolder+folder+'/bin')
					for candidate_file in candidate_list:
						test_file=self.adobeAirInstallFolder+folder+'/bin/'+candidate_file
						self._debug("Testing %s"%test_file)
						if os.access(test_file,os.X_OK):
							target_bin=test_file
							self._debug("Test OK for %s"%target_bin)
							break
		return(target_bin)

	def _generate_desktop_sdk(self,file_name):
		basedir_name=file_name.replace('.air','')
		desktop="/usr/share/applications/%s.desktop"%basedir_name
		f=open(desktop,'w')
		f.write("[Desktop Entry]\n\
Encoding=UTF-8\n\
Version=1.0\n\
Type=Application\n\
Exec=/opt/adobe-air-sdk/adobe-air/adobe-air "+self.adobeAirInstallFolder+basedir_name+"/"+file_name+"\n\
Icon="+basedir_name+".png\n\
Terminal=false\n\
Name="+basedir_name+"\n\
Comment=Application from AdobeAir "+basedir_name+"\n\
MimeType=application/x-scratch-project\n\
Categories=Application;Education;Development;ComputerScience;\n\
")
		f.close()
	#def _generate_desktop_sdk

	def _downloadSDK(self):
		baseUrl="http://lliurex.net/recursos-edu/misc"
		candidateFiles=["AdobeAIRSDK.tbz2","adobe-air.tar.gz"]
		ftmp=""
		for candidate in candidateFiles:
			pkgUrl=os.path.join(baseUrl,candidate)
			req=url.Request(pkgUrl,headers={'User-Agent':'Mozilla/5.0'})
			try:
				downloadF=url.urlopen(req)
			except Exception as e:
				self._debug(e)
				continue
			ftmp=tempfile.mktemp(suffix=".".join(candidate.split(".")[1:]))
			self._debug("Download {}".format(ftmp))
			with open(ftmp,'wb') as output:
				output.write(downloadF.read())
			break
		return(ftmp)
	#def _downloadSDK

	def installAdobeSDK(self):
		if os.path.isfile(os.path.join(self.adobeAirSdkFolder,"bin","adl")):
			self._debug("Already installed")
			return
		if not os.path.isdir(self.adobeAirSdkFolder):
			os.makedirs(self.adobeAirSdkFolder)
		self._installPackageDepends()
		self._debug("Installing Adobe Air SDK")
		ftmp=self._downloadSDK()
		if ftmp.endswith(".tar.gz"):
			subprocess.call(["tar","zxf",ftmp,"-C","/opt/adobe-air-sdk"])
		else:
			subprocess.call(["tar","jxf",ftmp,"-C","/opt/adobe-air-sdk"])
		airExe=os.path.join(self.adobeAirSdkFolder,"adobe-air","adobe-air")
		if os.path.exists(airExe):
			st=os.stat(airExe)
			os.chmod(airExe,st.st_mode | 0o111)
	#def installAdobeSDK

	def _downloadAdobeAir(self):
		adobeurl="http://airdownload.adobe.com/air/lin/download/2.6/adobeair.deb"
		req=url.Request(adobeurl,headers={'User-Agent':'Mozilla/5.0'})
		try:
			adobeair=url.urlopen(req)
		except Exception as e:
			self._debug('Donwload err: %s'%e)
			return False
		(ftmp,ftmpName)=tempfile.mkstemp()
		os.close(ftmp)
		with open(ftmpName,'wb') as output:
			output.write(adobeair.read())
		st=os.stat(ftmpName)
		os.chmod(ftmpName,st.st_mode | 0o111)
		return(ftmpName)
	#def _downloadAdobeAir

	def _linkLibs(self):
		ret=True
		lib_folder='x86_64-linux-gnu'
		self._debug("Linking libs")
		try:
			if os.path.isfile("/usr/lib/libgnome-keyring.so.0"):
				os.remove("/usr/lib/libgnome-keyring.so.0")
			if os.path.isfile("/usr/lib/libgnome-keyring.so.0.2.0"):
				os.remove("/usr/lib/libgnome-keyring.so.0.2.0")
			srcPath=os.path.join("/","usr","lib","x86_64-linux-gnu")
			dstPath=os.path.join("/","usr","lib")
			os.symlink(os.path.join(srcPath,"libgnome-keyring.so.0"),os.path.join(dstDir,"libgnome-keyring.so.0"))
			os.symlink(os.path.join(srcPath,"libgnome-keyring.so.0.2.0"),os.path.join(dstDir,"libgnome-keyring.so.0.2.0"))
		except Exception as e:
			self._debug(e)
			ret=False
		return(ret)
	#def _linkLibs

	def _installPackageDepends(self):
		ret=True
		subprocess.call(["apt-get","-q","update"])
		pkgList=["libgtk2.0-0:i386",
			"libstdc++6:i386",
			"libxml2:i386",
			"libxslt1.1:i386",
			"libcanberra-gtk-module:i386",
			"gtk2-engines-murrine:i386",
			"libqt4-qt3support:i386",
			"libgnome-keyring0:i386",
			"libnss-mdns:i386",
			"libnss3:i386",
			"libatk-adaptor:i386",
			"libgail-common:i386"]
		self._debug("Installing i386 libs")
		cmd=["dpkg","--add-architecture","i386"]
		subprocess.call(cmd)
		cmd=["apt-get","-q","-y","install"]
		cmd.extend(pkgList)
		ret=subprocess.call(cmd)
		if ret!=0:
			ret=False
		else:
			ret=self._linkLibs()
		return ret
	#def _installPackageDepends

	def _recompileForCertIssue(self,airFile):
		self._debug("Rebuilding package %s"%airFile)
		newAir=''
		tmpdir=self._unzipAir(airFile)
		cwd=os.getcwd()
		os.chdir(tmpdir)
		air_xml=''
		for xml_file in os.listdir("META-INF/AIR"):
			if xml_file.endswith(".xml"):
				air_xml=xml_file
				break
		if air_xml:
			shutil.move("META-INF/AIR/"+air_xml,air_xml)
			shutil.rmtree("META-INF/",ignore_errors=True)
			os.remove("mimetype")
			self._debug("Generating new cert")
			subprocess.call(["/opt/adobe-air-sdk/bin/adt","-certificate","-cn","lliurex","2048-RSA","lliurex.p12","lliurex"])
			newAir=os.path.basename(airFile)
			my_env=os.environ.copy()
			my_env["DISPLAY"]=":0"
			try:
				subprocess.check_output(["/opt/adobe-air-sdk/bin/adt","-package","-tsa","none","-storetype","pkcs12","-keystore","lliurex.p12",newAir,air_xml,"."],input=b"lliurex",env=my_env)
			except Exception as e:
				self._debug(e)
		os.chdir(cwd)
		return tmpdir+'/'+newAir
	#def _recompileForCertIssue
	

	def _unzipAir(self,airFile):
		cwd=os.getcwd()
		tmpdir=tempfile.mkdtemp()
		self._debug("Extracting %s to %s"%(airFile,tmpdir))
		os.chdir(tmpdir)
		air_pkg=zipfile.ZipFile(airFile,'r')
		for file_to_unzip in air_pkg.infolist():
			try:
				air_pkg.extract(file_to_unzip)
			except:
				pass
		air_pkg.close()
		os.chdir(cwd)
		return (tmpdir)
	#def _unzipAir

	def _getAirDesktop(self,appName,appFolder):
		dPath="/usr/share/applications"
		fDesktop=""
		candidateF=os.path.join(dPath,"{}.desktop".format(appName))
		print("Direct load for {}".format(candidateF))
		if os.path.isfile(candidateF):
			fDesktop=candidateF
		elif os.path.isfile(candidateF.lower()):
			fDesktop=candidateF.lower()
		else:
			metaFolder=os.path.join(appFolder,"share","META-INF","AIR")
			self._debug("Not found. Inspect {}".format(metaFolder))
			if os.path.isdir(metaFolder):
				for f in os.scandir(metaFolder):
					if f.name.endswith(".desktop"):
						fDesktop=os.path.join(dPath,f.name)
						break
		return(fDesktop)
	#def _getAirDesktop

	def _getAirId(self,appName):
		airId=""
		fxml=os.path.join(self.adobeAirInstallFolder,appName,"share","application.xml")
		fAir=os.path.join(self.adobeAirInstallFolder,appName,"{}.air".format(appName))
		if os.path.isfile(fAir):
			airId="{}.air".format(appName)
		elif os.path.isfile(fAir):
			fcontent=[]
			with open(fxml,"r") as f:
				fcontent=f.readlines()
			for fline in fcontent:
				if fline.startswith('<id>'):
					appId=fline.strip()
					appId=appId.replace('<id>','')
					appId=appId.replace('</id>','')
					break
		return(airId)
	#def _getAirId

	def getInstalledApps(self):
		installed={}
		if os.path.isdir(self.adobeAirInstallFolder):
			for appFolder in os.scandir(self.adobeAirInstallFolder):
				self._debug("Inspecting {}".format(appFolder.name))
				binFolder=os.path.join(appFolder.path,"bin")
				candidateAir=os.path.join(appFolder.path,"{}.air".format(appFolder.name))
				if os.path.isdir(binFolder) or os.path.isfile(candidateAir):
					#There's an app so get relevant data
					fDesktop=self._getAirDesktop(appFolder.name,binFolder)
					appId=self._getAirId(appFolder.name)
					installed[appFolder.name]={"desktop":fDesktop,"id":appId}
		return(installed)
	#def getInstalledApps

	def _appRemove(self,airDict):
		removed=True
		airFile=self.adobeAirInstallFolder+airDict['air_id'].replace('.air','')+'/'+airDict['air_id']
		self._debug("SDK app detected %s"%airFile)
		if os.path.isfile(airFile):
			try:
				shutil.rmtree(os.path.dirname(airFile))
			except Exception as e:
				self._debug(e)
				removed=False
		return(removed)
	#def _appRemove

	def _superCowRemove(self,*args):
		removed=True
		air_id=args[-1]
		self._debug("Supercow remove %s"%air_id)
		my_env=os.environ.copy()
		my_env["DISPLAY"]=":0"
		pkgname=subprocess.check_output(["apt-cache","search",air_id],env=my_env,universal_newlines=True)
		pkglist=pkgname.split(' ')
		for pkg in pkglist:
			if air_id.lower() in pkg.lower():
				try:
					self._debug("Uninstalling {}".format(pkg))
					sw_uninstall_err=subprocess.check_output(["apt-get","-y","remove",pkg],universal_newlines=True,env=my_env)
					self._debug("Uninstalled OK")
				except Exception as e:
					removed=False
					self._debug(e)
				break
		return(removed)
	#def _superCowRemove

	def _removeDesktop(self,airDict):
		dFile=airDict.get("desktop","")
		if os.path.isfile(dFile):
			try:
				os.remove(dFile)
			except Exception as e:
				self._debug(e)
	#def _removeDesktop

	def removeAirApp(self,*kwarg):
		removed=True
		airDict=kwarg[0]
		if 'air_id' in airDict.keys():
			self._debug("Removing {}".format(airDict['air_id']))
			if airDict['air_id'].endswith('.air'):
				self._appRemove(airDict)
			else:
				#Let's try with supercow's power
				self.supercowRemove(airDict['air_id'])
				#Some air apps install more than one app so it's needed to check the installed desktop
				if 'desktop' in airDict.keys():
					self._debug("Checking full uninstall of {}"%airDict['desktop'])
					if os.path.isfile(airDict['desktop']):
						self._debug("Uninstalling air from desktop")
						desktop=airDict['desktop'].replace('.desktop','')
						supercow_remove(os.path.basename(desktop))
				if err:
					try:
						myEnv=os.environ.copy()
						myEnv["DISPLAY"]=":0"
						cmd=["/usr/bin/Adobe AIR Application Installer","-silent","-uninstall","-location"]
						cmd.append(self.adobeAirInstallFolder)
						cmd.append(airDict["air_id"])
						sw_uninstall_err=subprocess.check_output(cmd,env=myEnv)
					except Exception as e:
						removed=False
						self._debug(e)
		self._removeDesktop(airDict)
		return removed
	#def removeAirApp

	def _readInfoFromXml(self,tmpdir):
		airInfo={}
		icon=""
		name=""
		fcontent=[]
		with open("application.xml","r") as f:
			fcontent=f.readlines()
		for fline in fcontent:
			fline=fline.strip()
			if fline.startswith('<filename>'):
				name=fline
			if fline.startswith('<image48x48>'):
				if fline!='<image48x48></image48x48>' and icon=='':
					icon=fline
					self._debug(fline)
		if len(icon)>0:
			icon=icon.replace('<image48x48>','')
			icon=icon.replace('</image48x48>','')
			if icon!='':
				icon=os.path.join(tmpdir,icon)
				airInfo['icon']=icon
				self._debug("ICON: {}".format(icon))
		if len(name)>0:
			name=name.replace('<filename>','')
			airInfo['name']=name.replace('</filename>','')
		return(airInfo)
	#def _readInfoFromXml
	
	def _readInfoFromFile(self,tmpdir,airFile):
		airInfo={}
		airInfo['name']=os.path.basename(airFile)
		airInfo['name']=airInfo['name'].replace('.air','')
		os.chdir(tmpdir)
		iconFiles=glob("*/*48*png")
		if not iconFiles:
			iconFiles=glob("*48*png")
		if iconFiles:
			airInfo['icon']=iconFiles[0]
		return(airInfo)
	#def _readInfoFromFile

	def getAirInfo(self,airFile):
		airInfo={"file":airFile}
		self._debug("Recovering info from {}".format(airFile))
		tmpdir=self._unzipAir(airFile)
		cwd=os.getcwd()
		os.chdir(tmpdir+'/META-INF/AIR')
		icon=''
		name=''
		if os.path.isfile('application.xml'):
			airInfo.update(self._readInfoFromXml(tmpdir))
		else:
			airInfo.update(self_readInfoFromFile(tmpdir,airFile))
		return airInfo
	#def _getAirInfo

	def _checkIsValid(self,airFile):
		retval=False
		if airFile.endswith(".air"):
			retval=True
		return retval
	#def _checkIsValid
		
