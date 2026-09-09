#!/usr/bin/python3
import sys
import os
import subprocess
from PySide2.QtWidgets import QApplication, QLabel, QWidget, QPushButton,QVBoxLayout,QLineEdit,QGridLayout,QHBoxLayout,QComboBox,QCheckBox,QTableWidget, \
				QGraphicsDropShadowEffect, QHeaderView
from PySide2 import QtGui
from PySide2.QtCore import Qt,QSize,Signal
from QtExtraWidgets import QStackedWindowItem
from lib import airmanager as installer
from app2menu import App2Menu

import gettext
_ = gettext.gettext

class airWidget(QWidget):
	remove=Signal("PyQt_PyObject")
	execute=Signal("PyQt_PyObject")
	def __init__(self,parent=None):
		super (airWidget,self).__init__(parent)
		self.desktop=''
		box=QGridLayout()
		box.setColumnStretch(0,-1)
		box.setColumnStretch(1,1)
		self.btn_icon=QPushButton()
		effect=QGraphicsDropShadowEffect(blurRadius=5,xOffset=3,yOffset=3)
		self.btn_icon.setGraphicsEffect(effect)
		self.btn_icon.setIconSize(QSize(64,64))
		self.btn_icon.setMinimumHeight(72)
		self.btn_icon.clicked.connect(self._executeAir)
		box.addWidget(self.btn_icon,0,0,2,1,Qt.AlignLeft)
		self.lbl_name=QLabel("")
		self.lbl_name.setObjectName("appName")
		box.addWidget(self.lbl_name,0,1,1,1,Qt.AlignLeft)
		self.lbl_desc=QLabel("")
		box.addWidget(self.lbl_desc,1,1,1,2,Qt.AlignLeft)
		btn_remove=QPushButton(_("Remove"))
		btn_remove.setObjectName("btnRemove")
		btn_remove.clicked.connect(self._removeAir)
		box.addWidget(btn_remove,0,2,1,1,Qt.AlignLeft)
		self.setObjectName("cell")
		self.setLayout(box)
		self.setStyleSheet(self._setCss())
	#def __init__

	def mouseDoubleClickEvent(self,*args):
		self._executeAir()

	def setIcon(self,icon):
		qicon=None
		if QtGui.QIcon.hasThemeIcon(icon):
			qicon=QtGui.QIcon.fromTheme(icon)
		elif os.path.isfile(icon):
			qicon=QtGui.QIcon(icon)
		else:
			qicon=QtGui.QIcon.fromTheme("package-x-generic")
		if qicon:
			self.btn_icon.setIcon(qicon)
	#def setIcon

	def setDesktop(self,desktop):
		self.desktop=desktop
	#def setName

	def getDesktop(self):
		return(self.desktop)

	def setName(self,name):
		self.lbl_name.setText(name)
	#def setName

	def getName(self):
		return(self.lbl_name.text())

	def setDesc(self,desc):
		self.lbl_desc.setText(desc)
	#def setDesc
	
	def getDesc(self):
		return(self.lbl_desc.text())
	
	def getIcon(self):
		return(self.lbl_desc.text())
	
	def setExe(self,exe):
		self.exe=exe.replace("'","")
	#def setExe

	def _removeAir(self):
		self.remove.emit(self)

	def _executeAir(self):
		exe=["kioclient5","exec",self.desktop]
		self.pid=subprocess.Popen(exe,stdin=None,stdout=None,stderr=None,shell=False)
	#def _executeAir(self):

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
		}"""
	#def _setCss

#class airWidget

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
		self.__initScreen__()
	#def __init__
	
	def __initScreen__(self):
		box=QVBoxLayout()
		self.lst_airApps=QTableWidget(0,1)
		self.lst_airApps.setShowGrid(False)
		self.lst_airApps.horizontalHeader().hide()
		self.lst_airApps.verticalHeader().hide()
		self.lst_airApps.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
		self.lst_airApps.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
		box.addWidget(self.lst_airApps)
		self.setLayout(box)
		self.updateScreen()
		return(self)
	#def _load_screen

	def updateScreen(self):
		self.lst_airApps.clear()
		apps=self.airinstaller.get_installed_apps()
		cont=0
		for airapp,airinfo in apps.items():
			airCell=self._paintCell(airinfo)
			if airCell:
				self.lst_airApps.insertRow(cont)
				self.lst_airApps.setCellWidget(cont,0,airCell)
				self.lst_airApps.resizeRowToContents(cont)
				cont+=1
		if cont==0:
			self.lst_airApps.insertRow(0)
			lbl=QLabel(_("There's no app installed"))
			lbl.setStyleSheet("background:silver;border:0px;margin:0px")
			self.lst_airApps.setCellWidget(0,0,lbl)
			cont+=1

		while (cont<self.lst_airApps.rowCount()):
			self.lst_airApps.removeRow(cont)
		self.lst_airApps.resizeColumnsToContents()

		return True
	#def _udpate_screen

	def _paintCell(self,airApp):
		widget=None
		if airApp:
			desktop=self.menu.get_desktop_info(airApp.get('desktop',''))
			name=desktop.get('Name','')
			if name:
				widget=airWidget()
				widget.setDesktop(airApp.get('desktop'))
				widget.remove.connect(self._removeAir)
				widget.setName(name)
				icon=desktop.get('Icon','')
				widget.setIcon(icon)
				comment=desktop.get('Comment','')
				widget.setDesc(comment)
				execute=desktop.get('Exec','')
				widget.setExe(execute)
		return widget
	#def _paintCell

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

