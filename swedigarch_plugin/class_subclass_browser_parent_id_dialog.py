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
#import copy
#from qgis.core import Qgis, QgsMessageLog
from qgis.PyQt import uic, QtWidgets
#from PyQt5 import QtCore
#from PyQt5.QtWidgets import QDialogButtonBox, QMenu, QAction, QTreeWidgetItem
#from PyQt5.QtCore import QVariant ,QAbstractTableModel, QModelIndex, Qt
from PyQt5.QtCore import Qt
# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'class_subclass_browser_parent_id_dialog.ui'))

class ClassSubclassBrowserParentIdDialog(QtWidgets.QDialog, FORM_CLASS):
    """ClassSubclassBrowserParentIdDialog dialog. Dialog to generate Parent Id to objects without geometry"""
    def __init__(self, parent_dialog_df, child_class_string):
        """ClassSubclassBrowserParentIdDialog Constructor"""
        super(ClassSubclassBrowserParentIdDialog, self).__init__()
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.parent_dialog_df = parent_dialog_df
        self.child_class_string = child_class_string
        self.button_box_generate_parent_id.button(QtWidgets.QDialogButtonBox.Cancel).setText(self.tr("Cancel"))
        self.button_box_generate_parent_id.button(QtWidgets.QDialogButtonBox.Ok).setText(self.tr("Create ParentId Table"))
        self.button_box_generate_parent_id.accepted.connect(self.on_ok)
        self.check_box_activate_grand_parent.stateChanged.connect(self.on_activate_grand_parent)
        self.check_box_activate_great_parent.stateChanged.connect(self.on_activate_great_parent)
        self.settings = []
        self.layers_chosen = []
        self.combo_box_parentlayer.currentIndexChanged.connect(self.update_combo_box_grandparentlayer)
        self.combo_box_grandparentlayer.currentIndexChanged.connect(self.update_combo_box_greatgrandparentlayer)
        self.check_box_activate_grand_parent.stateChanged.connect(self.update_check_box_activate_great_parent)
        self.init_gui()

    def on_activate_grand_parent(self, state):
        """When checked create add attributes parent id and grand parent id to objects without geometry"""
        if state == Qt.Checked:
            self.combo_box_grandparentlayer.setEnabled(True)
        else:
            self.combo_box_grandparentlayer.setEnabled(False)

    def on_activate_great_parent(self, state):
        """When checked create add attributes parent id and grand parent id to objects without geometry"""
        if state == Qt.Checked:
            self.combo_box_greatgrandparentlayer.setEnabled(True)
        else:
            self.combo_box_greatgrandparentlayer.setEnabled(False)

    def update_check_box_activate_great_parent(self):
        '''checkbox logics'''
        if self.check_box_activate_grand_parent.isChecked():
            self.check_box_activate_great_parent.setEnabled(True)
        else:
            self.check_box_activate_great_parent.setChecked(False)
            self.check_box_activate_great_parent.setEnabled(False)


    def update_combobox_class(self) -> None:
        '''Update and changes Class(es) in combobox'''
        self.combo_box_parentlayer.clear()
        self.combo_box_grandparentlayer.clear()
        self.combo_box_greatgrandparentlayer.clear()
        class_items = self.parent_dialog_df['parent_class'].unique().tolist()
        self.combo_box_parentlayer.addItems(class_items)

    def update_combo_box_grandparentlayer(self):
        self.combo_box_grandparentlayer.clear()
        selected_category = self.combo_box_parentlayer.currentText()
        filtered_df = self.parent_dialog_df[self.parent_dialog_df['parent_class'] == selected_category]
        self.combo_box_grandparentlayer.addItems(filtered_df['grand_parent_class'].unique())
        self.update_combo_box_greatgrandparentlayer()  # Reset combo3

    def update_combo_box_greatgrandparentlayer(self):
        self.combo_box_greatgrandparentlayer.clear()
        selected_type = self.combo_box_grandparentlayer.currentText()
        filtered_df = self.parent_dialog_df[self.parent_dialog_df['grand_parent_class'] == selected_type]
        self.combo_box_greatgrandparentlayer.addItems(filtered_df['great_grand_parent_class'].unique())

    def on_ok(self):
        """Selection of parent layers done"""
        self.get_values()
        #print(self.settings)
        self.accept()
        self.close()

    def on_cancel(self):
        """Handle cancel clicked - close dialog"""
        print("Dialog closed")
        self.close()

    def init_gui(self):
        """Initialize gui components and load data"""
        print("dialog open")
        self.update_combobox_class()
        self.combo_box_grandparentlayer.setEnabled(False)
        self.combo_box_greatgrandparentlayer.setEnabled(False)
        self.check_box_activate_great_parent.setChecked(False)
        self.check_box_activate_great_parent.setEnabled(False)
        self.label.setText(f"Select {self.child_class_string} Parent Layer")

    def get_values(self):
        self.settings = [self.combo_box_parentlayer.currentText(),'','']
        if(self.check_box_activate_grand_parent.isChecked() and self.check_box_activate_great_parent.isChecked()==False):
            self.settings = [self.combo_box_parentlayer.currentText(), self.combo_box_grandparentlayer.currentText(), '']
        if(self.check_box_activate_grand_parent.isChecked() and self.check_box_activate_great_parent.isChecked()):  
            self.settings = [self.combo_box_parentlayer.currentText(), self.combo_box_grandparentlayer.currentText(), self.combo_box_greatgrandparentlayer.currentText()]
