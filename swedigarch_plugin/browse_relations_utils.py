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
"""Utils functions for BrowseRelations"""
from typing import Union
from qgis.core import QgsMessageLog, Qgis
from PyQt5.QtWidgets import QTreeWidgetItem, QHeaderView, QTreeWidget
import traceback
from . import utils as Utils
from . import create_layers_utils as CreateLayersUtils
from .browse_relations_utils_classes import IntrasisItem, IntrasisTreeWidgetItem

MESSAGE_CATEGORY = 'Intrasis relationship browser'

def expand_tree_widget_item(tree_widget:QTreeWidget, tree_widget_item:QTreeWidgetItem):
    """Expand given QTreeWidget tree_widget downwards from start item 'tree_widget_item'"""
    stack = [tree_widget_item]

    while stack:
        current_node = stack.pop()
        if current_node is None:
            return
        
        if current_node.childCount() > 0:
            tree_widget.expandItem(current_node)
        
        for i in range(0, current_node.childCount()):
            child_node = current_node.child(i)
            stack.append(child_node)

def add_objects_below(gpkg_path:str, top_item:IntrasisTreeWidgetItem, max_number_of_tree_levels:int):
    """Add tree items below starting at top_item, and stopping 'max_number_of_tree_levels' levels down from top_item"""
    top_item.tree_level = 1
    stack = [top_item]

    while stack:
        # Get next node to process
        current_node = stack.pop()

        # Find current node's related directly below
        object_id = current_node.intrasis_item.object_id
        related_below = get_realated_below(gpkg_path, object_id)

        # Only add related below nodes if we're not at the max level depth from start node (top_item)
        if current_node.tree_level + 1 > max_number_of_tree_levels:
            if current_node.intrasis_item.has_unloaded_related_below:
                current_node.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator) # To show expand arrow in tree even though this node has no children
            continue

        # Add related below nodes to the stack for later processing
        for row in related_below:
            new_node = get_intrasis_tree_widget_item_for_object_id(gpkg_path, current_node, row[0])
            
            # Only add node to stack if it does not already exist as a parent
            if is_in_parents(new_node):
                QgsMessageLog.logMessage(f"IntrasisId #{new_node.intrasis_item.intrasis_id} already added at a parent level to node #{current_node.intrasis_item.intrasis_id}. Not added as child node to #{current_node.intrasis_item.intrasis_id}.", MESSAGE_CATEGORY, Qgis.Warning)
                current_node.removeChild(new_node)
                continue
        
            new_node.intrasis_item.related_text = row[1]
            new_node.tree_level = current_node.tree_level + 1
            new_node.intrasis_item.has_unloaded_related_below = has_related_below(gpkg_path, new_node.intrasis_item.object_id)
            new_node.set_description_text()
            new_node.setIcon(0, Utils.create_qicon_object(new_node.intrasis_item.color, new_node.intrasis_item.get_icon_type()))
            stack.append(new_node)
            
        current_node.intrasis_item.has_unloaded_related_below = False
        current_node.set_description_text()
        current_node.setIcon(0, Utils.create_qicon_object(current_node.intrasis_item.color, current_node.intrasis_item.get_icon_type()))
        current_node.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicatorWhenChildless)

def set_tree_widget_header_size_mode(tree_widget:QTreeWidget):
    """Set the tree_widget header to resize to contents"""
    header = tree_widget.header()
    header.setSectionResizeMode(0, QHeaderView.ResizeToContents)

def get_intrasis_item_dict_for_features(gpkg_path:str, features:list) -> dict:
    """Get a dictionary where IntrasisId is the key and IntrasisItem is the value"""
    object_id_field_name = 'object_id'
    object_id_list = []
    intrasis_item_dict = {}

    for feature in features:
        fields = feature.fields()

        index_object_id = fields.lookupField(object_id_field_name)
        if index_object_id < 0: #The feature has no object_id attribute, continue to the next feature
            continue
        object_id = feature.attribute(object_id_field_name)
        object_id_list.append(object_id)
    
    if len(object_id_list) > 0:
        for object_id in object_id_list:
            if not object_id in intrasis_item_dict:
                intrasis_item = get_intrasis_item_for_object_id(gpkg_path, object_id)
                if intrasis_item:
                    intrasis_item_dict[intrasis_item.intrasis_id] = intrasis_item
    
    return intrasis_item_dict
    
