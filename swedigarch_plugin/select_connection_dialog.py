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
from qgis.core import QgsApplication, QgsSettings, QgsAuthMethodConfig, QgsDataSourceUri
from qgis.PyQt import (uic, QtWidgets)
from PyQt5.QtCore import (QCoreApplication, QObject, QRunnable, QThread, QThreadPool, pyqtSignal, Qt, pyqtSlot)

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'select_connection_dialog_base.ui'))

class WorkerSignals(QObject):
    '''Defines the signals available from ConnectToDbWorker thread.'''
    ok = pyqtSignal()
    error = pyqtSignal(object)

class ConnectToDbWorker(QRunnable):
    """Connect to DB Worker thread, used to test the connection in the background"""

    def __init__(self, connection_string):
        """Constructor"""
        super(ConnectToDbWorker, self).__init__()
        self.connection_string = connection_string
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        """The actual thread function"""
        conn = None
        try:
            conn = psycopg2.connect(self.connection_string)
            db_result = pd.read_sql("SELECT datname FROM pg_database WHERE datistemplate = false", conn)
            # Is the next line necessary? databases variable is not used in the script.
            databases = db_result["datname"].to_list()
            if databases is not None:
                self.signals.ok.emit()
            else:
                print("databases whas None")
                self.signals.error.emit("databases was null")
        except psycopg2.OperationalError:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            #print(f"run() {exctype}  {value}")
            self.signals.error.emit(value)
        except Exception:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        finally:
            if conn is not None:
                conn.close()

class SelectConnectionDialog(QtWidgets.QDialog, FORM_CLASS):
    """Init select connection dialog"""
    def __init__(self, parent=None):
        """Constructor."""
        super(SelectConnectionDialog, self).__init__(parent)
        self.host = None
        self.port = None
        self.username = None
        self.password = None
        self.sslmode = QgsDataSourceUri.SslMode.SslDisable
        self.sslmode_text = ""
        self.is_running = False
        self.setupUi(self)
        self.setWindowFlags(Qt.Window |
                            Qt.CustomizeWindowHint |
                            Qt.WindowTitleHint)
        self.postGisConnectionComboBox.currentIndexChanged.connect(self.on_connection_changed)
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setText(self.tr("Connect"))
        self.button_box.button(QtWidgets.QDialogButtonBox.Cancel).setText(self.tr("Cancel"))
        self.button_box.accepted.connect(self.on_ok)
        self.button_box.rejected.connect(self.on_cancel)
        self.help_button.setText(self.tr("Help"))
        self.help_button.clicked.connect(self.on_help_clicked)
        self.threadpool = QThreadPool()
        self.set_info_boxes()
        settings = QgsSettings()
        settings.beginGroup("/PostgreSQL/connections/")
        connections = settings.childGroups()
        self.postGisConnectionComboBox.addItems(connections)

    def on_connection_changed(self) -> None:
        """Database connection selection changed, so test it"""
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        self.button_box.button(QtWidgets.QDialogButtonBox.Cancel).setEnabled(False)
        self.lblInfo.setStyleSheet("color: black")
        self.lblInfo.setText(self.tr("Trying to connect to the server"))
        conn = self.postGisConnectionComboBox.currentText()
        self.is_running = True
        connection_string = self.get_postgres_connection_string(conn)
        self.set_info_boxes(True)
        connect_worker = ConnectToDbWorker(connection_string)
        connect_worker.signals.ok.connect(self.connection_ok)
        connect_worker.signals.error.connect(self.connection_error)
        self.threadpool.start(connect_worker)

    def connection_ok(self) -> None:
        """Connection OK, called from background thread"""
        self.is_running = False
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        self.button_box.button(QtWidgets.QDialogButtonBox.Cancel).setEnabled(True)
        self.lblInfo.setStyleSheet("color: green")
        self.lblInfo.setText(self.tr("Connection OK"))
        self.editServerHost.setText(self.host)
        self.editServerPort.setText(str(self.port))
        self.editUsername.setText(self.username)
        self.editPassword.setText(self.password)

    def connection_error(self, error:str) -> None:
        """Connection error, called from background thread"""
        print(f"connection_error() {error}")
        self.is_running = False
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        self.button_box.button(QtWidgets.QDialogButtonBox.Cancel).setEnabled(True)
        self.editServerHost.setText(self.host)
        self.editServerPort.setText(str(self.port))
        self.editUsername.setText(self.username)
        self.editPassword.setText(self.password)
        self.lblInfo.setStyleSheet("color: red")
        error_text = f"{error}"
        if Utils.is_not_blank(error_text):
            self.lblInfo.setText(error_text)
        else:
            self.lblInfo.setText(self.tr("Empty error, may be login error"))
            # Empty Error: https://github.com/psycopg/psycopg2/issues/1442

    def on_ok(self) -> None:
        """Connection OK"""
        # The propeties have already been set in get_postgres_connection_string() before testing the connection
        self.accept()

    def on_cancel(self) -> None:
        """Dialog canceled"""
        self.close()

    def on_help_clicked(self) -> None:
        """Show Help dialog"""
        HelpDialog.show_help("SelectConnectionDialog")

    def set_info_boxes(self, set_info:bool = False) -> None:
        """Set text in text boxes"""
        if set_info:
            self.editServerHost.setText(self.host)
            self.editServerPort.setText(self.port)
            self.editUsername.setText(self.username)
            self.editPassword.setText(self.password)
        else:
            self.editServerHost.setText("")
            self.editServerPort.setText("")
            self.editUsername.setText("")
            self.editPassword.setText("")

    def read_postgres_connection_info(self, selected:str) -> None:
        """Read PostgreSQL connection info with QgsSettings"""
        settings = QgsSettings()
        settings.beginGroup("PostgreSQL/connections/" + selected)
        self.host = settings.value("host", "", type=str)
        self.port = settings.value("port", "5432", type=str)
        username = settings.value("username", "", type=str)
        password = settings.value("password", "", type=str)
        sslmode = settings.value("sslmode", "", type=str)
        self.sslmode, self.sslmode_text = Utils.parse_sslmode(sslmode)
        authconf = settings.value('authcfg', None)
        settings.endGroup()
        if authconf:
            auth_manager = QgsApplication.authManager()
            conf = QgsAuthMethodConfig()
            auth_manager.loadAuthenticationConfig(authconf, conf, True)
            if conf.id():
                self.username = conf.config('username', '')
                self.password = conf.config('password', '')
        else:
            self.username = username
            self.password = password

    def get_postgres_connection_string(self, selected:str) -> str:
        """Make connection string"""
        self.read_postgres_connection_info(selected)
        connection_string = f"dbname='postgres' host={self.host} user={self.username} password={self.password} port={self.port}{self.sslmode_text}"
        return connection_string
