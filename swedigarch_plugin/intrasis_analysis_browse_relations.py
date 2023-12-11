# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Swedigarch plugin is a tool for field archaeologist to transform their
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

import time
import os
import copy
from typing import Tuple
from qgis.core import QgsSettings, QgsMessageLog, Qgis, QgsProject, QgsLayerTreeGroup, QgsApplication
from qgis.PyQt import uic, QtWidgets
from PyQt5.QtGui import QCursor
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QTableWidgetItem, QHeaderView, QTreeWidgetItem, QMessageBox, QDialogButtonBox, QAction, QMenu, QApplication, QTreeWidget, QTableWidget
from . import utils as Utils
from . import browse_relations_utils as BrowseRelationsUtils
from .browse_relations_utils_classes import IntrasisTreeWidgetItem, LayerGroupTreeNode
from .select_geo_package_dalog import SelectGeoPackageDialog
from .select_tree_nodes_dialog import SelectTreeNodesDialog
from .help_dialog import HelpDialog
from . import create_layers_from_all_child_nodes_task as CreateLayersTaskModule

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'intrasis_analysis_browse_relations_dialog.ui'))

class IntrasisAnalysisBrowseRelationsDialog(QtWidgets.QDialog, FORM_CLASS):
    """Swedigarch DB Relationship Browser Dialog"""
    def __init__(self, parent=None):
        """Swedigarch DB Relationship Browser Dialog Constructor"""
        super(IntrasisAnalysisBrowseRelationsDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.selected_intrasis_item = None
        self.selected_features = []
        self.intrasis_item_dict = {}
        self.class_subclass_attributes = {}
        self.gpkg_path = ""
        self.active_gpkg_name = ""
        self.relations_above_context_menu = self.create_context_menu_add_to_selection(self.tree_widget_relations_above)
        self.relations_below_context_menu = self.create_context_menu_add_to_selection(self.tree_widget_relations_below)

        self.tree_widget_relations_above.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_widget_relations_above.customContextMenuRequested.connect(self.show_context_menu_relations_above)
        self.tree_widget_relations_below.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_widget_relations_below.customContextMenuRequested.connect(self.show_context_menu_relations_below)

        self.combo_box_intrasis_id.currentTextChanged.connect(self.on_intrasis_id_combobox_text_change)
        
        self.tree_widget_relations_above.currentItemChanged.connect(self.on_relations_above_tree_widget_current_item_changed)
        self.tree_widget_relations_below.currentItemChanged.connect(self.on_relations_below_tree_widget_current_item_changed)
        self.tree_widget_relations_below.itemExpanded.connect(self.on_relations_below_tree_widget_item_expanded)
        self.tree_widget_relations_above.itemExpanded.connect(self.on_relations_above_tree_widget_item_expanded)
        self.tree_widget_relations_above.itemCollapsed.connect(self.on_relations_above_tree_widget_item_collapsed)

        self.push_button_create_layer_closest_parents.clicked.connect(self.on_create_layer_from_closest_parents_clicked)
        self.push_button_create_layer_all_children.clicked.connect(self.on_create_layer_from_all_children_clicked)
        self.push_button_refresh_selection.clicked.connect(self.on_refresh_selection_clicked)

        self.check_box_hierarchical_layers.stateChanged.connect(self.on_check_box_create_layers_state_changed)
        self.check_box_flat_layers.stateChanged.connect(self.on_check_box_create_layers_state_changed)

        self.button_box.helpRequested.connect(self.on_help_clicked)

        self.button_box.button(QDialogButtonBox.StandardButton.Close).setText(self.tr("Close"))
        self.button_box.button(QDialogButtonBox.StandardButton.Help).setText(self.tr("Help"))

    def on_help_clicked(self):
        """Show Help dialog"""
        HelpDialog.show_help("RelationsDialog")

    def on_check_box_create_layers_state_changed(self, state):
        """Enable push button create layers from all children only if at least one of the flattened or hierarchical checkboxes is checked"""
        enable_crete_layers_from_all_children = self.check_box_hierarchical_layers.isChecked() or self.check_box_flat_layers.isChecked()
        self.push_button_create_layer_all_children.setEnabled(enable_crete_layers_from_all_children)
    
    def on_refresh_selection_clicked(self):
        """Handle refresh selection button click"""
        self.refresh_selected_features_and_active_geopackage()
        
    def create_context_menu_add_to_selection(self, tree_widget:QTreeWidget) -> QMenu:
        """Create a context menu for setting selected item as current object"""
        context_menu = QMenu(tree_widget)

        action_add_to_selection = QAction(self.tr("Set as current object"), tree_widget)
        action_add_to_selection.triggered.connect(lambda: self.on_add_tree_item_to_selected_clicked(tree_widget.currentItem()))
        context_menu.addAction(action_add_to_selection)

        return context_menu

    def on_add_tree_item_to_selected_clicked(self, item:QTreeWidgetItem):
        """Add the selected QTreeWidgetItem to the combobox and set as current object in GUI"""
        if item:
            if (item.intrasis_item.intrasis_id in self.intrasis_item_dict): # selected item is already in the combobox - make sure it is selected
                self.combo_box_intrasis_id.setCurrentText(self.get_combobox_text_for_intrasis_id(item.intrasis_item.intrasis_id))
                return

            # The id is not already added: clear gui and add the intrasis_id list to the combobox
            self.intrasis_item_dict.update({item.intrasis_item.intrasis_id: item.intrasis_item})
            self.clear_data_widgets()
            self.init_intrasis_id_combo_box(item.intrasis_item.intrasis_id)

    def show_context_menu_relations_above(self, position: QPoint):
        """Show context menu for the relations above tree widget"""
        self.show_context_menu(position, self.tree_widget_relations_above, self.relations_above_context_menu)
    
    def show_context_menu_relations_below(self, position: QPoint):
        """Show context menu for the relations below tree widget"""
        self.show_context_menu(position, self.tree_widget_relations_below, self.relations_below_context_menu)

    def show_context_menu(self, position: QPoint, widget:QTreeWidget, context_menu:QMenu):
        """Show 'context_menu' QMenu for 'widget' QTreeWidget"""
        global_pos = widget.viewport().mapToGlobal(position)
        context_menu.exec_(global_pos)

    def on_intrasis_id_combobox_text_change(self):
        """Handle new intrasis_id is selected in the combobox"""
        if self.combo_box_intrasis_id.currentText() == "":
            return

        selected_text = self.combo_box_intrasis_id.currentText()
        selected_intrasis_id = int(selected_text.split()[0])

        self.selected_intrasis_item = self.intrasis_item_dict.get(selected_intrasis_id)

        self.clear_data_widgets()
        self.load_data_to_current_object_table()
        self.set_current_object_labels()
        self.load_one_level_into_relations_above_tree_widget()
        self.load_data_into_relations_below_tree_widget()
        self.set_enabled_state_on_create_layer_buttons()

    def set_enabled_state_on_create_layer_buttons(self):
        """Set creaate layer buttons enabled or disabled based on if there is any data in the closest parents and children tree widgets"""
        self.push_button_create_layer_closest_parents.setEnabled(self.tree_widget_relations_above.topLevelItemCount() > 0)

        relations_below_has_data = self.tree_widget_relations_below.topLevelItemCount() > 0
        checkbox_create_layer_from_children_checked = self.check_box_hierarchical_layers.isChecked() or self.check_box_flat_layers.isChecked()
        self.push_button_create_layer_all_children.setEnabled(relations_below_has_data and checkbox_create_layer_from_children_checked)
        self.check_box_hierarchical_layers.setEnabled(relations_below_has_data)
        self.check_box_flat_layers.setEnabled(relations_below_has_data)

    def on_relations_above_tree_widget_current_item_changed(self, item: QTreeWidgetItem, prev_item:QTreeWidgetItem):
        """Handler for when new item selected in the relations above tree widget"""
        if item:
            self.load_data_into_widgets_relations_above(item)
    
    def on_relations_below_tree_widget_item_expanded(self, item:QTreeWidgetItem):
        """Handler for when item expanded in the relations below tree widget. If the item has unloaded 'related below' new child nodes will be loaded"""
        if item.intrasis_item.has_unloaded_related_below: #If the item has unloaded child nodes, add them (3 tree levels at a time)
            BrowseRelationsUtils.add_objects_below(self.gpkg_path, item, 3)
            self.tree_widget_relations_below.sortItems(0, Qt.AscendingOrder)
    
    def on_relations_above_tree_widget_item_collapsed(self, item:QTreeWidgetItem):
        """Handler for when expanded item is collapsed in the relations above tree widget. All top level items will be collapsed if one of them is collapsed"""
        tree_widget = item.treeWidget()
        for i in range(0, tree_widget.topLevelItemCount()):
            top_item = tree_widget.topLevelItem(i)
            tree_widget.collapseItem(top_item)

    def on_relations_above_tree_widget_item_expanded(self, item:QTreeWidgetItem):
        """Handler for when item is expanded in the relations above tree widget.  All top level items will be collapsed if one of them is expanded"""
        tree_widget = item.treeWidget()
        for i in range(0, tree_widget.topLevelItemCount()):
            top_item = tree_widget.topLevelItem(i)
            tree_widget.expandItem(top_item)

    def on_relations_below_tree_widget_current_item_changed(self, item:QTreeWidgetItem, prev_item:QTreeWidgetItem):
        """Handler for when an item is clicked in the relations below tree widget"""
        if item:
            self.load_data_into_widgets_relations_below(item)

    def on_create_layer_from_closest_parents_clicked(self):
        """Handler for when create layer from closest parents is clicked"""
        print(f"Create layers from closest parents for IntrasiId {self.selected_intrasis_item.intrasis_id} started.")
        layer_group_name = f"Relations.{self.active_gpkg_name}.IntrasisId_{self.selected_intrasis_item.intrasis_id}.Closest_Parents"
        self.create_layers_from_closest_parents(layer_group_name)
        
    def on_create_layer_from_all_children_clicked(self):
        """Handler for when create layer from children is clicked"""
        print(f"Create layers from children for IntrasiId {self.selected_intrasis_item.intrasis_id} started.")
        layer_group_name_base = f"Relations.{self.active_gpkg_name}.IntrasisId_{self.selected_intrasis_item.intrasis_id}.Children"
        self.create_layers_from_children(layer_group_name_base)

    def showEvent(self, event):
        """DialogShow event, returns selected databases to top list."""
        super(IntrasisAnalysisBrowseRelationsDialog, self).showEvent(event)
        
        settings = QgsSettings()
        point = settings.value("SwedigarchPlugin/dialog_position", None)
        if point is not None:
            self.move(point)

        # Check that there is a list of selected features
        if not self.selected_features:
            return
        
    def closeEvent(self, event):
        """The close dialog event (QCloseEvent)"""
        point = self.pos()
        settings = QgsSettings()
        settings.setValue("SwedigarchPlugin/dialog_position", point)

    def init_data_and_gui(self):
        """Intialize the gui with loaded 'self.selected_features'"""
        # Check that there is a list of selected features
        if not self.selected_features:
            return
        
        self.init_gui()
        self.set_enabled_state_on_create_layer_buttons()

    def init_gui(self):
        """Set up gui components and fill with data"""
        self.clear_gui()

        self.set_active_geopackage_name()

        BrowseRelationsUtils.set_tree_widget_header_size_mode(self.tree_widget_relations_below)
        BrowseRelationsUtils.set_tree_widget_header_size_mode(self.tree_widget_relations_above)

        # Get list of intrasis items from selected features and init combobox
        self.intrasis_item_dict = BrowseRelationsUtils.get_intrasis_item_dict_for_features(self.gpkg_path, self.selected_features)
        self.init_intrasis_id_combo_box()
        
    def init_selected_features_and_active_geopackage(self) -> Tuple[bool, bool]:
        """Get selected features and active geopackage, returns if there are any selected features and whether the user canceled opening the dialog"""
        features, active_gpkg_path, user_canceled = self.get_selected_features_and_init_active_geopackage()
        
        self.gpkg_path = active_gpkg_path
        self.selected_features = features
        
        features_selected = False
        if features:
            features_selected = True
        
        return features_selected, user_canceled
    
    def refresh_selected_features_and_active_geopackage(self):
        """Refresh selected features and active geopackage"""
        features, active_gpkg_path, user_canceled = self.get_selected_features_and_init_active_geopackage()
        
        if user_canceled:
            QgsMessageLog.logMessage("User canceled refresh selection", BrowseRelationsUtils.MESSAGE_CATEGORY, Qgis.Info)
            return
        
        if not features:
            QgsMessageLog.logMessage("No features selected - refresh selection aborted", BrowseRelationsUtils.MESSAGE_CATEGORY, Qgis.Info)
            self.show_messagebox_no_selected_objects()
            return
        
        self.gpkg_path = active_gpkg_path
        self.selected_features = features
        self.init_gui()
        QgsMessageLog.logMessage("Refresh selection done", BrowseRelationsUtils.MESSAGE_CATEGORY, Qgis.Info)

    def get_selected_features_and_init_active_geopackage(self) -> Tuple[list, str, bool]:
        """Returns a list of selected features belonging to the selected/active geopackage, and path to selected geopackage"""
        features = []
        user_canceled = False
        selected_features, gpkg_paths = Utils.get_all_selected_features_and_gpkg_paths()
        active_geopackage_path = None

        if not selected_features:
            return selected_features, active_geopackage_path, user_canceled

        num_selected_gpkg = len(gpkg_paths) # How many different gpkg sources the selected features belong to
        
        if num_selected_gpkg == 1: # If only one gpkg -> OK
            active_geopackage_path = gpkg_paths[0]
            # Get list of intrasis_ids from selected_features - all values (since only one gpkg)
            features = selected_features.keys()
        elif num_selected_gpkg > 1:
            ok_clicked, active_geopackage_path = self.select_geopackage()
            if not ok_clicked:
                user_canceled = True
            else:
                features = []
                # Get list of features belonging to selected geopackage
                for feature, path in selected_features.items():
                    if path.lower() == active_geopackage_path.lower():
                        features.append(feature)

        return features, active_geopackage_path, user_canceled

    def show_messagebox_no_selected_objects(self):
        """Show a message box to inform the user that objects must be selected befor opening browse relations"""
        msg_box = QMessageBox()
        msg_box.setWindowTitle(self.tr("No objects selected"))
        msg_box.setText(self.tr("To view data in the Intrasis relationship browser one or more objects must be selected either from the geometry layers or the 'objects' table."))
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.exec()

    def show_messagebox_no_loaded_gpkg(self):
        """Show a message box to inform the user that there are no gpkg loaded"""
        msg_box = QMessageBox()
        msg_box.setWindowTitle(self.tr("No Intrasis GeoPackage loaded"))
        msg_box.setText(self.tr("To view data in the Intrasis relationship browser one or more Intrasis GeoPackages must be loaded."))
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.exec()

    def set_active_geopackage_name(self):
        """Set active geopackage name in window title and init layer names based on active geopackage"""
        geopackage_path = self.gpkg_path
        idx_start = geopackage_path.rfind('/')
        idx_end = geopackage_path.rfind('.gkpg')
        gpkg_name_part = geopackage_path[idx_start+1:idx_end-4]
        self.active_gpkg_name = gpkg_name_part
        win_title = self.tr("Intrasis relationship browser")
        self.setWindowTitle(f"{win_title} - {gpkg_name_part}")

    def select_geopackage(self) -> Tuple[bool, str]:
        """Select geopackage using the select geopackage dialog"""
        select_geopackage_dlg = SelectGeoPackageDialog(only_gpkg_with_selected_features=True)
        result = select_geopackage_dlg.exec_()
        active_geopackage_path = select_geopackage_dlg.selected_geo_package
        ok_clicked = result == 1
        return ok_clicked, active_geopackage_path

    def select_tree_nodes(self, top_level_item:QTreeWidgetItem) -> Tuple[QDialogButtonBox.StandardButton, IntrasisTreeWidgetItem, bool, bool]:
        """Show dialog for selecting which nodes to include/not include in create layers"""
        win_title = self.tr("Create Layer from children")
        select_tree_nodes_dlg = SelectTreeNodesDialog(parent=self, top_level_intrasis_tree_item=top_level_item, gpkg_path=self.gpkg_path, win_titel=win_title)
        select_tree_nodes_dlg.flattened_layers = self.check_box_flat_layers.isChecked()
        select_tree_nodes_dlg.hierarchical_layers = self.check_box_hierarchical_layers.isChecked()
        select_tree_nodes_dlg.init_data_and_gui()
        select_tree_nodes_dlg.exec_()
        return select_tree_nodes_dlg.button_clicked, select_tree_nodes_dlg.final_top_level_item, select_tree_nodes_dlg.flattened_layers, select_tree_nodes_dlg.hierarchical_layers
        
    def clear_gui(self):
        """Clear data from all gui widgets"""
        self.combo_box_intrasis_id.clear()
        self.clear_data_widgets()

    def clear_data_widgets(self):
        """Clear all data from all gui widgets holding data"""
        self.label_intrasis_id.clear()
        self.label_name.clear()
        self.label_class.clear()
        self.label_subclass.clear()
        self.label_intrasis_id_above.clear()
        self.label_intrasis_id_below.clear()
        self.tree_widget_relations_above.clear()
        self.tree_widget_relations_below.clear()
        self.table_widget_current_object.clear()
        self.table_widget_relations_above.clear()
        self.table_widget_relations_below.clear()
        self.setup_table_widgets()

    def get_combobox_text_for_intrasis_id(self, intrasis_id:int) -> str:
        """Get the combobox display text for intrasis_id. Must exist in self.intrasis_item_dict"""
        return self.intrasis_item_dict.get(intrasis_id).get_short_description_text()
    
    def init_intrasis_id_combo_box(self, intrasis_id_to_select:int = None):
        """Fill intrasis_id combobox list and set selected item to 'intrasis_id_to_select' if it is not None"""
        intrasis_id_list = list(self.intrasis_item_dict.keys())
        intrasis_id_list.sort()

        self.combo_box_intrasis_id.clear()
        for intrasis_id in intrasis_id_list:
            self.combo_box_intrasis_id.addItem(self.get_combobox_text_for_intrasis_id(intrasis_id))
        
        if intrasis_id_to_select:
            self.combo_box_intrasis_id.setCurrentText(self.get_combobox_text_for_intrasis_id(intrasis_id_to_select))

    def setup_table_widgets(self):
        """Init table widgets"""
        self.setup_table_widget(self.table_widget_current_object)
        self.setup_table_widget(self.table_widget_relations_above)
        self.setup_table_widget(self.table_widget_relations_below)

    def setup_table_widget(self, table_widget:QTableWidget):
        """Init rows and columns for table_widget"""
        table_widget.setRowCount(0)
        table_widget.setColumnCount(3)
        table_widget.setHorizontalHeaderLabels([self.tr("Attribute"), self.tr("Value"), self.tr("Unit")])
        vertical_header = table_widget.verticalHeader()
        vertical_header.setSectionResizeMode(QHeaderView.Fixed)
        vertical_header.setDefaultSectionSize(24)

    def load_data_to_current_object_table(self):
        """Load attributes for the selected intrasis_id to the current object table widget"""
        self.table_widget_current_object.clear()
        self.setup_table_widget(self.table_widget_current_object)

        if self.selected_intrasis_item is None:
            message = "load_data_to_current_object_table: Selected intrasis item not set"
            QgsMessageLog.logMessage(message, BrowseRelationsUtils.MESSAGE_CATEGORY, Qgis.Warning)
            print(message)
            return

        self.load_attribute_data_into_table_widget(self.selected_intrasis_item.object_id, self.table_widget_current_object)

    def set_current_object_labels(self):
        """Set current object name and class labels"""
        if self.selected_intrasis_item is None:
            message = "set_current_object_labels: Selected intrasis item not set"
            QgsMessageLog.logMessage(message, BrowseRelationsUtils.MESSAGE_CATEGORY, Qgis.Warning)
            print(message)
            return
        
        self.label_intrasis_id.setText(f"#{self.selected_intrasis_item.intrasis_id}")
        self.label_intrasis_id_closest_parents.setText(f"#{self.selected_intrasis_item.intrasis_id}")
        self.label_intrasis_id_children.setText(f"#{self.selected_intrasis_item.intrasis_id}")
        self.label_name.setText(str(self.selected_intrasis_item.name))
        self.label_class.setText(str(self.selected_intrasis_item.classname))
        self.label_subclass.setText(str(self.selected_intrasis_item.subclass))

    def load_data_into_widgets_relations_below(self, tree_item:QTreeWidgetItem):
        """Load data into relations below attribute table and label for given tree_item"""
        self.table_widget_relations_below.clear()
        self.setup_table_widget(self.table_widget_relations_below)
        self.load_attribute_data_into_table_widget(tree_item.intrasis_item.object_id, self.table_widget_relations_below)
        self.label_intrasis_id_below.setText(f"#{tree_item.intrasis_item.intrasis_id}")

    def load_data_into_widgets_relations_above(self, tree_item:QTreeWidgetItem):
        """Load data into relations above attribute table and label for given tree_item"""
        self.table_widget_relations_above.clear()
        self.setup_table_widget(self.table_widget_relations_above)
        self.load_attribute_data_into_table_widget(tree_item.intrasis_item.object_id, self.table_widget_relations_above)
        self.label_intrasis_id_above.setText(f"#{tree_item.intrasis_item.intrasis_id}")
        
    def load_one_level_into_relations_above_tree_widget(self):
        """Load one level of parent nodes into the relations above tree widget"""
        self.tree_widget_relations_above.clear()
        if self.selected_intrasis_item is None:
            message = "load_one_level_into_relations_above_tree_widget: Selected intrasis item not set"
            QgsMessageLog.logMessage(message, BrowseRelationsUtils.MESSAGE_CATEGORY, Qgis.Warning)
            print(message)
            return

        current_node = IntrasisTreeWidgetItem(None, self.selected_intrasis_item)
        current_node.set_description_text()
        current_node.setIcon(0, Utils.create_qicon_object(current_node.intrasis_item.color, current_node.intrasis_item.get_icon_type()))
        
        related_above = BrowseRelationsUtils.get_realated_above(self.gpkg_path, self.selected_intrasis_item.object_id)
        if len(related_above) == 0:
            return
        
        for row in related_above:
            parent_object_id = row[0]
            parent_node = BrowseRelationsUtils.get_intrasis_tree_widget_item_for_object_id(self.gpkg_path, self.tree_widget_relations_above, parent_object_id)
            parent_node.intrasis_item.related_text = row[1]
            parent_node.set_description_text(0, True)
            parent_node.setIcon(0, Utils.create_qicon_object(parent_node.intrasis_item.color, parent_node.intrasis_item.get_icon_type()))
            parent_node.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
        
        # Sort parent items
        self.tree_widget_relations_above.sortItems(0, Qt.AscendingOrder)
        # Add current object as child node to the last of the parent nodes
        last_parent_node = self.tree_widget_relations_above.topLevelItem(self.tree_widget_relations_above.topLevelItemCount()-1)
        last_parent_node.addChild(current_node)
        self.tree_widget_relations_above.setCurrentItem(current_node)
        self.load_data_into_widgets_relations_above(current_node)
       
    def load_data_into_relations_below_tree_widget(self):
        """Load data into relations below tree widget based on selected IntrasisId"""
        max_tree_levels = 3
        self.tree_widget_relations_below.clear()

        if self.selected_intrasis_item is None:
            message = "load_data_into_relations_below_tree_widget: Selected intrasis item not set"
            QgsMessageLog.logMessage(message, BrowseRelationsUtils.MESSAGE_CATEGORY, Qgis.Warning)
            print(message)
            return

        # Create top tree item (from selected object_id) and then add realtions below that item to the tree widget
        top_item = IntrasisTreeWidgetItem(self.tree_widget_relations_below, self.selected_intrasis_item)
        top_item.set_description_text(0, False)
        top_item.setIcon(0, Utils.create_qicon_object(top_item.intrasis_item.color, top_item.intrasis_item.get_icon_type()))

        BrowseRelationsUtils.add_objects_below(self.gpkg_path, top_item, max_tree_levels)
        if top_item.childCount() == 0:
            self.tree_widget_relations_below.clear()
            return

        self.tree_widget_relations_below.setCurrentItem(top_item)
        self.tree_widget_relations_below.sortItems(0, Qt.AscendingOrder)
        BrowseRelationsUtils.expand_tree_widget_item(self.tree_widget_relations_below, top_item)
        self.load_data_into_widgets_relations_below(top_item)
    
    def load_attribute_data_into_table_widget(self, object_id:int, table_widget:QTableWidget):
        """Load data from the attributes layer for given object_id into given table_widget"""
        attribute_data_frame = Utils.get_attributes_data_for_object_id(BrowseRelationsUtils.MESSAGE_CATEGORY, self.gpkg_path, object_id)
        if attribute_data_frame is None:
            return
        
        table_widget.setRowCount(len(attribute_data_frame))
        for idx, row in attribute_data_frame.iterrows():
            table_widget.setItem(idx, 0, QTableWidgetItem(str(row[0])))
            table_widget.setItem(idx, 1, QTableWidgetItem(str(row[1])))
            table_widget.setItem(idx, 2, QTableWidgetItem(str(row[2])))
    
    def create_layers_from_closest_parents(self, layer_group_name:str):
        """Collect all top level items in a list and create layers"""
        top_level_items = []
        for i in range(self.tree_widget_relations_above.topLevelItemCount()):
            top_level_items.append(self.tree_widget_relations_above.topLevelItem(i))
        
        task_name = f"Create Layers: {layer_group_name}"
        task_create_layers_from_parents = CreateLayersTaskModule.CreateLayersFromAllChildNodesTask(task_name,
                                                                                                   BrowseRelationsUtils.MESSAGE_CATEGORY,
                                                                                                   self.gpkg_path,
                                                                                                   top_level_items,
                                                                                                   layer_group_name,
                                                                                                   False,
                                                                                                   False)
        task_create_layers_from_parents.result_done_signal.connect(self.on_task_create_layers_finished)
        QgsApplication.taskManager().addTask(task_create_layers_from_parents)
        QgsApplication.processEvents()  # Allow the scheduler to schedule the tasks
        
    def create_layers_from_children(self, layer_group_name_base:str):
        """Show select nodes dialog and start create layers based on user input"""
        # Disable the checkboxes while working in the select nodes dialog
        self.check_box_hierarchical_layers.setEnabled(False)
        self.check_box_flat_layers.setEnabled(False)

        # Open select tree nodes dialog with a copy of the top level item in the children tree widget
        top_level_item = self.tree_widget_relations_below.topLevelItem(0)
        button_clicked, selected_top_level_item, flattened_layers, hierarchical_layers = self.select_tree_nodes(copy.deepcopy(top_level_item))

        # Set checked states on the checkboxes based on the checkbox states in the select nodes dialog
        self.check_box_hierarchical_layers.setChecked(hierarchical_layers)
        self.check_box_flat_layers.setChecked(flattened_layers)

        print(f"Flattened layers: {flattened_layers}. Hierarchical layers: {hierarchical_layers}")

        # Done with selectning nodes: Enable checkboxes again
        self.check_box_hierarchical_layers.setEnabled(True)
        self.check_box_flat_layers.setEnabled(True)

        if button_clicked == QDialogButtonBox.Cancel:
            print("Create layers canceled by user")
            return

        if selected_top_level_item is None:
            QgsMessageLog.logMessage("Error in select nodes dialog. Create layers aborted", BrowseRelationsUtils.MESSAGE_CATEGORY, Qgis.Critical)
            return
        
        if flattened_layers:
            layer_group_name = f"{layer_group_name_base}.Flattened"
            task_name = f"Create Layers: {layer_group_name}"
            task_create_flat_layers = CreateLayersTaskModule.CreateLayersFromAllChildNodesTask(task_name,
                                                                                               BrowseRelationsUtils.MESSAGE_CATEGORY,
                                                                                               self.gpkg_path,
                                                                                               [copy.deepcopy(selected_top_level_item)],
                                                                                               layer_group_name,
                                                                                               True,
                                                                                               True)
            task_create_flat_layers.result_done_signal.connect(self.on_task_create_layers_finished)
            QgsApplication.taskManager().addTask(task_create_flat_layers)
        if hierarchical_layers:
            layer_group_name = f"{layer_group_name_base}.Hierarchical"
            task_name = f"Create Layers: {layer_group_name}"
            task_create_hieararchical_layers = CreateLayersTaskModule.CreateLayersFromAllChildNodesTask(task_name,
                                                                                                        BrowseRelationsUtils.MESSAGE_CATEGORY,
                                                                                                        self.gpkg_path,
                                                                                                        [copy.deepcopy(selected_top_level_item)],
                                                                                                        layer_group_name,
                                                                                                        True,
                                                                                                        False)
            task_create_hieararchical_layers.result_done_signal.connect(self.on_task_create_layers_finished)
            QgsApplication.taskManager().addTask(task_create_hieararchical_layers)

        if flattened_layers or hierarchical_layers:
            QgsApplication.processEvents()  # Allow the scheduler to schedule the tasks
    
    def on_task_create_layers_finished(self, result):
        """Handler for when a 'CreateLayersFromAllChildNodesTask' has finished. Parameter 'result' contains the created layers and a tree structure for 
        the layer groups that should be created for the created layers"""
        if result:
            layers, group_tree_top_node = result
            
            if not group_tree_top_node:
                QgsMessageLog.logMessage("Error in on_task_create_layers_finished: Could not add created layers to table of contents. No top layer group found.", 
                                         BrowseRelationsUtils.MESSAGE_CATEGORY, 
                                         Qgis.Critical)
                return

            self.add_groups_and_layers_to_table_of_contents(group_tree_top_node, layers)

    def add_groups_and_layers_to_table_of_contents(self, group_tree_top_node: LayerGroupTreeNode, layers:dict):
        """Add all layer groups to the QGIS table of contents according to the stree structure below the top node 'group_tree_top_node'. For each
        node the layers in the LayerGroupTreeNode:layer_list is added to the created QGIS layer group"""
        # Add the layers, containing the geometries and attributes, to the project
        QgsProject.instance().addMapLayers(layers.values(), False)
        
        root = QgsProject.instance().layerTreeRoot()
        top_group = QgsLayerTreeGroup(group_tree_top_node.group_name)
        root.insertChildNode(0, top_group)
        
        group_tree_top_node.group_added_to_qgis_toc = top_group

        stack = [group_tree_top_node]
        while stack:
            current_node:LayerGroupTreeNode = stack.pop()
            
            if not current_node.group_added_to_qgis_toc:
                QgsMessageLog.logMessage(f"Error in add_groups_and_layers_to_table_of_contents: Could not add layers to tabe of contents. No layer group found", 
                                         BrowseRelationsUtils.MESSAGE_CATEGORY, 
                                         Qgis.Critical)
                return
            
            # Add layers to the current node's added_group (TOC group)
            for layer in current_node.layer_list:
                current_node.group_added_to_qgis_toc.insertLayer(0, layer)

            # Add groups for all child nodes
            added = {}
            for i in range(0, current_node.childCount()):
                child_item:LayerGroupTreeNode = current_node.child(i)
                added_group = added.get(child_item.group_name)
                if not added_group:
                    added_group = current_node.group_added_to_qgis_toc.addGroup(child_item.group_name)
                    added[child_item.group_name] = added_group
                child_item.group_added_to_qgis_toc = added_group
                stack.append(child_item)
            
        Utils.expand_group(top_group.name())