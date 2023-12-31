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
from typing import Callable
import numpy as np
# Import the code for the dialog
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from PyQt5 import QtWidgets
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QStyle, QWidget
from PyQt5.QtWidgets import QFileDialog
from qgis.utils import iface
from qgis.core import QgsSettings
from osgeo import ogr
from .swedigarch_export_dialog import SwedigarchExportDialog
from .intrasis_analysis_browse_relations import IntrasisAnalysisBrowseRelationsDialog
from .intrasis_analysis_browse_tables import IntrasisAnalysisBrowseTablesDialog
from .select_geo_package_dalog import SelectGeoPackageDialog
from .export_geopackage_to_csv import export_geopackage_to_csv
from .resources import * # This row is needed for the ToolBar button to get its icon.
from . import utils as Utils
from .constant import RetCode

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

    def run_export_dialog(self) -> None:
        """Run method that performs all the real work (Intrasis DB Manager)"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
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
        if self.first_start_browse_relations == True:
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
        if self.first_start_browse_tables == True:
            self.first_start = True
            self.first_start_browse_tables = False
            self.dlg_browse_tables = IntrasisAnalysisBrowseTablesDialog()
        else:
            self.dlg_browse_tables.activateWindow()

        intrasis_gpkg_loaded = self.dlg_browse_tables.check_if_intrasis_geopackage_is_loaded()
        if intrasis_gpkg_loaded == False:
            self.dlg_browse_tables.show_messagebox_no_loaded_gpkg()
            return
        user_select_klicked = self.dlg_browse_tables.select_and_activate_intrasis_geopackage()
        if user_select_klicked == False:
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
