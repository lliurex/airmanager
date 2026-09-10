#!/usr/bin/python3
import sys
import os
import subprocess
from PySide2.QtWidgets import QLabel, QGridLayout, QHeaderView
from QtExtraWidgets import QStackedWindowItem,QTableTouchWidget
from lib import airmanager as installer
from wdg import airapp
from app2menu import App2Menu

import gettext
_ = gettext.gettext

class manager(QStackedWindowItem):
	def __init_stack__(self):
		self.dbg=False
		self._debug("manager load")
		self.setProps(shortDesc=_("Manage air apps"),
			longDesc=_("Air Apps Manager"),
			icon="system-run",
			tooltip=_("From here you can manage the air apps installed on your system"),
			index=0,
			visible=True)
		self.hideControlButtons()
		self.airinstaller=installer.AirManager()	
		self.menu=App2Menu.app2menu()
		self.setStyleSheet(self._setCss())
		self.widget=''
	#def __init__
	
	def __initScreen__(self):
		box=QGridLayout(self)
		self.tblApps=QTableTouchWidget(0,1)
		self.tblApps.setShowGrid(False)
		self.tblApps.horizontalHeader().hide()
		self.tblApps.verticalHeader().hide()
		self.tblApps.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
		self.tblApps.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
		box.addWidget(self.tblApps)
	#def __initScreen__

	def _paintCell(self,airApp):
		widget=None
		desktop=self.menu.get_desktop_info(airApp.get('desktop',''))
		name=desktop.get('Name','')
		appId=airApp["id"]
		if len(appId)>0:
			widget=airapp.appWidget(airApp.get('desktop'))
			widget.remove.connect(self._removeAir)
			if name=="":
				name=appId.removesuffix(".air")
			widget.setName(name)
			icon=desktop.get('Icon','')
			widget.setIcon(icon)
			comment=desktop.get('Comment','')
			widget.setDesc(comment)
			execute=desktop.get('Exec','')
			widget.setExe(execute)
		return widget
	#def _paintCell

	def updateScreen(self):
		self.tblApps.setRowCount(0)
		self.tblApps.setColumnCount(1)
		apps=self.airinstaller.getInstalledApps()
		for airapp,airinfo in apps.items():
			airCell=self._paintCell(airinfo)
			if airCell!=None:
				self.tblApps.setRowCount(self.tblApps.rowCount()+1)
				self.tblApps.setCellWidget(self.tblApps.rowCount()-1,0,airCell)
		if self.tblApps.rowCount()==0:
			self.tblApps.insertRow(0)
			lbl=QLabel(_("There's no app installed"))
			lbl.setStyleSheet("background:silver;border:0px;margin:0px")
			self.tblApps.setCellWidget(0,0,lbl)


		return True
	#def _udpate_screen

	def writeConfig(self):
		if self.widget=='':
			return
		subprocess.check_call(['/usr/bin/xhost','+'])
		try:
			subprocess.check_call(['pkexec','/usr/bin/air-helper-installer.py','remove',self.widget.getName(),self.widget.getDesktop()])
		except  Exception as e:
			print(e)
		subprocess.check_call(['/usr/bin/xhost','-'])
		self.showMsg(_("App %s uninstalled"%self.widget.getName()))
		self.updateScreen()
	#def writeConfig

	def _removeAir(self,widget):
		self.widget=widget
		self.writeConfig()
	#def _removeAir

	def _setCss(self):
		css="""
		#cell{
			padding:10px;
			margin:6px;
			background-color:rgb(250,250,250);

		}
		#appName{
			font-weight:bold;
			border:0px;
		}
		#btnRemove{
			background:red;
			color:white;
			font-size:9pt;
			padding:3px;
			margin:3px;
		}
		
		"""

		return(css)
	#def _setCss

