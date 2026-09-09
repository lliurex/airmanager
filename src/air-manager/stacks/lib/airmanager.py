#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import stat
import datetime
import time
import subprocess
import sys
import shutil
import tempfile
import zipfile
import urllib.request as url
import glob
import json
import re

LOG='/tmp/air_manager.log'

class AirManager():
	def __init__(self):
		self.dbg=True
		self.default_icon="/usr/share/air-installer/rsrc/air-installer_icon.png"
		self.adobeair_folder="/opt/AdobeAirApp/"
		self.adobeairsdk_folder="/opt/adobe-air-sdk/"
		self.adobeair_pkgname="adobeair"
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
			f=open(LOG,'a')
			f.write("%s"%msg)
			f.close()
		except:
			print("Can't write log")
	#def _log

	def set_default_icon(self,icon):
		self.default_icon=icon

	def install(self,air_file,icon=None):
		sw_err=0
		self.rebuild=False
		sw_install_sdk=False
		self._check_adobeair()
		if not icon:
			icon=self.default_icon
		self._debug("Procced with file: %s"%air_file)
		file_name=os.path.basename(air_file)
		if self._check_file_is_air(air_file):
			basedir_name=file_name.replace(".air","")
			self._debug("Installing %s"%air_file)
			config=self._chk_config_file(air_file)
			if 'preinstall' in config.keys():
				air_file=self._recompile_for_preinstall(air_file,config['preinstall'])
			sw_err=self._install_air_package(air_file)
			if sw_err and not self.rebuild:
				self._debug("Trying rebuild...")
				modified_air_file=self._recompile_for_certificate_issue(air_file)
				self._debug("Installing %s"%modified_air_file)
				sw_err=self._install_air_package(modified_air_file)
			if sw_err:
				self._debug("Failed to install code: %s"%sw_err)
				self._debug("Going with sdk installation")
				sw_err=self._install_air_package_sdk(air_file,icon)
				sw_install_sdk=True

			sw_desktop=True
			if 'generate-desktop' in config.keys():
				sw_desktop=config['generate-desktop']

			if not sw_err and sw_install_sdk:
				#Copy icon to hicolor
				if sw_desktop:
					sw_installed=self._generate_desktop(file_name)
					if sw_installed:
						hicolor_icon='/usr/share/icons/hicolor/48x48/apps/%s.png'%basedir_name
						shutil.copyfile (icon,hicolor_icon)
						self._debug("Installed in %s"%(basedir_name))
					else:
						self._debug("%s Not Installed!!!"%(basedir_name))
