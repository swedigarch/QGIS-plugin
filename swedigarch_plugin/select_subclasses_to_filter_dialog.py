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
import re
import traceback
import psycopg2
import pandas as pd
from qgis.PyQt import uic, QtWidgets
from PyQt5 import QtCore
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QDialogButtonBox, QTreeWidgetItem, QHeaderView
from . import utils as Utils

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'select_subclasses_to_filter_dialog.ui'))

class SelectSubClassesToFilterDialog(QtWidgets.QDialog, FORM_CLASS):
    """SelectTreeNodesDialog dialog. Dialog to remove tree nodes from a QTreeWidget"""
    def __init__(self, selected_databases:list[str], host:str, user_name:str, password:str, port:int, sslmode:str, parent=None):
        """Ui_SelectSubClassesToFilterDialog Constructor"""
        super(SelectSubClassesToFilterDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.initialized = False
        self.final_top_level_item = None
        self.button_clicked = None
        self.databases = selected_databases
        self.host = host
        self.user_name = user_name
        self.password = password
        self.port = port
        self.sslmode_text = sslmode
        self.selected_sub_classes = []

        self.tree_widget_class_subclass.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tree_widget_class_subclass.customContextMenuRequested.connect(self.show_context_menu)
        self.tree_widget_class_subclass.itemChanged.connect(self.on_item_changed)
        self.tree_widget_class_subclass.setColumnWidth(0, 800)
        header = self.tree_widget_class_subclass.header()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setStretchLastSection(True)

        self.lbl_filter_info.setText(self.tr("No selection"))
        self.lwSelectedSubClasses.setSortingEnabled(True)
        self.splitter.setSizes([500, 130])

        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setText(self.tr("OK"))
        self.button_box.button(QtWidgets.QDialogButtonBox.Cancel).setText(self.tr("Cancel"))
        self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)
        self.button_box.accepted.connect(self.on_ok)
        self.button_box.rejected.connect(self.on_cancel)

        #self.check_box_hierarchical_layers.stateChanged.connect(self.on_check_box_hierarchical_create_layers_state_changed)
        #self.check_box_flat_layers.stateChanged.connect(self.on_check_box_flat_create_layers_state_changed)

    def closeEvent(self, event):
        """The close dialog event (QCloseEvent)"""
        self.button_clicked = QDialogButtonBox.Cancel

    def keyPressEvent(self, event):
        """Handle key press event, to be able to delete with delete key"""
        if event.key() == 16777223: # Delete key
            current_row = self.lwSelectedSubClasses.currentRow()
            if current_row >= 0:
                row_text = self.lwSelectedSubClasses.currentItem().text()
                parts = row_text.split('\\')
                class_name = parts[0].strip()
                sub_class_name = parts[1].strip()
                ix = sub_class_name.index("(")
                sub_class_name = sub_class_name[:ix].strip()
                found_item = self.find_item(class_name)
                if found_item is None:
                    return

                child_item = self.find_item_in_children(found_item, sub_class_name)
                if child_item is not None:
                    self.lwSelectedSubClasses.takeItem(current_row)  # Remove the item from the list
                    child_item.setCheckState(0, QtCore.Qt.Unchecked)

    def init_data_and_gui(self):
        """Load data and init gui"""
        try:
            idx = 0
            all_classes = {}
            sub_class_databases = {}
            header = self.tree_widget_class_subclass.header()
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            for database in self.databases:
                print(f"loading for database: {database}")
                connection_string = f"dbname={database} host={self.host} user={self.user_name} password={self.password} port={self.port}{self.sslmode_text}"
                conn = psycopg2.connect(connection_string)

                sql = Utils.load_resource('sql/select_classes.sql')
                data_frame = pd.read_sql(sql, conn)
                classes = {}
                for row in data_frame.itertuples(index=False):
                    #print(f"ClassId: {row.MetaId}  Class: {row.Name}")
                    if row.Name not in all_classes:
                        all_classes[row.Name] = []
                    classes[row.MetaId] = row.Name

                sql = Utils.load_resource('sql/select_sub_classes.sql')
                data_frame = pd.read_sql(sql, conn)
                for row in data_frame.itertuples(index=False):
                    #print(f"ClassId: {row.ClassId}  SubClassId: {row.MetaId}  Class: {row.Name}")
                    if row.ClassId not in classes:
                        print(f"{row.ClassId} not found in: {classes}")
                    class_name = classes[row.ClassId]
                    combined_name = f"{class_name}|{row.Name}"
                    if combined_name in sub_class_databases:
                        sub_class_databases[combined_name].append(database)
                    else:
                        sub_class_databases[combined_name] = [database]

                    if row.Name not in all_classes[class_name]:
                        all_classes[class_name].append(row.Name)
                        #all_classes[class_name].append(f"{database|{row.Name}")

            for class_name, subclasses in sorted(all_classes.items()):
                if len(subclasses) > 0:
                    #print(f"class_name: {class_name} subclasses: {subclasses}")
                    item = ClassTreeNodeItem(self.tree_widget_class_subclass, class_name)
                    item.setText(0, class_name)
                    idx += 1

                    for sub_class_name in subclasses:
                        sc_databases = []
                        combined_name = f"{class_name}|{sub_class_name}"
                        if combined_name in sub_class_databases:
                            sc_databases = sub_class_databases[combined_name]
                        else:
                            print(f"No match in sub_class_databases for: {combined_name}")
                        sc_item = SubClassTreeNodeItem(item, sc_databases, class_name, sub_class_name)
                        sc_item.setText(0, sub_class_name)
                        sc_item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
                        sc_item.setCheckState(0, QtCore.Qt.Unchecked)

            self.tree_widget_class_subclass.setSortingEnabled(True)
            self.tree_widget_class_subclass.sortItems(0, QtCore.Qt.AscendingOrder) # Sort by Class (column 0)
            self.tree_widget_class_subclass.sortItems(1, QtCore.Qt.AscendingOrder) # Sort by SubClass (column 1)

            # Resize columns to fit contents
            self.tree_widget_class_subclass.resizeColumnToContents(0)
            self.initialized = True
        except Exception as err:
            traceback.print_exc()
            print(f"Exception in init_data_and_gui(): {err}")

    def get_selected_sub_classes_as_list_of_strings(self) -> list[str]:
        """Get selected sub classes list items as a list of strings"""
        return [self.lwSelectedSubClasses.item(x).text() for x in range(self.lwSelectedSubClasses.count())]
    
    def get_selected_sub_classes_as_list_of_tuples(self) -> list[tuple[str,str]]:
        """Get selected sub classes list items as a list of tuples, each tuple is a string (className,subClassName)"""
        item_list = [self.lwSelectedSubClasses.item(x).text() for x in range(self.lwSelectedSubClasses.count())]
        return [self.extract_class_and_subclass_from_string(s) for s in item_list]
    
    def extract_class_and_subclass_from_string(self, s):
        """Extract class and subclass from a string on the form 'class_name \\ subclass_name (occurrence)'"""
        class_name, subclass_with_occurrence = s.split(' \\ ')
        subclass_name = re.sub(r' \(\d+\)', '', subclass_with_occurrence)  # Remove the occurrence part
        return (class_name, subclass_name)

    def on_ok(self):
        """Selection of tree nodes done"""
        self.button_clicked = QDialogButtonBox.Ok
        self.accept()

    def on_cancel(self):
        """Handle cancel clicked - close dialog"""
        self.close()

    def update_ok_status(self) -> None:
        """Update Ok button status"""
        if len(self.selected_sub_classes) > 0:
            self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.button_box.button(QtWidgets.QDialogButtonBox.Ok).setEnabled(False)

    def on_item_changed(self, item):
        """On tree item selection changed"""
        if self.initialized:
            #print(f"on_item_changed() item: {item.text(0)}  checkState: {item.checkState(0)}")
            combined_name = f"{item.class_name}\\{item.sub_class_name}"
            long_combined_name = f"{item.class_name} \\ {item.sub_class_name} ({len(item.databases)})"
            if item.checkState(0) == 2:
                self.selected_sub_classes.append(combined_name)
                self.lwSelectedSubClasses.addItem(long_combined_name)
            else:
                self.selected_sub_classes.remove(combined_name)
                self.remove_selected_filter(long_combined_name)

            if len(self.selected_sub_classes) > 0:
                self.lbl_filter_info.setText(f"{len(self.selected_sub_classes)} " + self.tr("Selected"))
            else:
                self.lbl_filter_info.setText(self.tr("No selection"))
            #print(f"self.selected_sub_classes: {self.selected_sub_classes}, databases: {item.databases}")
            self.update_ok_status()

    def find_item(self, text):
        """Find ClassNodeItem matching the given text"""
        for index in range(self.tree_widget_class_subclass.topLevelItemCount()):
            item = self.tree_widget_class_subclass.topLevelItem(index)
            if item.text(0) == text:
                return item
            found_item = self.find_item_in_children(item, text)
            if found_item:
                return found_item
        return None

    def find_item_in_children(self, parent_item, text):
        """Find SubClassNodeItem matching the given text under the give parent item"""
        for index in range(parent_item.childCount()):
            child_item = parent_item.child(index)
            if child_item.text(0) == text:
                return child_item
            found_item = self.find_item_in_children(child_item, text)
            if found_item:
                return found_item
        return None

    def show_context_menu(self, position):
        """Show context_menu for tree widget"""
        #global_pos = self.tree_widget_intrasis_relations.viewport().mapToGlobal(position)
        #self.relations_below_context_menu.exec_(global_pos)


    def remove_selected_filter(self, to_remove:str):
        """Remove matching item from lwSelectedSubClasses"""
        for index in range(self.lwSelectedSubClasses.count()):
            item = self.lwSelectedSubClasses.item(index)
            if item.text() == to_remove:
                self.lwSelectedSubClasses.takeItem(index)
                break

class ClassTreeNodeItem(QTreeWidgetItem):
    """Class that represents a tree node for a Intrasis Class."""
    def __init__(self, parent:QTreeWidgetItem, class_name: str):
        super().__init__(parent)
        self.sub_classes:list = []
        self.class_name = class_name
        self.setSizeHint(0, QSize(200, 16))  # Width is ignored, Height is set to 40

    def sizeHint(self):
        """Set the size of this item"""
        # Set your custom height here
        print("ClassTreeNodeItem.sizeHint")
        height = 60  # Example height
        return QSize(self.parent().viewport().width(), height)

class SubClassTreeNodeItem(QTreeWidgetItem):
    """Class that represents a tree node for a Intrasis SubClass."""
    def __init__(self, parent:QTreeWidgetItem, databases:list[str], class_name:str, sub_class_name: str):
        super().__init__(parent)
        self.databases = databases
        self.class_name = class_name
        self.sub_class_name = sub_class_name
        self.setSizeHint(0, QSize(0, 16))  # Width is ignored, Height is set to 40
