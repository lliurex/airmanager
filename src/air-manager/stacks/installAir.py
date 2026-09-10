#!/usr/bin/python3
import sys
import os
import subprocess
from PySide2.QtWidgets import QLabel, QWidget, QPushButton,QLineEdit,QGridLayout,QFileDialog
from PySide2.QtGui import QIcon,QPixmap
from PySide2.QtCore import Qt,QSize
from QtExtraWidgets import QStackedWindowItem
from lib import airmanager as installer
import tempfile

import gettext
_ = gettext.gettext

class installAir(QStackedWindowItem):
	def __init_stack__(self):
		self.dbg=False
		self._debug("installer load")
		self.setProps(shortDesc=_("Install air apps"),
			longDesc=_("Air Apps Installer"),
			icon="install",
			tooltip=_("From here you can manage the air apps installed on your system"),
			index=1,
			visible=True)
		self.enabled=True
#		self.hideControlButtons()
		self.airManager=installer.AirManager()	
		self.setStyleSheet(self._setCss())
		self.airInfo={}
	#def __init__
	
	def __initScreen__(self):
		box=QGridLayout()
		box.addWidget(QLabel(_("Air file")),0,0,1,1)
		self.inpFile=QLineEdit()
		self.inpFile.setPlaceholderText(_("Choose file for install"))
		box.addWidget(self.inpFile,1,0,1,1)
		btnFile=QPushButton("...")
		btnFile.setObjectName("fileButton")
		btnFile.clicked.connect(self._chooseAirFile)
		box.addWidget(btnFile,1,1,1,1)
		box.addWidget(QLabel(_("App name")),2,0,1,1)
		self.btnIcon=QPushButton()
		self.btnIcon.setIconSize(QSize(64,64))
		self.btnIcon.setToolTip(_("Push for icon change"))
		box.addWidget(self.btnIcon,2,1,2,1)
		self.inpName=QLineEdit()
		self.inpName.setObjectName("fileInput")
		self.inpName.setPlaceholderText(_("Application name"))
		box.addWidget(self.inpName,3,0,1,1)
		box.addWidget(QLabel(_("App description")),4,0,1,1)
		self.inpDesc=QLineEdit()
		self.inpDesc.setPlaceholderText(_("Application description"))
		box.addWidget(self.inpDesc,5,0,1,2)
		self.setLayout(box)
		self.btnAccept.clicked.connect(self.writeConfig)
		return(self)
	#def __initScreen__

	def _chooseAirFile(self):
		fdia=QFileDialog()
		fdia.setNameFilter("air apps(*.air)")
		if (fdia.exec_()):
			fchoosed=fdia.selectedFiles()[0]
			self.inpFile.setText(fchoosed)
			self._loadAppData(fchoosed)
	#def _chooseAirFile

	def _loadAppData(self,air=""):
		if air:
			self.airInfo=self.airManager.getAirInfo(air)
		else:
			self.airInfo={}
		self.updateScreen()
	#def _loadAppData

	def updateScreen(self):
		icon=self.airInfo.get("icon","xterm")
		pxm=QPixmap(icon)
		icn=QIcon(pxm)
		self.btnIcon.setIcon(icn)
		self.inpName.setText(self.airInfo.get("name",""))
	#def updateScreen
	
	def writeConfig(self):
		tmpIcon=tempfile.mkstemp()[1]
		self.btnIcon.icon().pixmap(QSize(64,64)).save(tmpIcon,"PNG")
		try:
			ins=subprocess.check_call(['pkexec','/usr/bin/air-helper-installer.py','install',self.airInfo["file"],tmpIcon])
			self.install_err=False
		except Exception as e:
			print(e)
		subprocess.check_output(["xdg-mime","install","/usr/share/mime/packages/x-air-installer.xml"])
		subprocess.check_output(["xdg-mime","default","/usr/share/applications/air-installer.desktop","/usr/share/mime/packages/x-air-installer.xml"],input=b"")
		subprocess.check_call(['/usr/bin/xhost','-'])
		self.showMsg(_("App %s installed succesfully"%os.path.basename(air)))
	#def writeConfig

	def _setCss(self):
		css="""
			#fileButton{
				margin:0px;
				padding:1px;
			}
			#fileInput{
				margin:0px;
			}
			#imgButton{
				margin:0px;
				padding:0px;
			}"""
		return(css)
	#def _setCss

