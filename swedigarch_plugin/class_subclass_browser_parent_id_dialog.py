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
import copy
from qgis.core import Qgis, QgsMessageLog
from qgis.PyQt import uic, QtWidgets
from PyQt5 import QtCore
from PyQt5.QtWidgets import QDialogButtonBox, QMenu, QAction, QTreeWidgetItem
#from . import browse_relations_utils as BrowseRelationsUtils
#from .browse_relations_utils_classes import IntrasisTreeWidgetItem

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'class_subclass_browser_parent_id_dialog.ui'))

class ClassSubclassBrowserParentIdDialog(QtWidgets.QDialog, FORM_CLASS):
    """ClassSubclassBrowserParentIdDialog dialog. Dialog to generate Parent Id to objects without geometry"""
    #def __init__(self, parent=None, top_level_intrasis_tree_item:IntrasisTreeWidgetItem=None, gpkg_path:str = None, win_titel:str = ""):
    def __init__(self, parent_classes, grandparent_classes, greatgrandparent_classes):
        """ClassSubclassBrowserParentIdDialog Constructor"""
        #super(ClassSubclassBrowserParentIdDialog, self).__init__(parent)
        super(ClassSubclassBrowserParentIdDialog, self).__init__()
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.parent_classes = parent_classes
        self.grandparent_classes = grandparent_classes
        self.greatgrandparent_classes = greatgrandparent_classes
        '''self.top_level_item = top_level_intrasis_tree_item
        self.final_top_level_item = None
        self.button_clicked = None
        self.gpkg_path = gpkg_path
        self.win_titel = win_titel
        self.flattened_layers = False
        self.hierarchical_layers = True
        self.relations_below_context_menu = self.create_context_menu_remove_tree_node()
        self.last_removed_nodes = []

        self.tree_widget_intrasis_relations.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tree_widget_intrasis_relations.customContextMenuRequested.connect(self.show_context_menu)
        self.tree_widget_intrasis_relations.itemExpanded.connect(self.on_tree_widget_item_expanded)
        '''

        self.button_box_generate_parent_id.button(QtWidgets.QDialogButtonBox.Cancel).setText(self.tr("Cancel"))
        #self.button_box_generate_parent_id.accepted.connect(self.on_ok)
        #self.button_box_generate_parent_id.rejected.connect(self.on_cancel)

        '''self.check_box_hierarchical_layers.stateChanged.connect(self.on_check_box_hierarchical_create_layers_state_changed)
        self.check_box_flat_layers.stateChanged.connect(self.on_check_box_flat_create_layers_state_changed)
        '''

        #self.push_button_undo.clicked.connect(self.on_undo_clicked)
        self.init_gui()

    def showEvent(self, event):
        """DialogShow event"""
        super(ClassSubclassBrowserParentIdDialog, self).showEvent(event)
        
    def closeEvent(self, event):
        """The close dialog event (QCloseEvent)"""
        self.button_clicked = QDialogButtonBox.Cancel

    #def init_data_and_gui(self):
    #    """Load data and init gui"""
    #    self.init_gui()
    #    #self.set_ok_button_enabled_state()

    def update_combobox_class(self) -> None:
        '''Update and changes Class(es) in combobox'''
        self.combo_box_parentlayer.clear()
        self.combo_box_grandparentlayer.clear()
        self.combo_box_greatgrandparentlayer.clear()
        class_items = self.parent_classes['Class.SubClass'].tolist()
        #class_items = ['kalle','anka']#self.archeological_classes[1]
        class_items.insert(0,'-')
        self.combo_box_parentlayer.addItems(class_items)
        self.combo_box_grandparentlayer.addItems(self.grandparent_classes['Class.SubClass'].tolist())
        self.combo_box_greatgrandparentlayer.addItems(self.greatgrandparent_classes['Class.SubClass'].tolist())

    def on_ok(self):
        """Selection of tree nodes done"""
        #self.final_top_level_item = copy.deepcopy(self.top_level_item)
        #self.button_clicked = QDialogButtonBox.Ok
        print("Ok clicked")
        self.accept()

    def on_cancel(self):
        """Handle cancel clicked - close dialog"""
        print("Dialog closed")
        self.close()
    
    #def set_ok_button_enabled_state(self):
        """Disable the Ok button if none of the flattened layers and hierarchical layers checkboxes is checked"""
        #enable_ok_button = self.check_box_hierarchical_layers.isChecked() or self.check_box_flat_layers.isChecked()
        #ok_button = self.button_box.button(QDialogButtonBox.Ok)
    #    ok_button.setEnabled(enable_ok_button)

    def init_gui(self):
        """Initialize gui components and load data"""
        print("dialog open")
        self.update_combobox_class()
        '''if self.top_level_item is None:
            QgsMessageLog.logMessage("Failed to display tree", BrowseRelationsUtils.MESSAGE_CATEGORY, Qgis.Critical)
            return
        
        self.setWindowTitle(f"{self.win_titel} - IntrasisId #{self.top_level_item.intrasis_item.intrasis_id}")
        
        self.push_button_undo.setEnabled(False)

        self.check_box_flat_layers.setChecked(self.flattened_layers)
        self.check_box_hierarchical_layers.setChecked(self.hierarchical_layers)
        
        BrowseRelationsUtils.set_tree_widget_header_size_mode(self.tree_widget_intrasis_relations)

        self.tree_widget_intrasis_relations.addTopLevelItem(self.top_level_item)
        self.set_child_indicator_policy()
        BrowseRelationsUtils.expand_tree_widget_item(self.tree_widget_intrasis_relations, self.top_level_item)
        '''
