#!/usr/bin/python3
from PySide2.QtWidgets import QLabel, QWidget, QPushButton,QGridLayout, QHeaderView
from PySide2.QtGui import QIcon,QCursor
from PySide2.QtCore import Qt,QSize,Signal,QThread
from lib.threadLib import exeApp
from extras.i18n import *

class appWidget(QWidget):
	remove=Signal(str)
	execute=Signal(str)

	def __init__(self,desktop,parent=None):
		super (appWidget,self).__init__(parent)
		self.app=desktop
		self.exeApp=exeApp()
		self.exeApp.finished.connect(self._endExecuteApp)
		self.__initScreen__()
	#def __init__

	def __initScreen__(self,*args):
		fontBtn=self.font()
		fontBtn.setPointSize(fontBtn.pointSize()-2)
		box=QGridLayout()
		box.setColumnStretch(0,-1)
		box.setColumnStretch(1,1)
		self.btnIcon=QPushButton()
		self.btnIcon.setIconSize(QSize(64,64))
		self.btnIcon.setMinimumHeight(72)
		#self.btnIcon.clicked.connect(self._executeApp)
		box.addWidget(self.btnIcon,0,0,2,1,Qt.AlignLeft)
		self.lblName=QLabel("")
		self.lblName.setObjectName("appName")
		box.addWidget(self.lblName,0,1,1,1,Qt.AlignLeft)
		self.lblDesc=QLabel("")
		box.addWidget(self.lblDesc,1,1,1,3,Qt.AlignLeft)
		self.btnLaunch=QPushButton(i18n["APPLAUNCH"])
		self.btnLaunch.setFont(fontBtn)
		self.btnLaunch.setObjectName("btnLaunch")
		self.btnLaunch.clicked.connect(self._executeApp)
		self.btnLaunch.setCursor(Qt.PointingHandCursor)
		box.addWidget(self.btnLaunch,0,2,1,1,Qt.AlignLeft)
		self.btnRemove=QPushButton(i18n["APPREMOVE"])
		self.btnRemove.setFont(fontBtn)
		self.btnRemove.setObjectName("btnRemove")
		self.btnRemove.clicked.connect(self._removeApp)
		self.btnRemove.setCursor(Qt.PointingHandCursor)
		box.addWidget(self.btnRemove,0,3,1,1,Qt.AlignLeft)
		self.setObjectName("cell")
		self.setLayout(box)
		self.setStyleSheet(self._setCss())
	#def __initScreen__

	def __init2__(self,parent=None):
		super (airWidget,self).__init__(parent)
		self.desktop=''
		box=QGridLayout()
		box.setColumnStretch(0,-1)
		box.setColumnStretch(1,1)
		self.btnIcon=QPushButton()
		self.btnIcon.setIconSize(QSize(64,64))
		self.btnIcon.setMinimumHeight(72)
		self.btnIcon.clicked.connect(self._executeAir)
		box.addWidget(self.btnIcon,0,0,2,1,Qt.AlignLeft)
		self.lblName=QLabel("")
		self.lblName.setObjectName("appName")
		box.addWidget(self.lblName,0,1,1,1,Qt.AlignLeft)
		self.lblDesc=QLabel("")
		box.addWidget(self.lblDesc,1,1,1,2,Qt.AlignLeft)
		btnRemove=QPushButton(_("Remove"))
		btnRemove.setObjectName("btnRemove")
		btnRemove.clicked.connect(self._removeAir)
		box.addWidget(btnRemove,0,2,1,1,Qt.AlignLeft)
		self.setObjectName("cell")
		self.setLayout(box)
		self.setStyleSheet(self._setCss())
	#def __init__

	def mouseDoubleClickEvent(self,*args):
		self._executeApp()
	#def mouseDoubleClickEvent

	def getDesktop(self):
		return(self.desktop)
	#def getDesktop

	def setDesktop(self,desktop):
		self.desktop=desktop
	#def setDesktop

	def setIcon(self,icon):
		icn=None
		icn=QIcon.fromTheme(icon)
		if icn.isNull():
			icn=QIcon(icon)
		if icn.isNull():
			icn=QIcon.fromTheme("package-x-generic")
		if icn:
			self.btnIcon.setIcon(icn)
	#def setIcon

	def setName(self,name):
		self.lblName.setText(name)
	#def setName

	def getName(self):
		return(self.lblName.text())
	#def getName(self):

	def setDesc(self,desc):
		self.lblDesc.setText(desc)
	#def setDesc
	
	def getDesc(self):
		return(self.lblDesc.text())
	
	def getIcon(self):
		return(self.lblDesc.text())
	
	def setExe(self,exe):
		self.exe=exe.replace("'","")
	#def setExe

	def _removeApp(self):
		self.remove.emit(self)
	#def _removeApp

	def _executeApp(self):
		cursor=QCursor(Qt.WaitCursor)
		self.btnLaunch.setCursor(cursor)
		cursor=QCursor(Qt.ForbiddenCursor)
		self.btnRemove.setCursor(cursor)
		self.blockSignals(True)
		self.exeApp.setApp(self.app)
		self.exeApp.start()
	#def _executeApp(self):

	def _endExecuteApp(self):
		cursor=QCursor(Qt.PointingHandCursor)
		self.btnLaunch.setCursor(cursor)
		self.btnRemove.setCursor(cursor)
		self.blockSignals(False)
	#def _endExecuteApp

	def _executeApp2(self):
		exe=["kioclient5","exec",self.desktop]
		self.pid=subprocess.Popen(exe,stdin=None,stdout=None,stderr=None,shell=False)
	#def _executeAir(self):

	def _setCss(self):
		css="""
		#btnRemove{
			background:red;
			color:white;
		}
		"""
	#def _setCss
#class appWidget