def get_intrasis_item_for_object_id(gpkg_path:str, object_id:int) -> Union[IntrasisItem,None]:
    """Get an IntrasisItem for given object_id"""
    data_frame = Utils.get_objects_data_for_object_id(MESSAGE_CATEGORY, gpkg_path, object_id)
    
    if data_frame is None:
        return None
    
    try:
        item = IntrasisItem(int(object_id))
        item.intrasis_id = int(data_frame["IntrasisId"][0])
        item.name = str(data_frame["Name"][0])
        item.classname = str(data_frame["Class"][0])
        if Utils.is_empty_string_or_none(data_frame["SubClass"][0]):
            item.subclass = None
        else:    
            item.subclass = str(data_frame["SubClass"][0])
        item.color = int(data_frame["Color"][0])

        return item
    except Exception as ex:
        traceback.print_exc()
        print(f"Error in Browse Relations - get_intrasis_item_for_object_id() {ex}")

def get_intrasis_tree_widget_item_for_object_id(gpkg_path:str, parent:IntrasisTreeWidgetItem, object_id:int) -> Union[IntrasisTreeWidgetItem,None]:
    """Get IntrasisTreeWidgetItem item for given object_id"""
    item = IntrasisTreeWidgetItem(parent, IntrasisItem(object_id))
    item.intrasis_item = get_intrasis_item_for_object_id(gpkg_path, object_id)

    if item.intrasis_item is None:
        return None

    return item

def get_realated_below(gpkg_path:str, object_id:int) -> list:
    """Get related_id and related_text from the object_relations table where base_id=object_id, i.e. all relations directly below object_id"""
    sql = f"SELECT related_id, related_text FROM {Utils.OBJECT_RELATIONS_TABLE_NAME} WHERE base_id = {object_id}"
    data_frame = Utils.get_data_frame_from_gpkg(gpkg_path, sql)
    
    if len(data_frame) <= 0:
        return []
    if len(data_frame.columns) != 2:
        message = f"get_realated_below: Incorrect number of columns for base_id = {object_id}"
        QgsMessageLog.logMessage(message, MESSAGE_CATEGORY, Qgis.Warning)
        print(message)
        return []

    return data_frame.values

def get_realated_above(gpkg_path:str, object_id:int) -> list:
    """Get base_id and related_text from the object_relations table where related_id=object_id, i.e. all relations directly above object_id"""
    sql = f"SELECT base_id, base_text FROM {Utils.OBJECT_RELATIONS_TABLE_NAME} WHERE related_id = {object_id}"
    data_frame = Utils.get_data_frame_from_gpkg(gpkg_path, sql)
    
    if len(data_frame) <= 0:
        return []
    if len(data_frame.columns) != 2:
        message = f"get_realated_above: Incorrect number of columns for related_id={object_id}"
        QgsMessageLog.logMessage(message, MESSAGE_CATEGORY, Qgis.Warning)
        print(message)
        return []

    return data_frame.values

def has_related_below(gpkg_path:str, object_id:int) -> int:
    """Return True/False based on if object_id has any related objects below"""
    return len(get_realated_below(gpkg_path, object_id)) > 0

def is_in_parents(tree_node:IntrasisTreeWidgetItem) -> bool:
    """Check if given node 'tree_node' already exitists at a parent level"""
    current_parent:IntrasisTreeWidgetItem = tree_node.parent()
    
    while current_parent is not None:
        if current_parent.intrasis_item.object_id == tree_node.intrasis_item.object_id:
            return True # Found the same object_id at parent level
        current_parent = current_parent.parent()
    
    return False # Could not find the same object_id at any parent level