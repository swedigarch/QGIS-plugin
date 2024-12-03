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
import base64
import traceback
from multiprocessing import cpu_count
import psycopg2
import pandas as pd
from qgis.core import Qgis, QgsSettings
from qgis.PyQt import uic, QtWidgets
from PyQt5 import QtGui
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QListWidgetItem
from PyQt5.QtCore import QDir, QSettings
from qgis.core import (QgsApplication, QgsTask, QgsProviderRegistry, QgsProject, QgsRasterLayer, QgsDataSourceUri, QgsRasterPipe, QgsRasterFileWriter, QgsCoordinateTransformContext, QgsCategorizedSymbolRenderer, QgsRendererCategory,
                        QgsSymbol, QgsMarkerSymbol, QgsWkbTypes, QgsUnitTypes)
from PyQt5.QtGui import QIcon, QPixmap
from qgis.PyQt.QtXml import QDomDocument
from . import utils as Utils
from .help_dialog import HelpDialog
from .connect_to_db_dialog import ConnectToDbDialog
from .select_connection_dialog import SelectConnectionDialog
from .export_confirmation_dialog import ExportConfirmationDialog
from .geo_package_export_task import GeoPackageExportTask
from .geo_package_bulk_export_task import GeoPackageBulkExportMainTask
from .select_subclasses_to_filter_dialog import SelectSubClassesToFilterDialog

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'swedigarch_export_dialog_base.ui'))

class SwedigarchExportDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor for (Intrasis DB Manager Dialog)"""
        super(SwedigarchExportDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.host = None
        self.port = None
        self.user_name = None
        self.password = None
        self.sslmode = QgsDataSourceUri.SslMode.SslDisable
        self.sslmode_text = ""
        self.export_folder = None
        self.bulk_export_threshold = 8
        print(f'cpu_count(): {cpu_count()}')
        if cpu_count() >= 4:
            self.bulk_export_max_number_of_subtasks = cpu_count() - 2 # leave 2 as spare
        else:
            self.bulk_export_max_number_of_subtasks = cpu_count()
        self.all_databases = []
        print(f'Max bulk export threads: {self.bulk_export_max_number_of_subtasks}, bulk export threshold: {self.bulk_export_threshold} databases')
        self.read_settings()

        #print(f"QGIS Version {Qgis.QGIS_VERSION_INT} ({Qgis.QGIS_VERSION})")
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setText(self.tr("Run export"))
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        self.button_box.button(QtWidgets.QDialogButtonBox.Cancel).setText(self.tr("Cancel"))
        self.help_button.setText(self.tr("Help"))

        self.cbOverwriteExistingGeoPackage.setText(self.tr("Overwrite existing GeoPackage"))
        self.cbOverwriteExistingGeoPackage.setToolTip(self.tr("If the GeoPackage already exist it will be overwritten if checked.\nOtherwice the GeoPackage will not be exported."))
        self.cbExportCSV.setText(self.tr("CSV"))
        self.cbExportCSV.setToolTip(self.tr("Should a CSV export also be done for every exported database"))
        self.cbFilterSubClass.setText(self.tr("Exclude Subclasses"))
        self.cbFilterSubClass.setToolTip(self.tr("Should selected Subclasses (selected in next step) be excluded from the export"))
        self.cbSimplifiedExport.setText(self.tr("Simplified GPKG"))
        self.cbSimplifiedExport.setToolTip(self.tr("Should simplified GPKG export also be done for every exported database"))

        self.pbSelectAllDb.setEnabled(False)
        self.lwDatabases.setSortingEnabled(True)
        self.lwSelectedDatabases.setSortingEnabled(True)
        self.lineEdit_DbConnection.setText(self.tr("No connection"))
        self.pgSelectConnection.clicked.connect(self.on_select_connection)
        self.pbConnect.clicked.connect(self.on_connect_clicked)
        self.pbDisconnect.clicked.connect(self.on_disconnect_clicked)
        self.pbDisconnect.setEnabled(False)
        self.lblSearchInfo.setText("")
        self.lineEditSearch.textChanged.connect(self.on_search_databases)
        self.lineEditSearch.setEnabled(False)
        self.pbBrowse.clicked.connect(self.on_browse_clicked)
        self.lwDatabases.itemDoubleClicked.connect(self.on_db_item_double_clicked)

        self.sel_databases_model = self.lwDatabases.selectionModel()
        self.sel_databases_model.selectionChanged.connect(self.on_databases_selection_changed)
        self.pbAdd.setEnabled(False)
        self.pbAdd.clicked.connect(self.on_add_databases_clicked)
        self.lwSelectedDatabases.itemDoubleClicked.connect(self.on_selected_db_item_double_clicked)
        self.sel_selected_databases_model = self.lwSelectedDatabases.selectionModel()
        self.sel_selected_databases_model.selectionChanged.connect(self.on_selected_databases_changed)
        self.pbRemove.setEnabled(False)
        self.pbRemove.clicked.connect(self.on_remove_databases_clicked)

        self.button_box.accepted.disconnect()
        self.button_box.accepted.connect(self.on_start_export_clicked)
        self.help_button.clicked.connect(self.on_help_clicked)
        self.lineEditExportDirectory.textChanged[str].connect(self.export_ready_check)
        self.pbSelectAllDb.clicked.connect(self.on_select_all_db_clicked)

    def on_select_all_db_clicked(self):
        """Handle click on button to add or remove all databases"""
        if self.lwSelectedDatabases.count() == 0:
            databases = None
            databases = [self.lwDatabases.item(x).text() for x in range(self.lwDatabases.count())]
            for database in databases:
                self.lwSelectedDatabases.addItem(database)
            self.lwDatabases.clear()
            self.export_ready_check()
            self.update_button_status()
        else:
            databases = None
            databases = [self.lwSelectedDatabases.item(x).text() for x in range(self.lwSelectedDatabases.count())]
            for database in databases:
                self.lwDatabases.addItem(database)
            self.lwSelectedDatabases.clear()
            self.export_ready_check()
            self.update_button_status()
            self.on_search_databases()
        self.update_search_info_text()

    def update_search_info_text(self):
        """Update search info text"""
        search_text = self.lineEditSearch.text()
        if Utils.is_empty_string_or_none(search_text):
            self.lblSearchInfo.setText("")
        else:
            if len(self.lwDatabases) > 0:
                self.lblSearchInfo.setText(self.tr("{0} databases found").format(len(self.lwDatabases)))
            else:
                self.lblSearchInfo.setText(self.tr("No databases match search string"))

    def on_databases_selection_changed(self):
        """Handle selection changes in databases list (top list)"""
        selection = self.sel_databases_model.selection()
        selection_count = len(selection.indexes())
        self.pbAdd.setEnabled(selection_count > 0)

    def on_selected_databases_changed(self):
        """Handle selection changes in selected databases list (bottom list)"""
        selection = self.sel_selected_databases_model.selection()
        selection_count = len(selection.indexes())
        self.pbRemove.setEnabled(selection_count > 0)

    def on_add_databases_clicked(self):
        """Add selected databases"""
        indexes = self.sel_databases_model.selectedIndexes()
        # Sort in reverse order because we need to start removing items from the bottom
        indexes.sort(key=lambda idx: idx.row(), reverse=True)
        for index in indexes:
            database = self.lwDatabases.item(index.row()).text()
            item = self.lwDatabases.itemFromIndex(index)
            self.lwDatabases.takeItem(self.lwDatabases.row(item))
            self.lwSelectedDatabases.addItem(database)

        self.export_ready_check()
        self.lwDatabases.clearSelection()
        self.update_button_status()
        self.update_search_info_text()

    def on_remove_databases_clicked(self):
        """Remove selected databases"""
        indexes = self.sel_selected_databases_model.selectedIndexes()
        # Sort in reverse order because we need to start removing items from the bottom
        indexes.sort(key=lambda idx: idx.row(), reverse=True)
        for index in indexes:
            database = self.lwSelectedDatabases.item(index.row()).text()
            item = self.lwSelectedDatabases.itemFromIndex(index)
            self.lwSelectedDatabases.takeItem(self.lwSelectedDatabases.row(item))
            self.lwDatabases.addItem(database)
        self.export_ready_check()
        self.lwSelectedDatabases.clearSelection()
        self.update_button_status()
        self.update_search_info_text()
        self.on_search_databases()

    def update_button_status(self):
        """Uppdate the status of the buttons to add and remove databases"""
        if Utils.is_empty_string_or_none(self.lineEditSearch.text()) is False:
            self.pbSelectAllDb.setEnabled(True)
            if self.lwSelectedDatabases.count() == 0:
                self.pbSelectAllDb.setText(self.tr("Select filtered databases"))
            else:
                self.pbSelectAllDb.setText(self.tr("Select no databases"))
        elif self.lwSelectedDatabases.count() == 0:
            self.pbSelectAllDb.setEnabled(True)
            self.pbSelectAllDb.setText(self.tr("Select all databases"))
        else:
            self.pbSelectAllDb.setEnabled(True)
            self.pbSelectAllDb.setText(self.tr("Select no databases"))
        enable_search = self.lwDatabases.count() > 0 or self.lwSelectedDatabases.count() != len(self.all_databases)
        self.lineEditSearch.setEnabled(enable_search)
        self.pbDisconnect.setEnabled(len(self.all_databases) > 0)

    # pylint: disable=invalid-name
    def showEvent(self, event):
        """DialogShow event, returns selected databases to top list."""
        super(SwedigarchExportDialog, self).showEvent(event)
        while self.lwSelectedDatabases.count() > 0:
            item = self.lwSelectedDatabases.item(0)
            db_name = item.text()
            self.lwSelectedDatabases.takeItem(self.lwSelectedDatabases.row(item))
            self.lwDatabases.addItem(db_name)
        self.export_ready_check()
        settings = QgsSettings()
        point = settings.value("SwedigarchGeotools/dialog_position", None)
        if point is not None:
            self.move(point)

    # pylint: disable=invalid-name
    def closeEvent(self, _):
        """The close dialog event (QCloseEvent)"""
        point = self.pos()
        settings = QgsSettings()
        settings.setValue("SwedigarchGeotools/dialog_position", point)

    def read_settings(self):
        """Read settings"""
        s = QgsSettings()
        self.host = s.value("SwedigarchGeotools/host", "localhost")
        self.port = s.value("SwedigarchGeotools/port", 5432)
        self.user_name = s.value("SwedigarchGeotools/userName", "intrasis")
        pwd_crypt = s.value("SwedigarchGeotools/password", "")
        self.password = self.decode_text(pwd_crypt)
        sslmode = s.value("SwedigarchGeotools/sslmode", "prefer")
        if sslmode is None:
            sslmode = "prefer"
        self.sslmode, self.sslmode_text = Utils.parse_sslmode(sslmode)
        self.export_folder = s.value("SwedigarchGeotools/exportFolder", "")
        self.lineEditExportDirectory.setText(self.export_folder)

    def on_select_connection(self):
        """Open Dialog to select connection stored by DB Manager"""
        sel_dlg = SelectConnectionDialog()
        if sel_dlg.exec_():
            self.host = sel_dlg.host
            if sel_dlg.port is None:
                self.port = 5432
            else:
                self.port = sel_dlg.port
            self.user_name = sel_dlg.username
            self.password = sel_dlg.password
            self.sslmode = sel_dlg.sslmode
            self.sslmode_text = sel_dlg.sslmode_text
            conn_string = f"dbname='postgres' host={self.host} user={self.user_name} password={self.password} port={self.port}{self.sslmode_text}"
            conn = psycopg2.connect(conn_string)
            db_result = pd.read_sql("SELECT datname FROM pg_database WHERE datistemplate = false AND datname <> 'postgres' ORDER BY 1", conn)
            lst_items = db_result["datname"]
            conn.close()
            self.lwDatabases.clear()
            self.lwSelectedDatabases.clear()
            self.all_databases = []
            for row in lst_items:
                self.lwDatabases.addItem(row)
                self.all_databases.append(row)

            self.update_button_status()
            self.lblSearchInfo.setText(self.tr("{0} databases found").format(len(self.all_databases)))

    def on_connect_clicked(self):
        """Connect to server"""
        con_dlg = ConnectToDbDialog(self.host, self.port, self.user_name, self.password, self.sslmode)
        if con_dlg.exec_():
            #Get (possibly) updated values from dialog
            self.host = con_dlg.host
            self.port = con_dlg.port
            self.user_name = con_dlg.user_name
            self.password = con_dlg.password
            self.sslmode = con_dlg.sslmode
            self.sslmode_text = con_dlg.sslmode_text
            s = QgsSettings()
            s.setValue("SwedigarchGeotools/host", self.host)
            s.setValue("SwedigarchGeotools/port", self.port)
            s.setValue("SwedigarchGeotools/userName", self.user_name)
            pwd_crypt = self.encode_text(self.password)
            s.setValue("SwedigarchGeotools/password", pwd_crypt)
            s.setValue("SwedigarchGeotools/sslmode", self.sslmode)

            #Use values from dialog to connect and get db names
            conn_string = f"dbname='postgres' host={self.host} user={self.user_name} password={self.password} port={self.port} application_name=swedigarch_main"
            conn = psycopg2.connect(conn_string)
            db_result = pd.read_sql("SELECT datname FROM pg_database WHERE datistemplate = false AND datname <> 'postgres' ORDER BY 1", conn)
            lst_items = db_result["datname"]
            conn.close()

            #Update GUI with new connection and db names
            conn_phrase = self.tr('Connected to')
            self.lineEdit_DbConnection.setText(f"{conn_phrase} {self.host}")
            self.lwDatabases.clear()
            self.lwSelectedDatabases.clear()
            self.all_databases = []
            for row in lst_items:
                self.lwDatabases.addItem(row)
                self.all_databases.append(row)

            self.update_button_status()
            self.lblSearchInfo.setText(self.tr("{0} databases found").format(len(self.lwDatabases)))

    def on_disconnect_clicked(self):
        """Disconnect from server"""
        msg_box = QMessageBox()
        msg_box.setText(self.tr("Disconnect from server?"))
        msg_box.setWindowTitle(self.tr("Disconnect"))
        msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msg_box.button(QMessageBox.Cancel).setText(self.tr("Cancel"))
        return_value = msg_box.exec()
        if return_value == QMessageBox.Ok:
            self.lineEdit_DbConnection.setText(self.tr("No connection"))
            self.lwDatabases.clear()
            self.lwSelectedDatabases.clear()
            self.all_databases = []
            self.update_button_status()
            self.lblSearchInfo.setText('')

    def on_search_databases(self):
        """Run database filtering based on filter text if we have any, (Search databases)"""
        self.lwDatabases.clear()
        search_text = self.lineEditSearch.text()
        selected_items = [self.lwSelectedDatabases.item(x).text() for x in range(self.lwSelectedDatabases.count())]
        for row in self.all_databases:
            if Utils.is_empty_string_or_none(search_text) or search_text.casefold() in row.casefold():
                if row not in selected_items: # Don't and already selected database
                    self.lwDatabases.addItem(row)
        if len(self.lwDatabases) > 0:
            if Utils.is_empty_string_or_none(search_text):
                self.lblSearchInfo.setText(self.tr("{0} databases found").format(len(self.lwDatabases)))
            else:
                self.lblSearchInfo.setText(self.tr("{0} databases match filter").format(len(self.lwDatabases)))
        else:
            self.lblSearchInfo.setText(self.tr("No databases match search string"))
        self.update_button_status()

    def on_db_item_double_clicked(self, item:QListWidgetItem):
        """DoubleClicked on a database in the list (top list)"""
        db_name = item.text()
        self.lwDatabases.takeItem(self.lwDatabases.row(item))
        self.lwSelectedDatabases.addItem(db_name)
        self.export_ready_check()
        self.update_button_status()
        self.update_search_info_text()

    def on_selected_db_item_double_clicked(self, item:QListWidgetItem):
        """DoubleClicked on a database in the list of selected databases (bottom list)"""
        db_name = item.text()
        self.lwSelectedDatabases.takeItem(self.lwSelectedDatabases.row(item))
        self.lwDatabases.addItem(db_name)
        self.export_ready_check()
        self.update_button_status()
        self.on_search_databases()
        self.update_search_info_text()

    def on_browse_clicked(self):
        """Browse for export folder"""
        export_folder = self.lineEditExportDirectory.text()
        if QDir(export_folder).exists():
            export_folder = QFileDialog.getExistingDirectory(self, self.tr('Select export folder'), export_folder, QtWidgets.QFileDialog.ShowDirsOnly)
        else:
            export_folder = QFileDialog.getExistingDirectory(self, self.tr('Select export folder'), "", QtWidgets.QFileDialog.ShowDirsOnly)
        if QDir(export_folder).exists():
            self.lineEditExportDirectory.setText(export_folder)
            settings = QgsSettings()
            settings.setValue("SwedigarchGeotools/exportFolder", export_folder)
            self.export_folder = export_folder
            print(f"exportFolder: {export_folder}")
        self.export_ready_check()

    def on_start_export_clicked(self):
        """Start exporting task, after verify dialog"""
        try:
            if QgsApplication.taskManager().countActiveTasks() > 0:
                msg_box = QMessageBox()
                msg_box.setText(self.tr("Wait for ongoing export to finish"))
                msg_box.setWindowTitle(self.tr("Ongoing export"))
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.exec()
            else:
                subclasses_to_exclude = []
                selected_subclasses_list = []
                databases = [self.lwSelectedDatabases.item(x).text() for x in range(self.lwSelectedDatabases.count())]

                if self.cbFilterSubClass.isChecked():
                    select_sub_classes_dlg = SelectSubClassesToFilterDialog(databases, self.host, self.user_name, self.password, self.port, self.sslmode_text, parent=self)
                    select_sub_classes_dlg.init_data_and_gui()
                    if not select_sub_classes_dlg.exec_():
                        return
                    subclasses_to_exclude = select_sub_classes_dlg.get_selected_subclasses_as_list_of_tuples()
                    selected_subclasses_list = select_sub_classes_dlg.get_selected_subclasses_as_list_of_strings()

                number_of_databases = self.lwSelectedDatabases.count()
                bulk_export_mode = number_of_databases >= self.bulk_export_threshold
                export_confirmed = self.confirm_export_dialog(bulk_export_mode, selected_subclasses_list)

                if export_confirmed:
                    export_folder = self.lineEditExportDirectory.text()
                    print(f"export_to_geopackage(db_count: {len(databases)}  export_folder: {export_folder})")
                    main_export_task = self.create_export_task(databases, export_folder, subclasses_to_exclude)
                    QgsApplication.taskManager().addTask(main_export_task)
                    QgsApplication.processEvents()
                    self.close()
        except Exception as err:
            traceback.print_exc()
            print(f"Exception in on_start_export_clicked(): {err}")

    def on_help_clicked(self):
        """Show Help dialog"""
        HelpDialog.show_help("ExportDialog")

    def create_export_task(self, databases:list[str], export_folder:str, subclasses_to_exclude:list[tuple[str,str]]) -> QgsTask:
        """Create export tasks"""
        bulk_export_mode = len(databases) >= self.bulk_export_threshold
        #bulk_export_mode = False #Bulk mode disabled
        detailed_print_outs = not bulk_export_mode
        overwrite = self.cbOverwriteExistingGeoPackage.isChecked()
        csv = self.cbExportCSV.isChecked()
        simplified = self.cbSimplifiedExport.isChecked()
        #print(f'overwrite: {overwrite} csv: {csv}')
        if not bulk_export_mode: #If not bulk export: create one main task
            return GeoPackageExportTask("Exporting GeoPackages", self.host, self.port, self.user_name, self.password, databases, export_folder, overwrite, csv, simplified, detailed_print_outs, subclasses_to_exclude)

        # is bulk export: create bulk main task with subtasks
        main_export_task = GeoPackageBulkExportMainTask("Exporting GeoPackages", self.host, self.port, self.user_name, self.password, export_folder, overwrite, csv, simplified, databases, subclasses_to_exclude)
        main_export_task.create_subtasks("Exporting GeoPackages", min(len(databases),self.bulk_export_max_number_of_subtasks))
        return main_export_task

    def confirm_export_dialog(self, bulk_export_mode: bool, class_subclass_list: list[str]) -> bool:
        """Dialog to confirm export, used before normal export (one by one)"""
        databases = [self.lwSelectedDatabases.item(x).text() for x in range(self.lwSelectedDatabases.count())]
        confirm_dlg = ExportConfirmationDialog(databases, class_subclass_list, bulk_export_mode, parent=self)
        return_value = confirm_dlg.exec()
        return return_value == 1

    def export_ready_check(self):
        """Check if we are ready for export and then enable export button"""
        #print("export_ready_check()")
        selected_db = self.lwSelectedDatabases.count() > 0
        export_folder = self.lineEditExportDirectory.text()
        #print(f"export_folder: {export_folder}")
        export_folder_ok = export_folder != "" and QDir(export_folder).exists()
        #print(f"selected_db: {selected_db}  export_folder_ok: {export_folder_ok}")
        export_ok = selected_db and export_folder_ok
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(export_ok)

    def enable_checkbox_selct_all(self):
        """Make sure there are available databases and if so enable the select all checkbox"""
        print(f"Enable: {self.lwDatabases.count() > 0}")

    def encode_text(self, text:str) -> str:
        """Base64 encode string"""
        if text != "":
            message_bytes = text.encode('ascii')
            base64_bytes = base64.b64encode(message_bytes)
            return base64_bytes.decode('ascii')
        return ""

    def decode_text(self, encoded_text:str) -> str:
        """Decode Base64 encoded string"""
        if encoded_text != "":
            base64_bytes = encoded_text.encode('ascii')
            message_bytes = base64.b64decode(base64_bytes)
            return message_bytes.decode('ascii')
        return "empty"
