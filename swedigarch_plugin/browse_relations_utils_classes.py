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
"""Helper classes for the Browse Relations dialog"""
import copy
from PyQt5.QtWidgets import QTreeWidgetItem
from . import utils as Utils
from .utils_classes import IconType

class IntrasisItem:
    """Intrasis item, containing the items's Intrasis information"""
    def __init__(self, object_id:int):
        self.object_id = object_id
        self.intrasis_id = 0
        self.classname = ""
        self.subclass = ""
        self.name = ""
        self.related_text = ""
        self.color = 0
        self.has_unloaded_related_below = False

    def subclass_is_none(self):
        """Return true if subclass is none"""
        return not self.subclass or self.subclass.upper() in ("NULL", "NONE")

    def get_icon_type(self) -> IconType:
        """Get icon type based on if subclass is 'NULL' or not"""
        if self.subclass_is_none():
            return IconType.SQUARE
        return IconType.CIRCLE
        
    def get_description_text(self, include_relation_text:bool = True) -> str:
        """Get description text"""
        description = f"{self.classname}"

        if not self.subclass_is_none():
            description += f" / {self.subclass}"

        description += f" #{self.intrasis_id}"

        if include_relation_text and self.related_text != "":
            description += f" ({self.related_text})"

        return description

    def get_short_description_text(self) -> str:
        """Get a short description text"""
        description = f"{self.intrasis_id} - {self.classname}"

        if not self.subclass_is_none():
            description += f" / {self.subclass}"

        return description

class IntrasisTreeWidgetItem(QTreeWidgetItem):
    """IntrasisTreeWidgetItem inherits QTreeWidgetItem, for storing and accessing intrasis items in a QTreeWidget"""
    def __init__(self, parent:QTreeWidgetItem, item:IntrasisItem):
        super().__init__(parent)
        self.intrasis_item = item
        self.tree_level = 0
        self.tree_level_layer_id = 0
        self.layer_group = None
    
    def __hash__(self):
        return id(self)
    
    def __deepcopy__(self, memo):
        """Create a new instance as a deep copy of this instance of the IntrasisTreeWidgetItem"""
        if self in memo:
            return memo[self]
        
        # Craete a new instance
        cloned_item = super().clone()
        copied_item = IntrasisTreeWidgetItem(cloned_item.parent(), copy.copy(self.intrasis_item))

        # Copy all attributes
        for attr_name in cloned_item.__dict__:
            setattr(copied_item, attr_name, getattr(cloned_item, attr_name))
        
        # Set text and icon for the copied object
        copied_item.setText(0, copied_item.intrasis_item.get_description_text())
        copied_item.setIcon(0, Utils.create_qicon_object(copied_item.intrasis_item.color, copied_item.intrasis_item.get_icon_type()))

        # Recursively copy all child nodes
        for i in range(self.childCount()):
            child_node = self.child(i)
            new_child_node = copy.deepcopy(child_node, memo)
            copied_item.addChild(new_child_node)

        memo[self] = copied_item
        # Return the new instance
        return copied_item
    
    def set_description_text(self, column:int = 0, include_relation_text:bool = True):
        """Sets the tree item description text for this item"""
        self.setText(column, self.intrasis_item.get_description_text(include_relation_text))

class LayerGroupTreeNode(QTreeWidgetItem):
    """Class that represents a tree node with information for the QGIS layer group which layers it should contain. Used to create the correct layer group tree
    structure in the 'CreateLayersFromAllChildNodesTask', since it is not allowed to crete actual QGIS table of contents layer groups in a background thread."""
    def __init__(self, parent:QTreeWidgetItem, group_name: str, level_id:int):
        super().__init__(parent)
        self.group_name = group_name
        self.layer_list:list = []
        self.tree_level_id = level_id
        self.group_added_to_qgis_toc = None