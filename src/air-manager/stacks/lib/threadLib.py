#!/usr/bin/python3
from PySide2.QtCore import QThread
import subprocess

class exeApp(QThread):
	def __init__(self,parent=None):
		super (exeApp,self).__init__(parent)
		self.app=None
	#def __init__

	def setApp(self,app):
		self.app=app
	#def setApp

	def run(self):
		cmd=["kioclient5","exec",self.app]
		subprocess.run(cmd,stdin=None,stdout=None,stderr=None,shell=False)
	#def run
#class exeApp

