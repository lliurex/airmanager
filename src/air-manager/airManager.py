#!/usr/bin/env python3
import sys
import os
from PySide2.QtWidgets import QApplication
from QtExtraWidgets import QStackedWindow
import gettext
gettext.textdomain('airmanager')
_ = gettext.gettext
app=QApplication(["AirManager"])
config=QStackedWindow()
if os.path.islink(__file__)==True:
	abspath=os.path.join(os.path.dirname(__file__),os.path.dirname(os.readlink(__file__)))
else:
	abspath=os.path.dirname(__file__)
config.addStacksFromFolder(os.path.join(abspath,"stacks"))
config.setBanner(os.path.join(abspath,"rsrc","air-manager_banner.png"))
#config.setWiki("https://wiki.edu.gva.es/lliurex/tiki-index.php?page=Repoman-en-Lliurex-23")
config.setIcon("airmanager")
config.show()
config.setMinimumWidth(config.sizeHint().width()*1.1)
config.setMinimumHeight(config.sizeHint().width()*0.6)
app.exec_()
