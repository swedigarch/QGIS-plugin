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
from .help_dialog import HelpDialog
from qgis.PyQt import (uic, QtWidgets)
from qgis.core import QgsDataSourceUri
from PyQt5.QtCore import (QCoreApplication, QObject, QRunnable, QThread, QThreadPool, pyqtSignal, Qt, pyqtSlot)

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'connect_to_db_dialog_base.ui'))

class WorkerSignals(QObject):
    """Defines the signals available from ConnectToDbWorker thread."""
    ok = pyqtSignal()
    error = pyqtSignal(object)

class ConnectToDbWorker(QRunnable):
    """Connect to DB Worker thread, used to test the connection in the background"""

    def __init__(self, connection_string:str):
        """Constructor"""
        super(ConnectToDbWorker, self).__init__()
        self.connection_string = connection_string
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self) -> None:
        """The actual thread function"""
        conn = None
        try:
            conn = psycopg2.connect(self.connection_string)
            dbResult = pd.read_sql("SELECT datname FROM pg_database WHERE datistemplate = false", conn)
            databases = dbResult["datname"].to_list()
            if databases is not None:
                self.signals.ok.emit()
            else:
                print("databases whas None")
                self.signals.error.emit("databases was null")
        except psycopg2.OperationalError:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            print(f"run() {exctype}  {value}")
            self.signals.error.emit(value)
        except Exception:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        finally:
            if conn is not None:
                conn.close()

class ConnectToDbDialog(QtWidgets.QDialog, FORM_CLASS):
    """Init connect to DB dialog"""
    def __init__(self, host:str, port:int, user_name:str, password:str, sslmode:str = "prefer", parent=None) -> None:
        """Constructor."""
        super(ConnectToDbDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.setWindowFlags(Qt.Window |
                            Qt.CustomizeWindowHint |
                            Qt.WindowTitleHint)
        self.host = None
        self.port = None
        self.user_name = None
        self.password = None
        sslmodes = ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]
        initial_sslmode = "prefer"
        if not Utils.is_empty_string_or_none(sslmode):
            initial_sslmode = sslmode
        self.comboBox_sslmode.addItems(sslmodes)
        idx = sslmodes.index(initial_sslmode)
        #print(f'idx: {idx}  initial_sslmode: {initial_sslmode}')
        self.comboBox_sslmode.setCurrentIndex(idx)
        self.sslmode, self.sslmode_text = Utils.parse_sslmode(initial_sslmode)
        self.editServerHost.setText(host)
        self.is_running = False
        self.editServerPort.setText(str(port))
        self.editUsername.setText(user_name)
        self.editPassword.setText(password)
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setText(self.tr("Connect"))
        self.button_box.button(QtWidgets.QDialogButtonBox.Cancel).setText(self.tr("Cancel"))
        self.button_box.accepted.connect(self.on_connect_clicked)
        self.button_box.rejected.connect(self.on_cancel)
        self.help_button.setText(self.tr("Help"))
        self.help_button.clicked.connect(self.on_help_clicked)
        self.threadpool = QThreadPool()

    def on_connect_clicked(self) -> None:
        """Connect clicked handler, will test the connection (in background thread) and if successful close the dialog"""
        self.host = self.editServerHost.text()
        self.port = self.editServerPort.text()
        self.user_name = self.editUsername.text()
        self.password = self.editPassword.text()
        self.sslmode, self.sslmode_text = Utils.parse_sslmode(self.comboBox_sslmode.currentText())
        self.is_running = True
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        self.button_box.button(QtWidgets.QDialogButtonBox.Cancel).setEnabled(False)
        self.lblInfo.setStyleSheet("color: black")
        self.lblInfo.setText(self.tr("Trying to connect to the server"))
        connection_string = f"dbname='postgres' host={self.host} user={self.user_name} password={self.password} port={self.port}{self.sslmode_text}"
        connect_worker = ConnectToDbWorker(connection_string)
        connect_worker.signals.ok.connect(self.connection_ok)
        connect_worker.signals.error.connect(self.connection_error)
        self.threadpool.start(connect_worker)

    def connection_ok(self) -> None:
        """Connection OK, called from background thread"""
        self.is_running = False
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        self.button_box.button(QtWidgets.QDialogButtonBox.Cancel).setEnabled(True)
        self.accept()

    def connection_error(self, error:str) -> None:
        """Connection error, called from background thread"""
        print(f"connection_error() {error}")
        self.is_running = False
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        self.button_box.button(QtWidgets.QDialogButtonBox.Cancel).setEnabled(True)

        self.lblInfo.setStyleSheet("color: red")
        error_text = f"{error}"
        if Utils.is_not_blank(error_text):
            self.lblInfo.setText(error_text)
        else:
            self.lblInfo.setText(self.tr("Empty error, may be login error"))
            # Empty Error: https://github.com/psycopg/psycopg2/issues/1442

    def on_cancel(self) -> None:
        """Dialog canceled"""
        if self.is_running is not True:
            self.close()

    def on_help_clicked(self) -> None:
        """Show Help dialog"""
        HelpDialog.show_help("ConnectToDbDialog")