#			elif not sw_err and icon!=self.default_icon:
			elif not sw_err and sw_desktop:
				#Modify desktop with icon
				hicolor_icon='/usr/share/icons/hicolor/48x48/apps/%s.png'%basedir_name
				shutil.copyfile (icon,hicolor_icon)
				icon_new=os.path.basename(hicolor_icon)
				self._modify_desktop(air_file,icon_name=icon_new)
		
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

	def _chk_config_file(self,air_file):
		pkgConfig={}
		airName=os.path.basename(air_file).replace(".air","")
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

	def _recompile_for_preinstall(self,air_file,conf):
		self._debug("Modifying package %s"%air_file)
		sw_ok=True
		new_air_file=air_file
		tmpdir=self._unzip_air_file(air_file)
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
			new_air_file=os.path.basename(air_file)
			my_env=os.environ.copy()
			my_env["DISPLAY"]=":0"
			try:
				subprocess.check_output(["/opt/adobe-air-sdk/bin/adt","-package","-tsa","none","-storetype","pkcs12","-keystore","lliurex.p12",new_air_file,air_xml,"."],input=b"lliurex",env=my_env)
				new_air_file="%s/%s"%(tmpdir,new_air_file)
			except Exception as e:
				self._debug(e)
		os.chdir(cwd)
		self.rebuild=True
		return (new_air_file)
	#def _recompile_for_certificate_issue

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

	def _modify_desktop(self,air_file,icon_name=None):
		self._debug("Modify desktop %s"%air_file)
		air_info=self.get_air_info(air_file)
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
					self._debug("Looking for %s"%self.adobeair_folder)
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

	def _check_adobeair(self):
		sw_install_adobe=False
		sw_download=False
		try:
			res=subprocess.check_output(["dpkg-query","-W","-f='${Status}'",self.adobeair_pkgname])
			if "not" in str(res):
				self._debug("adobeair not installed")
				sw_install_adobe=True
		except Exception as e:
			self._debug("dpkg-query failed: %s"%e)
			sw_install_adobe=True
		finally:
			if sw_install_adobe:
				sw_download=self._install_adobeair()

		if sw_download==False:
			if sw_install_adobe:
				self._debug("Adobeair failed to install")
			else:
				self._debug("Adobeair already installed")
		#Now install the sdk
		if not os.path.isdir(self.adobeair_folder):
			os.makedirs(self.adobeair_folder)
		self._install_adobeair_sdk()

	def _install_air_package(self,air_file):
		sw_err=1
		my_env=os.environ.copy()
		my_env["PATH"]="/usr/share/air-installer/src/bin:%s"%my_env["PATH"]
		self._debug("PATH: %s"%my_env)
		my_env["DISPLAY"]=":0"
		try:
			subprocess.check_output(["/usr/bin/Adobe AIR Application Installer","-silent","-eulaAccepted","-location","/opt/AdobeAirApp",air_file],env=my_env)
			sw_err=0
		except Exception as e:
			self._debug("Install Error: %s"%e)
		return sw_err
	#def _install_air_package

	def _install_air_package_sdk(self,air_file,icon=None):
		sw_err=0
		if not icon:
			icon=self.default_icon
		file_name=os.path.basename(air_file)
		basedir_name=file_name.replace('.air','')
		wrkdir=self.adobeair_folder+basedir_name
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
				shutil.copyfile (air_file,wrkdir+"/"+file_name)
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
		self._debug("Installed in %s/%s"%(wrkdir,air_file))
		return (sw_err)
	#def _install_air_package_sdk

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
		for folder in os.listdir(self.adobeair_folder):
			target_folder=''
			if basedir_name.lower() in folder.lower() or basedir_name.lower==folder.lower():
				target_folder=os.listdir(self.adobeair_folder+folder)
			else:
				split_name=''
				if '-' in basedir_name.lower():
					split_name=basedir_name.lower().split('-')[0]
				elif ' ' in basedir_name.lower():
					split_name=basedir_name.lower().split(' ')[0]
				elif '.' in basedir_name.lower():
					split_name=basedir_name.lower().split('.')[0]
				if split_name!='' and split_name in folder.lower():
					target_folder=os.listdir(self.adobeair_folder+folder)
			if target_folder:
				if 'bin' in target_folder:
					candidate_list=os.listdir(self.adobeair_folder+folder+'/bin')
					for candidate_file in candidate_list:
						test_file=self.adobeair_folder+folder+'/bin/'+candidate_file
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
Exec=/opt/adobe-air-sdk/adobe-air/adobe-air "+self.adobeair_folder+basedir_name+"/"+file_name+"\n\
Icon="+basedir_name+".png\n\
Terminal=false\n\
Name="+basedir_name+"\n\
Comment=Application from AdobeAir "+basedir_name+"\n\
MimeType=application/x-scratch-project\n\
Categories=Application;Education;Development;ComputerScience;\n\
")
		f.close()
	#def _generate_desktop_sdk

	def _install_adobeair_sdk(self):
		if os.path.isfile(self.adobeairsdk_folder+'adobe-air/adobe-air'):
			return
		self._install_adobeair_depends()
		self._debug("Installing Adobe Air SDK")
		adobeair_urls=["http://lliurex.net/recursos-edu/misc/AdobeAIRSDK.tbz2","http://lliurex.net/recursos-edu/misc/adobe-air.tar.gz"]
		for adobeair_url in adobeair_urls:
			req=url.Request(adobeair_url,headers={'User-Agent':'Mozilla/5.0'})
			try:
				adobeair_file=url.urlopen(req)
			except Exception as e:
				self._debug(e)
				return False
			(tmpfile,tmpfile_name)=tempfile.mkstemp()
			os.close(tmpfile)
			self._debug("Download %s"%tmpfile_name)
			with open(tmpfile_name,'wb') as output:
				output.write(adobeair_file.read())
			try:
				os.makedirs ("/opt/adobe-air-sdk")
			except:
				pass
			if adobeair_url.endswith(".tar.gz"):
				subprocess.call(["tar","zxf",tmpfile_name,"-C","/opt/adobe-air-sdk"])
			else:
				subprocess.call(["tar","jxf",tmpfile_name,"-C","/opt/adobe-air-sdk"])
		st=os.stat("/opt/adobe-air-sdk/adobe-air/adobe-air")
		os.chmod("/opt/adobe-air-sdk/adobe-air/adobe-air",st.st_mode | 0o111)

	#def _install_adobeair_sdk

	def _install_adobeair(self):
		if self._install_adobeair_depends():
			self._debug("Installing Adobe Air")
