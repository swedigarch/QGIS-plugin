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
from . import browse_relations_utils as BrowseRelationsUtils
from .browse_relations_utils_classes import IntrasisTreeWidgetItem

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'select_tree_nodes_dialog.ui'))

class SelectTreeNodesDialog(QtWidgets.QDialog, FORM_CLASS):
    """SelectTreeNodesDialog dialog. Dialog to remove tree nodes from a QTreeWidget"""
    def __init__(self, parent=None, top_level_intrasis_tree_item:IntrasisTreeWidgetItem=None, gpkg_path:str = None, win_titel:str = ""):
        """SelectTreeNodesDialog Constructor"""
        super(SelectTreeNodesDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.top_level_item = top_level_intrasis_tree_item
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

        self.button_box.button(QtWidgets.QDialogButtonBox.Cancel).setText(self.tr("Cancel"))
        self.button_box.accepted.connect(self.on_ok)
        self.button_box.rejected.connect(self.on_cancel)

        self.check_box_hierarchical_layers.stateChanged.connect(self.on_check_box_hierarchical_create_layers_state_changed)
        self.check_box_flat_layers.stateChanged.connect(self.on_check_box_flat_create_layers_state_changed)

        self.push_button_undo.clicked.connect(self.on_undo_clicked)

    def showEvent(self, event):
        """DialogShow event"""
        super(SelectTreeNodesDialog, self).showEvent(event)
        
    def closeEvent(self, event):
        """The close dialog event (QCloseEvent)"""
        self.button_clicked = QDialogButtonBox.Cancel

    def init_data_and_gui(self):
        """Load data and init gui"""
        self.init_gui()
        self.set_ok_button_enabled_state()
        
    def on_undo_clicked(self):
        """Add all nodes in the 'self.last_removed_nodes' list to the their parent nodes in the tree widget"""
        if len(self.last_removed_nodes) == 0:
            return
        
        for row in self.last_removed_nodes:
            parent_node = row[0]
            child_node = row[1]
            parent_node.addChild(child_node)
        
        self.tree_widget_intrasis_relations.sortItems(0, QtCore.Qt.AscendingOrder)
        self.last_removed_nodes = []
        self.push_button_undo.setEnabled(False)
            
    def on_check_box_flat_create_layers_state_changed(self, state):
        """Handle checked state changed for flattened layers checkbox"""
        self.flattened_layers = (state == QtCore.Qt.CheckState.Checked)
        self.set_ok_button_enabled_state()

    def on_check_box_hierarchical_create_layers_state_changed(self, state):
        """Handle checked state changed for flattened layers checkbox"""
        self.hierarchical_layers = (state == QtCore.Qt.CheckState.Checked)
        self.set_ok_button_enabled_state()
        
    def on_ok(self):
        """Selection of tree nodes done"""
        self.final_top_level_item = copy.deepcopy(self.top_level_item)
        self.button_clicked = QDialogButtonBox.Ok
        self.accept()

    def on_cancel(self):
        """Handle cancel clicked - close dialog"""
        self.close()
    
    def set_ok_button_enabled_state(self):
        """Disable the Ok button if none of the flattened layers and hierarchical layers checkboxes is checked"""
        enable_ok_button = self.check_box_hierarchical_layers.isChecked() or self.check_box_flat_layers.isChecked()
        ok_button = self.button_box.button(QDialogButtonBox.Ok)
        ok_button.setEnabled(enable_ok_button)

    def set_child_indicator_policy(self):
        """Make sure items that have unloaded child nodes have an expand arrow"""
        stack = [self.top_level_item]

        while stack:
            # Get next node to process
            current_node = stack.pop()
            if current_node.childCount() == 0:
                if current_node.intrasis_item.has_unloaded_related_below:
                        # Show expand arrow in tree even though this node has no children
                        current_node.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
            
            for i in range(0, current_node.childCount()):
                child_item = current_node.child(i)
                stack.append(child_item)

    def on_tree_widget_item_expanded(self, item):
        """Handler for when expand item is clicked in the relations below tree widget. Unloaded related below items are loaded"""
        if item.intrasis_item.has_unloaded_related_below: #If the item has unloaded child nodes, add them (3 tree levels at a time)
            BrowseRelationsUtils.add_objects_below(self.gpkg_path, item, 3)
            self.tree_widget_intrasis_relations.sortItems(0, QtCore.Qt.AscendingOrder)

    def init_gui(self):
        """Initialize gui components and load data"""
        if self.top_level_item is None:
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
    
    def create_context_menu_remove_tree_node(self):
        """Create a context menu for removing selected nodes"""
        context_menu = QMenu(self.tree_widget_intrasis_relations)

        action_add_to_selection = QAction(self.tr("Remove"), self.tree_widget_intrasis_relations)
        action_add_to_selection.triggered.connect(lambda: self.remove_selected_tree_nodes(self.tree_widget_intrasis_relations.selectedItems()))
        context_menu.addAction(action_add_to_selection)

        return context_menu

    def remove_selected_tree_nodes(self, selected_tree_items):
        """Remove selected tree nodes (top level tree node will not be removed)"""
        if len(selected_tree_items) == 0:
            return
        
        self.last_removed_nodes = []
        for item in selected_tree_items:
            if item == self.top_level_item or item.parent() is None:
                QgsMessageLog.logMessage("Cannot remove top level tree node", BrowseRelationsUtils.MESSAGE_CATEGORY, Qgis.Warning)
            else:
                index = item.parent().indexOfChild(item)
                self.last_removed_nodes.append((item.parent(), item.parent().takeChild(index)))
        
        self.push_button_undo.setEnabled(True)

    def show_context_menu(self, position):
        """Show context_menu for tree widget"""
        global_pos = self.tree_widget_intrasis_relations.viewport().mapToGlobal(position)
        self.relations_below_context_menu.exec_(global_pos)