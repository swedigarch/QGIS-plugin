# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Swedigarch Geotools is a tool for field archaeologist to transform their
 data from proprietary to open format.

 Copyright (C) 2023 Swedigarch
 
 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or 
 any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <https://www.gnu.org/licenses/>.

 Contact: swedigarch@uu.se
 Address: Swedigarch, Department of Archaeology and Ancient History, 
		  Uppsala University, Box 626, 751 26 Uppsala, Sweden

***************************************************************************/
"""

import os
import sys
import traceback
import psycopg2
import pandas as pd
from . import utils as Utils
from qgis.core import QgsApplication, QgsSettings, QgsAuthMethodConfig
from qgis.PyQt import (uic, QtWidgets)
from PyQt5.QtCore import (QCoreApplication, QObject, QRunnable, QThread, QThreadPool, pyqtSignal, Qt, pyqtSlot)

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'export_confirmation_dialog.ui'))

class ExportConfirmationDialog(QtWidgets.QDialog, FORM_CLASS):
    """Init export confirmation dialog"""
    def __init__(self, databases:list[str], subclasses_to_exclude:list[str]=[], parent=None) -> None:
        """Constructor."""
        super(ExportConfirmationDialog, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.Window |
                            Qt.CustomizeWindowHint |
                            Qt.WindowTitleHint)
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setText(self.tr("Start"))
        self.button_box.button(QtWidgets.QDialogButtonBox.Cancel).setText(self.tr("Cancel"))
        self.button_box.accepted.connect(self.on_ok)
        self.button_box.rejected.connect(self.on_cancel)
        self.lwDatabases.setSortingEnabled(True)
        self.databases = databases
        self.subclasses_to_exclude = subclasses_to_exclude
        self.init_gui_load_data()
    
    def init_gui_load_data(self) -> None:
        """Load data to GUI"""
        self.lwDatabases.clear()
        for database in self.databases:
            self.lwDatabases.addItem(database)

        self.lwExcludedSubclasses.clear()
        if not self.subclasses_to_exclude:
            self.lwExcludedSubclasses.addItem("No subclasses selcted")
        else:
            for subclass in self.subclasses_to_exclude:
                self.lwExcludedSubclasses.addItem(subclass)

    def on_ok(self) -> None:
        """Connection OK"""
        self.accept()

    def on_cancel(self) -> None:
        """Dialog canceled"""
        self.close()
