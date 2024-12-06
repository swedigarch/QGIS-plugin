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

# Initialize Qt resources from file resources.py
import configparser
from pathlib import Path
import os.path
import glob
import traceback
from typing import Callable
#import numpy as np
# Import the code for the dialog
from qgis.utils import iface
from qgis.core import QgsApplication, QgsProject, QgsTask, Qgis, QgsSettings, QgsMessageLog, QgsVectorLayer, QgsWkbTypes, QgsVectorFileWriter, QgsLayerMetadata
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QStyle, QWidget
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import QDir, QSettings
from osgeo import ogr
from swedigarch_plugin import export_utils
from .swedigarch_export_dialog import SwedigarchExportDialog
from .intrasis_analysis_browse_relations import IntrasisAnalysisBrowseRelationsDialog
from .intrasis_analysis_browse_tables import IntrasisAnalysisBrowseTablesDialog
from .export_geopackage_to_csv import export_geopackage_to_csv
from .resources import * # This row is needed for the ToolBar button to get its icon.
from . import utils as Utils
from .constant import RetCode
from .geopackage_export import export_simplified_gpkg

class SwedigarchGeotools:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        self.swedish_locale = "sv_SE"
        user_locale = QSettings().value("locale/userLocale")
        print(f"userLocale: {user_locale}")
        locale = user_locale
        #sometimes swedish locale is "sv" and sometimes "sv_SE" need to chatch all "sv_ cases" and send to same .qm file
        if locale.startswith("sv"):
            locale = self.swedish_locale
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            f'swedigarch_db_mgr_{locale}.qm')
        if os.path.exists(locale_path) is False:
            print(f"locale_path: {locale_path}  does not exist!")

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = iface.pluginMenu().addMenu(
            QIcon(":/plugins/swedigarch_plugin/assets/svedigark.svg"), self.tr("&Swedigarch Geotools")
        )
        self.menu.setObjectName("swedigarch_plugin_menu")

        #self.menu = self.tr('&Swedigarch Geotools')
        self.toolbar = self.iface.addToolBar('Swedigarch Geotools')
        self.toolbar.setObjectName('Swedigarch Geotools')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None
        self.first_start_browse_relations = None
        self.first_start_browse_tables = None

        self.dlg = None
        self.dlg_browse_tables = None
        self.title_export_gpkg_to_csv = self.tr('Export GPKG to CSV')
        self.title_export_simplified_gpkg = self.tr('Export simplified version of GPKG')

        # Explicitly signal using exceptions to silence warning
        ogr.UseExceptions()

    # noinspection PyMethodMayBeStatic
    def tr(self, message:str) -> str:
        """Get the translation for a string using Qt translation API."""
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('SwedigarchGeotools', message)

    def add_action(
        self,
        icon_in, # str|QIcon
        text:str,
        callback:Callable,
        enabled_flag:bool=True,
        add_to_toolbar:bool=True,
        status_tip:str=None,
        whats_this:str=None,
        parent=None) -> QAction:
        """Help function to add an action with icon, to menu and toolbar (as selected)

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        if isinstance(icon_in, str):
            icon = QIcon(icon_in)
        else:
            icon = icon_in

        #action = QAction(icon, text, parent)
        action = self.menu.addAction(icon, text)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action) # Adds plugin icon to Plugins toolbar

        self.actions.append(action)
        return action

    def initGui(self) -> None:
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/swedigarch_plugin/assets/id.svg'
        self.add_action(
            icon_path,
            text=self.tr('Intrasis DB Manager'),
            callback=self.run_export_dialog,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/swedigarch_plugin/assets/cs.svg'
        self.add_action(
            icon_path,
            text=self.tr('Intrasis Class/Subclass Browser'),
            callback=self.run_analysis_browse_tables,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/swedigarch_plugin/assets/rb.svg'
        self.add_action(
            icon_path,
            text=self.tr('Intrasis Relationship Browser'),
            callback=self.run_analysis_browse_relations,
            parent=self.iface.mainWindow())

        self.add_action(
            '',
            text=self.title_export_gpkg_to_csv,
            callback=self.export_gpkg_to_csv,
            parent=self.iface.mainWindow(),
            add_to_toolbar=False)

        self.add_action(
            '',
            text=self.title_export_simplified_gpkg,
            callback=self.on_export_simplified_gpkg,
            parent=self.iface.mainWindow(),
            add_to_toolbar=False)

        self.add_action(
            self.menu.style().standardIcon(QStyle.SP_MessageBoxInformation),
            text=self.tr("About"),
            callback=self.show_about,
            parent=self.iface.mainWindow(),
            add_to_toolbar=False)

        # will be set False in run()
        self.first_start = True
        self.first_start_browse_relations = True
        self.first_start_browse_tables = True

    def unload(self) -> None:
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr('&Swedigarch Geotools'),
                action)
            self.iface.removeToolBarIcon(action)
        self.iface.mainWindow().removeToolBar(self.toolbar)

    def run_export_dialog(self) -> None:
        """Run method that performs all the real work (Intrasis DB Manager)"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start:
            self.first_start_browse_relations = True
            self.first_start = False
            self.dlg = SwedigarchExportDialog()
        else:
            self.dlg.activateWindow()

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass

    def run_analysis_browse_relations(self) -> None:
        """Run method that performs all the real work (Swedigarch DB Relationship Browser Dialog)"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start_browse_relations:
            self.first_start = True
            self.first_start_browse_relations = False
            self.dlg = IntrasisAnalysisBrowseRelationsDialog()
        else:
            self.dlg.activateWindow()

        # Check if user has any geopackages loaded
        gpkg_list = Utils.find_geo_packages()
        if gpkg_list is None or len(gpkg_list) == 0:
            self.dlg.show_messagebox_no_loaded_gpkg()
            return

        # Init selected features and check the there is a selection and that user did not cancel before showing the dialog
        features_selected, user_canceled = self.dlg.init_selected_features_and_active_geopackage()

        if user_canceled:
            return

        if not features_selected:
            self.dlg.show_messagebox_no_selected_objects()
            return

        self.dlg.init_data_and_gui()

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass

    def run_analysis_browse_tables(self) -> None:
        """Run method that performs all the real work (Swedigarch Analysis Class/Subclass Browser)"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start_browse_tables == False:
            self.dlg_browse_tables = IntrasisAnalysisBrowseTablesDialog()
        if self.first_start_browse_tables:
            self.first_start = True
            self.first_start_browse_tables = False
            self.dlg_browse_tables = IntrasisAnalysisBrowseTablesDialog()
        else:
            self.dlg_browse_tables.activateWindow()

        intrasis_gpkg_loaded = self.dlg_browse_tables.check_if_intrasis_geopackage_is_loaded()
        if not intrasis_gpkg_loaded:
            self.dlg_browse_tables.show_messagebox_no_loaded_gpkg(QIcon(":/plugins/swedigarch_plugin/assets/svedigark.svg"))
            return
        user_select_klicked = self.dlg_browse_tables.select_and_activate_intrasis_geopackage()
        self.dlg_browse_tables.init_gui()
        if not user_select_klicked:
            return

        # show the dialog
        self.dlg_browse_tables.show()
        # Run the dialog event loop
        result = self.dlg_browse_tables.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass

    def export_gpkg_to_csv(self) -> None:
        """Export all GPKG in selected folder to CSV"""
        try:
            s = QgsSettings()
            export_folder = s.value("SwedigarchGeotools/exportFolder", "")
            print(f'start export_folder: {export_folder}')
            if QDir(export_folder).exists():
                export_folder = QFileDialog.getExistingDirectory(None, self.tr('Select folder to convert GPKG to CSV in'), export_folder, QtWidgets.QFileDialog.ShowDirsOnly)
            else:
                export_folder = QFileDialog.getExistingDirectory(None, self.tr('Select folder to convert GPKG to CSV in'), "", QtWidgets.QFileDialog.ShowDirsOnly)
            if export_folder == '':
                return # Canceled

            print(f'Selected export_folder: {export_folder}')
            all_gpkg_files = []
            gpkg_files = []
            for gpkg_file in glob.glob(f'{export_folder}/*.gpkg'):
                all_gpkg_files.append(gpkg_file)
                if Utils.is_intrasis_gpkg_export(gpkg_file) is True:
                    gpkg_files.append(gpkg_file)
                else:
                    QgsMessageLog.logMessage(f'{gpkg_file} is not an Intrasis GPKG, skipping', self.title_export_gpkg_to_csv, Qgis.Info)

            msg_box = QMessageBox()
            msg_box.setWindowTitle(self.title_export_gpkg_to_csv)
            msg_box.setIcon(QMessageBox.Information)
            if len(gpkg_files) == 0:
                msg_box.setStandardButtons(QMessageBox.Ok)
                msg_box.button(QMessageBox.Ok).setText(self.tr("OK"))
                msg_box.setText(self.tr('Selected folder does not contain any Intrasis GeoPackages'))
                msg_box.exec()
                return

            msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            msg_box.button(QMessageBox.Cancel).setText(self.tr("Cancel"))
            text = self.tr('Start export of _COUNT_ Intrasis GeoPackages to CSV-zip files.\nIn directory _FOLDER_')
            text = text.replace('_COUNT_', f'{len(gpkg_files)}')
            text = text.replace('_FOLDER_', f'{export_folder}')
            msg_box.setText(text)
            return_value = msg_box.exec()
            if return_value != QMessageBox.Ok:
                return

            globals()['Task_export_gpkg_to_csv'] = QgsTask.fromFunction(
                self.title_export_gpkg_to_csv,
                self.task_export_gpkg_to_csv,
                on_finished=self.export_gpkg_to_csv_done,
                export_folder = export_folder,
                gpkg_files = gpkg_files)
            QgsApplication.taskManager().addTask(globals()['Task_export_gpkg_to_csv'])
            QgsApplication.processEvents()

        except Exception as err:
            print(f'export_gpkg_to_csv() Exception: {err}')

    def task_export_gpkg_to_csv(self, task:QgsTask, export_folder:str, gpkg_files:list) -> tuple[int, int]:
        """Task to run actual calls to export_geopackage_to_csv()"""
        try:
            task.setProgress(1)
            with open(export_utils.create_log_file_name(export_folder, "folder_gpkg_to_csv"), "w", encoding='utf-8') as log_file:
                failed = 0
                total_count = 0
                print(f'Found {len(gpkg_files)} Intrasis GPKG files in folder: {export_folder}')
                max_length = len(max(gpkg_files, key=len))
                log_file.write(f'Starting export of {len(gpkg_files)} Intrasis GPKG files in folder: {export_folder}\n')
                log_file.flush()
                file_count = len(gpkg_files)
                QgsMessageLog.logMessage(f'Starting export of {file_count} Intrasis GPKG files to CSV' ,self.title_export_gpkg_to_csv, Qgis.Info)
                for gpkg_file in gpkg_files:
                    if task.isCanceled():
                        QgsMessageLog.logMessage(f'Task was canceled: {task.description()}', self.title_export_gpkg_to_csv, Qgis.Info)
                        return None

                    padded_gpkg_file = gpkg_file.ljust(max_length + 2)
                    ret_code, error_msg, output_filename = export_geopackage_to_csv(gpkg_file)
                    total_count += 1
                    if ret_code == RetCode.EXPORT_OK:
                        log_file.write(f'{padded_gpkg_file} CSV export OK  ({output_filename})\n')
                        QgsMessageLog.logMessage(f'{padded_gpkg_file} CSV export OK ({output_filename})' ,self.title_export_gpkg_to_csv, Qgis.Info)
                    else:
                        log_file.write(f'{padded_gpkg_file} Error during CSV export: {error_msg}\n')
                        QgsMessageLog.logMessage(f'{padded_gpkg_file} Error during CSV export: {error_msg})' ,self.title_export_gpkg_to_csv, Qgis.Warning)
                        failed += 1

                    log_file.flush()
                    task.setProgress((total_count / file_count) * 100)

                task.setProgress(100)
                return total_count, failed

        except Exception as err:
            print(f'export_gpkg_to_csv() Exception: {err}')
            QgsMessageLog.logMessage(f'Error: {err}', self.title_export_gpkg_to_csv, Qgis.Critical)
            raise
        finally:
            if log_file is not None:
                log_file.close()

    def export_gpkg_to_csv_done(self, exception:Exception, result:tuple[int, int]=None) -> None:
        """GPKG export to CSV done
        Exception is not None if self.task_export_gpkg_to_csv raises an exception.
        result is the return value of self.task_export_gpkg_to_csv."""
        try:
            msg_box = QMessageBox()
            msg_box.setWindowTitle(self.tr('Result from:') + ' ' + f'{self.title_export_gpkg_to_csv}')
            msg_box.setStandardButtons(QMessageBox.Ok)
            if result is None:
                text = f'Error during runnig of "{self.title_export_gpkg_to_csv}" Exception: {exception}'
                msg_box.setText(text)
                msg_box.setIcon(QMessageBox.Critical)
            else:
                total_count, failed = result
                if failed == 0:
                    text = self.tr("Successfully converted all _COUNT_ Intrasis GeoPackages to CSV.")
                    text = text.replace('_COUNT_', f'{total_count}')
                    msg_box.setIcon(QMessageBox.Information)
                elif failed > 0:
                    text = self.tr("Have tried to convert _COUNT_ALL_ Intrasis GeoPackages to CSV, _COUNT_ failed.")
                    text = text.replace('_COUNT_ALL_', f'{total_count}')
                    text = text.replace('_COUNT_', f'{failed}')
                    msg_box.setIcon(QMessageBox.Warning)
                msg_box.setText(text)
            msg_box.exec()
            del globals()['Task_export_gpkg_to_csv']
        except Exception as err:
            traceback.print_exc()
            print(f'export_gpkg_to_csv_done() Exception: {err}')

    def on_export_simplified_gpkg(self) -> None:
        """Export simplified version of GPKG"""
        try:
            s = QgsSettings()
            export_folder = s.value("SwedigarchGeotools/exportFolder", "")
            print(f'start export_folder: {export_folder}')

            options = QtWidgets.QFileDialog.Options()
            gpkg_path = QtWidgets.QFileDialog.getOpenFileName(None, self.tr('Select Intrasis GPKG to export to simplified version'),
                                                              export_folder, self.tr('GeoPackge (*.gpkg);;All files (*.*)'), '*.gpkg', options)[0]
            if gpkg_path == '':
                return # Canceled

            ok, error_msg = export_simplified_gpkg(gpkg_path)
            msg_box = QMessageBox()
            msg_box.setWindowTitle(self.tr('Result from:') + ' ' + self.title_export_simplified_gpkg)
            msg_box.setStandardButtons(QMessageBox.Ok)
            if ok:
                text = self.tr('Successfully converted Intrasis GeoPackage to simplified version')
                msg_box.setIcon(QMessageBox.Information)
            else:
                text = f'Error during runnig of "{self.title_export_simplified_gpkg}" Error: {error_msg}'
                msg_box.setIcon(QMessageBox.Critical)
            msg_box.setText(text)
            msg_box.exec()

        except Exception as err:
            print(f'export_gpkg_to_csv() Exception: {err}')

    def show_about(self) -> None:
        """Display the about message box"""
        # To add icon to About dialog
        bogus = QWidget(iface.mainWindow())
        bogus.setWindowIcon(QIcon(":/plugins/swedigarch_plugin/assets/svedigark.svg"))

        # Fetch metadata infomation
        cfg = configparser.ConfigParser()
        cfg.read(Path(__file__).parent / "metadata.txt")

        name = cfg.get("general", "name")
        version = cfg.get("general", "version")
        repository = cfg.get("general", "repository")
        tracker = cfg.get("general", "tracker")
        homepage = cfg.get("general", "homepage")
        author = cfg.get("general", "author")
        #about = cfg.get("general", "about")

        QMessageBox.about(
            bogus,
            self.tr("About {0}").format(name),
            f'Swedigarch Geotools version {version}, Copyright (C) 2023 Swedigarch<br>'
            'Swedigarch Geotools comes with ABSOLUTELY NO WARRANTY<br>'
            'Swedigarch Geotools is free software, and you are welcome to redistribute it<br>'
            ' under certain conditions.<br><br>'
            f'<b>Version</b> {version}<br>'
            f'<b>{self.tr("Source code")}</b> : <a href={repository}>{repository}</a><br>'
            f'<b>{self.tr("Report issues")}</b> : <a href={tracker}/issues>{tracker}</a><br>'
            f'<b>{self.tr("Documentation")}</b> : <a href={homepage}>{homepage}</a><br><br>'
            f'<b>{self.tr("Author")}</b> : {author}</a>'
        )
        bogus.deleteLater()
