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
import traceback
import numpy as np
from . import utils as Utils
from qgis.PyQt import (uic, QtWidgets)
from PyQt5.QtCore import (Qt, QTimer)

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'select_geo_package_dalog.ui'))

class SelectGeoPackageDialog(QtWidgets.QDialog, FORM_CLASS):
    """Init dialog"""
    def __init__(self, title=None, parent=None, only_gpkg_with_selected_features = False):
        """Constructor."""
        super(SelectGeoPackageDialog, self).__init__(parent)
        self.setupUi(self)
        if title is not None:
            self.setWindowTitle(title)
        self.setWindowFlags(Qt.Window |
                            Qt.CustomizeWindowHint |
                            Qt.WindowTitleHint)
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setText(self.tr("Select"))
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        self.button_box.button(QtWidgets.QDialogButtonBox.Cancel).setText(self.tr("Cancel"))
        self.button_box.accepted.connect(self.on_ok)
        self.button_box.rejected.connect(self.on_cancel)
        self.lwGeoPackages.selectionModel().selectionChanged.connect(self.selection_ok)
        self.selected_geo_package = None
        self.tmr_close = QTimer(self)
        self.tmr_close.setInterval(200)
        self.tmr_close.timeout.connect(self.tmr_close_timeout)
        self.only_gpkg_with_selected_features = only_gpkg_with_selected_features
        self.dialog_init()

    # pylint: disable=invalid-name
    def dialog_init(self):
        """DialogShow event, returns selected databases to top list."""
        gpkg_files = None
        if self.only_gpkg_with_selected_features:
            gpkg_files = Utils.find_geo_packages_from_selected_features()
        else:
            gpkg_files = Utils.find_geo_packages()
        
        print(f'gpkg_files.count: {len(gpkg_files)}')
        print(f'gpkg_files: {gpkg_files}')
        # Sort list of GeoPackages by the number of loaded items they have (descending order)
        keys = list(gpkg_files.keys())
        values = list(gpkg_files.values())
        sorted_value_index = np.argsort(values)[::-1]
        sorted_dic = {keys[i]: values[i] for i in sorted_value_index}
        for geo_pack, count in sorted_dic.items():
            items_text = self.tr("Items loaded")
            if self.only_gpkg_with_selected_features:
                items_text = self.tr("Selected objects")
            item = f"{geo_pack}  ({items_text}: {count})"
            if Utils.is_intrasis_gpkg_export(geo_pack) is True:
                self.lwGeoPackages.addItem(item)
        # Select the fist in the list
        self.lwGeoPackages.setCurrentRow(0)
        if self.lwGeoPackages.count() == 1:
            # We only have one GeoPackages left after filtering.
            # So select it and close dialog.
            self.tmr_close.start()

    def tmr_close_timeout(self):
        """Auto close timeout function"""
        self.on_ok()

    def selection_ok(self):
        """Check if Select button can be enabled"""
        sel_count = len(self.lwGeoPackages.selectedItems())
        #print(f"selection_ok() count: {self.lwGeoPackages.count()} selected count: {sel_count}")
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(sel_count == 1)

    def on_ok(self):
        """Selection of GeoPackage done"""
        if len(self.lwGeoPackages.selectedItems()) > 0:
            selected_item = self.lwGeoPackages.selectedItems()[0].text()
            parts = selected_item.split("  ")
            self.selected_geo_package = parts[0]
        self.accept()

    def on_cancel(self):
        """Dialog canceled"""
        self.close()