#			adobeair_url="http://airdownload.adobe.com/air/lin/download/2.6/AdobeAIRInstaller.bin"
			adobeair_url="http://airdownload.adobe.com/air/lin/download/2.6/adobeair.deb"
			req=url.Request(adobeair_url,headers={'User-Agent':'Mozilla/5.0'})
			try:
				adobeair_file=url.urlopen(req)
			except Exception as e:
				self._debug('Donwload err: %s'%e)
				return False
			(tmpfile,tmpfile_name)=tempfile.mkstemp()
			os.close(tmpfile)
			with open(tmpfile_name,'wb') as output:
				output.write(adobeair_file.read())
			st=os.stat(tmpfile_name)
			os.chmod(tmpfile_name,st.st_mode | 0o111)
#			subprocess.call([tmpfile_name,"-silent","-eulaAccepted","-pingbackAllowed"])
#			os.system("DISPLAY=:0 LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu " + tmpfile_name + " -silent -eulaAccepted -pingbackAllowed")
			os.system("dpkg -i %s"%tmpfile_name)
			os.remove(tmpfile_name)
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
	#def _install_adobeair

	def _install_adobeair_depends(self):
		subprocess.call(["apt-get","-q","update"])
		lib_folder='x86_64-linux-gnu'
		if os.uname().machine=='x86_64':
			self._debug("Installing i386 libs")
			ret=subprocess.call(["apt-get","-q","-y","install","libgtk2.0-0:i386","libstdc++6:i386","libxml2:i386","libxslt1.1:i386","libcanberra-gtk-module:i386","gtk2-engines-murrine:i386","libqt4-qt3support:i386","libgnome-keyring0:i386","libnss-mdns:i386","libnss3:i386","libatk-adaptor:i386","libgail-common:i386"])
			if ret!=0:
				ret=subprocess.call(["dpkg","--add-architecture","i386"])
				ret=subprocess.call(["apt-get","-q","-y","install","libgtk2.0-0:i386","libstdc++6:i386","libxml2:i386","libxslt1.1:i386","libcanberra-gtk-module:i386","gtk2-engines-murrine:i386","libqt4-qt3support:i386","libgnome-keyring0:i386","libnss-mdns:i386","libnss3:i386","libatk-adaptor:i386","libgail-common:i386"])
			if ret!=0:
				return False
				
		else:
			lib_folder='i386-linux-gnu'
			subprocess.call(["apt-get","-q","-y","install","libgtk2.0-0","libxslt1.1","libxml2","libnss3","libxaw7","libgnome-keyring0","libatk-adaptor","libgail-common"])
		self._debug("Linking libs")
		try:
			if os.path.isfile("/usr/lib/libgnome-keyring.so.0"):
				os.remove("/usr/lib/libgnome-keyring.so.0")
			if os.path.isfile("/usr/lib/libgnome-keyring.so.0.2.0"):
				os.remove("/usr/lib/libgnome-keyring.so.0.2.0")
			os.symlink("/usr/lib/"+lib_folder+"/libgnome-keyring.so.0","/usr/lib/libgnome-keyring.so.0")
			os.symlink("/usr/lib/"+lib_folder+"/libgnome-keyring.so.0.2.0","/usr/lib/libgnome-keyring.so.0.2.0")
		except Exception as e:
			self._debug(e)
		return True
	#def _install_adobeair_depends

	def _recompile_for_certificate_issue(self,air_file):
		self._debug("Rebuilding package %s"%air_file)
		new_air_file=''
		tmpdir=self._unzip_air_file(air_file)
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
			new_air_file=os.path.basename(air_file)
			my_env=os.environ.copy()
			my_env["DISPLAY"]=":0"
			try:
				subprocess.check_output(["/opt/adobe-air-sdk/bin/adt","-package","-tsa","none","-storetype","pkcs12","-keystore","lliurex.p12",new_air_file,air_xml,"."],input=b"lliurex",env=my_env)
			except Exception as e:
				self._debug(e)
		os.chdir(cwd)
		return tmpdir+'/'+new_air_file
	#def _recompile_for_certificate_issue
	

	def _unzip_air_file(self,air_file):
		cwd=os.getcwd()
		tmpdir=tempfile.mkdtemp()
		self._debug("Extracting %s to %s"%(air_file,tmpdir))
		os.chdir(tmpdir)
		air_pkg=zipfile.ZipFile(air_file,'r')
		for file_to_unzip in air_pkg.infolist():
			try:
				air_pkg.extract(file_to_unzip)
			except:
				pass
		air_pkg.close()
		os.chdir(cwd)
		return (tmpdir)

	def get_installed_apps(self):
		installed_apps={}
		if os.path.isdir(self.adobeair_folder):
			for app_dir in os.listdir(self.adobeair_folder):
				self._debug("Testing %s"%app_dir)
				app_desktop=''
				if os.path.isdir(self.adobeair_folder+app_dir+'/bin') or os.path.isfile(self.adobeair_folder+app_dir+'/'+app_dir+'.air'):
					#Search the desktop of the app
					self._debug("Searching desktop %s"%'/usr/share/applications/'+app_dir+'.desktop')
					sw_desktop=False
					if os.path.isdir(self.adobeair_folder+app_dir+'/share/META-INF/AIR'):
						for pkg_file in os.listdir(self.adobeair_folder+app_dir+'/share/META-INF/AIR'):
							if pkg_file.endswith('.desktop'):
								app_desktop='/usr/share/applications/'+pkg_file
								sw_desktop=True
								break
					if sw_desktop==False:
						if os.path.isfile('/usr/share/applications/'+app_dir+'.desktop'):
							app_desktop='/usr/share/applications/'+app_dir+'.desktop'
						elif os.path.isfile('/usr/share/applications/'+app_dir.lower()+'.desktop'):
							app_desktop='/usr/share/applications/'+app_dir.lower()+'.desktop'
					#Get the app_id
					app_id=''
					self._debug("Searching id %s"%self.adobeair_folder+app_dir+'/share/application.xml')
					if os.path.isfile(self.adobeair_folder+app_dir+'/share/application.xml'):
						f=open(self.adobeair_folder+app_dir+'/share/application.xml','r')
						flines=f.readlines()
						app_id=''
						for fline in flines:
							fline=fline.strip()
							if fline.startswith('<id>'):
								app_id=fline
								app_id=app_id.replace('<id>','')
								app_id=app_id.replace('</id>','')
								break
						f.close()
					elif os.path.isfile(self.adobeair_folder+app_dir+'/'+app_dir+'.air'):
						app_id=app_dir+'.air'
					installed_apps[app_dir]={'desktop':app_desktop,'air_id':app_id}
		return installed_apps
	#def get_installed_apps

	def remove_air_app(self,*kwarg):

		def supercow_remove(*args):
			air_id=args[-1]
			self._debug("Supercow remove %s"%air_id)
			my_env=os.environ.copy()
			my_env["DISPLAY"]=":0"
			pkgname=subprocess.check_output(["apt-cache","search",air_id],env=my_env,universal_newlines=True)
			pkglist=pkgname.split(' ')
			for pkg in pkglist:
				self._debug("Testing %s"%pkg)
				if air_id.lower() in pkg.lower():
					try:
						self._debug("Uninstalling %s"%pkg)
						sw_uninstall_err=subprocess.check_output(["apt-get","-y","remove",pkg],universal_newlines=True,env=my_env)
						self._debug("Uninstalled OK %s"%pkg)
						sw_err=0
					except Exception as e:
						self._debug(e)
					break

		sw_err=1
		my_env=os.environ.copy()
		my_env["DISPLAY"]=":0"
		air_dict=kwarg[0]
		sw_uninstall_err=False
		if 'air_id' in air_dict.keys():
			self._debug("Removing %s"%air_dict['air_id'])
			if air_dict['air_id'].endswith('.air'):
				air_file=self.adobeair_folder+air_dict['air_id'].replace('.air','')+'/'+air_dict['air_id']
				self._debug("SDK app detected %s"%air_file)
				if os.path.isfile(air_file):
					try:
						shutil.rmtree(os.path.dirname(air_file))
						sw_err=0
					except Exception as e:
						self._debug(e)
			else:
				try:
				#Let's try with supercow's power
					supercow_remove(air_dict['air_id'])
				except Exception as e:
						sw_uninstall_err=True
				#Some air apps install more than one app so it's needed to check the installed desktop
				try:
					if 'desktop' in air_dict.keys():
						self._debug("Checking full uninstall of %s"%air_dict['desktop'])
						if os.path.isfile(air_dict['desktop']):
							self._debug("Uninstalling air from desktop")
							desktop=air_dict['desktop'].replace('.desktop','')
							supercow_remove(os.path.basename(desktop))
				except Exception as e:
						sw_uninstall_err=True

				
				if sw_err:
					try:
						sw_uninstall_err=subprocess.check_output(["/usr/bin/Adobe AIR Application Installer","-silent","-uninstall","-location",self.adobeair_folder,air_dict['air_id']],env=my_env)
						sw_err=0
					except Exception as e:
						self._debug(e)

		if 'desktop' in air_dict.keys():
			if os.path.isfile(air_dict['desktop']):
				try:
					os.remove(air_dict['desktop'])
				except Exception as e:
					self._debug(e)
		return sw_err

	def get_air_info(self,air_file):
		air_info={}
		self._debug("Info for %s"%air_file)
		tmpdir=self._unzip_air_file(air_file)
		cwd=os.getcwd()
		os.chdir(tmpdir+'/META-INF/AIR')
		icon_line=''
		name_line=''
		if os.path.isfile('application.xml'):
			f=open('application.xml','r')
			flines=f.readlines()
			for fline in flines:
				fline=fline.strip()
				if fline.startswith('<filename>'):
					name_line=fline
				if fline.startswith('<image48x48>'):
					if fline!='<image48x48></image48x48>' and icon_line=='':
						icon_line=fline
						self._debug(fline)
			if icon_line:
				icon=icon_line.replace('<image48x48>','')
				icon=icon.replace('</image48x48>','')
				if icon!='':
					icon=tmpdir+'/'+icon
					air_info['icon']=icon
					self._debug("ICON: %s"%icon)
			if name_line:
				name=name_line.replace('<filename>','')
				air_info['name']=name.replace('</filename>','')
		else:
			air_info['name']=os.path.basename(air_file)
			air_info['name']=air_info['name'].replace('.air','')
			os.chdir(tmpdir)
			icon_files=glob("*/*48*png")
			if not icon_files:
				icon_files=glob("*48*png")
			if icon_files:
				air_info['icon']=icon_files[0]
				#air_info['pb']=GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_files[0],64,-1,True)

		return air_info
	#def _get_air_info

	def _check_file_is_air(self,air_file):
		retval=False
		if air_file.endswith(".air"):
			retval=True
		return retval
	#def _check_file_is_air
		
