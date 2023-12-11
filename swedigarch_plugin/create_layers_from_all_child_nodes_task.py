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

from typing import Tuple
from qgis.core import QgsTask, QgsMessageLog, Qgis, QgsVectorLayer, QgsWkbTypes, QgsFeature, QgsFields, QgsGeometry
from PyQt5.QtCore import QObject, pyqtSignal
from . import utils as Utils
from . import browse_relations_utils as BrowseRelationsUtils
from .browse_relations_utils_classes import IntrasisTreeWidgetItem, LayerGroupTreeNode
from . import create_layers_utils as CreateLayersUtils

class CreateLayersFromAllChildNodesTask(QgsTask):
    """QgsTask to create layers from all child nodes to each top node in the provided 'top_item_list' (list of 'IntrasisTreeWidgetItem'). 
    When the task is finished the signal 'result_done_signal'is emitted with a dict of all created layers and the top node of a 'LayerGroupTreeNode'
    tree structure of the layer groups"""
    result_done_signal = pyqtSignal(object)

    def __init__(self,
                 description:str,
                 message_category:str,
                 gpkg_path:str,
                 top_item_list:list,
                 layer_group_name:str,
                 include_id_in_group_name:bool = True,
                 flatten_layers:bool = False):
        super().__init__(description, QgsTask.CanCancel)
        self.message_category = message_category
        self.gpkg_path = gpkg_path
        self.top_item_list = top_item_list
        self.layer_group_name = layer_group_name
        self.include_id_in_group_name = include_id_in_group_name
        self.flatten_layers = flatten_layers
        self.layers = {}
        self.class_subclass_attributes = {}
        self.current_feature_id = 0
        self.group_tree_top_node = None
        
    def run(self):
        """Run method for the QgsTask. Loop over all top nodes in 'self.top_item_list' (list of 'IntrasisTreeWidgetItem') 
        emit 'result_done_signal' when finished (if the task was not canceled before finishing)"""
        top_layer_group = LayerGroupTreeNode(None, self.layer_group_name, 0)

        for top_item in self.top_item_list:
            result = self.create_layers_and_layer_groups_for_all_child_nodes(top_item, top_layer_group)

            if not result:
                return False
        
        self.result_done_signal.emit((self.layers, self.group_tree_top_node))
        return True
    
    def create_layers_and_layer_groups_for_all_child_nodes(self, top_item:IntrasisTreeWidgetItem, top_level_group:LayerGroupTreeNode) -> bool:
        """Create layers and layer groups for all child nodes of 'IntrasisTreeWidgetItem' 'top_item'. Layer groups will be added as child nodes to the 
        'LayerGroupTreeNode' 'top_level_group' and, if self.flatten_layers=False, have the same tree strucutre as the tree below 'top_item'. If
        self.flatten_layers=True only one subgroup will be created below the 'top_level_group' where all created layers will be placed"""
        current_layer_level_id = 0
        top_item.tree_level_layer_id = current_layer_level_id
        subgroup_base_name = "children"
        self.group_tree_top_node = top_level_group
        top_item.layer_group = self.group_tree_top_node
        next_group_node = None

        # If flattened layer - only create one subgroup for all child node layers
        if self.flatten_layers:
            next_group_node = LayerGroupTreeNode(top_item.layer_group, subgroup_base_name, 1)

        stack = [top_item]
        while stack:
            if self.isCanceled():
                return False
            
            current_node = stack.pop()
            
            self.add_item_to_layers_and_layer_groups(current_node)
            
            # Check if the current item has child nodes, and if not if it has unloaded child nodes (not all levels are loaded into the tree widget 
            # from the beginning to prevent crash/long waiting times for large tree structures)
            if current_node.childCount() == 0:
                if current_node.intrasis_item.has_unloaded_related_below:
                    BrowseRelationsUtils.add_objects_below(self.gpkg_path, current_node, 3) # Max number of nodes not reached -> load more nodes
                else:
                    continue
            
            # Move on to next tree level
            current_layer_level_id += 1

            # If not flattened layer structure: create new layer subgroup to add the child nodes to
            group_name = subgroup_base_name
            if not self.flatten_layers:
                if self.include_id_in_group_name:
                    group_name = f"{group_name}_IntrasisId_{current_node.intrasis_item.intrasis_id}"

                next_group_node = LayerGroupTreeNode(current_node.layer_group, group_name, current_layer_level_id)
                        
            # Find current node's child nodes and add to stack for processing
            for i in range(0, current_node.childCount()):
                child_item:IntrasisTreeWidgetItem = current_node.child(i)
                child_item.tree_level_layer_id = current_layer_level_id
                child_item.layer_group = next_group_node
                stack.append(child_item)
        
        return True
    
    def add_item_to_layers_and_layer_groups(self, tree_item:IntrasisTreeWidgetItem):
        """Add all geometries (if there are any) and attributes to a layer in self.layers and for 'IntrasisTreeWidgetItem' 'tree_item'"""
        # Get all geometries for current tree node
        type_geometries = Utils.get_geometries_for_object_id(self.gpkg_path, tree_item.intrasis_item.object_id)
        srids = Utils.get_srid_per_table_name(self.gpkg_path)

        # Get attributes for current tree node
        attribute_fields, attribute_values = CreateLayersUtils.get_attribute_fields_and_values(self.gpkg_path,
                                                                                               tree_item.intrasis_item.object_id,
                                                                                               tree_item.intrasis_item.classname,
                                                                                               tree_item.intrasis_item.subclass,
                                                                                               self.class_subclass_attributes)
        
        # Get parent node and layer group name based on parent
        group_name = "NONE"
        parent_item:IntrasisTreeWidgetItem = tree_item.parent()
        if(parent_item):
            group_name = "children"
            if not self.flatten_layers:
                group_name = f"{group_name}.IntrasisId_{parent_item.intrasis_item.intrasis_id}"
        
        layer_base_name = tree_item.intrasis_item.classname.replace(' ', '_')
        if not tree_item.intrasis_item.subclass_is_none():
            layer_base_name = f"{layer_base_name}.{tree_item.intrasis_item.subclass.replace(' ', '_')}"                                                
        
        # If no geometries - add feature to table layer
        if not type_geometries:
            layer = self.get_qgs_vector_layer("None", attribute_fields, group_name, layer_base_name, tree_item)
                        
            if not CreateLayersUtils.object_is_in_layer(layer, tree_item.intrasis_item.object_id):
                feature = self.create_qgs_feature(attribute_values)
                layer.dataProvider().addFeatures([feature])
        else: # Loop over the geometries and add them to geometry layer
            for type_geom in type_geometries:
                geom_list = type_geometries.get(type_geom)
                for geom in geom_list:
                    srid = srids.get(type_geom)

                    layer_name = f"{layer_base_name}.{type_geom}"
                    layer_type = f"{QgsWkbTypes.displayString(geom.wkbType())}?crs=epsg:{srid}"
                    layer = self.get_qgs_vector_layer(layer_type, attribute_fields, group_name, layer_name, tree_item)
                                        
                    if not CreateLayersUtils.object_is_in_layer(layer, tree_item.intrasis_item.object_id, geom):
                        feature = self.create_qgs_feature(attribute_values, geom)
                        layer.dataProvider().addFeatures([feature])

    def create_qgs_feature(self, attribute_values:list, geom:QgsGeometry=None) -> QgsFeature:
        """Create a 'QgsFeature' having the provided 'attribute_values' as attributes and 'geom' as geometry (if provided)"""
        feature = QgsFeature()
        feature.setId(self.current_feature_id)
        self.current_feature_id += 1
        if geom:
            feature.setGeometry(geom)
        feature.setAttributes(attribute_values)
        return feature
    
    def get_layer_key(self, group_name:str, layer_name:str, tree_level_layer_id:int) -> str:
        """Get the layer key, used for the 'self.layers' dict"""
        layer_key = f"{group_name}||{layer_name}"
        if not self.flatten_layers:
            layer_key = f"{layer_key}||{tree_level_layer_id}"
        return layer_key
    
    def get_qgs_vector_layer(self, layer_type:str, attribute_fields:QgsFields, group_name:str, layer_name:str, tree_item:IntrasisTreeWidgetItem) -> QgsVectorLayer:
        """Get the correct 'QgsVectorLayer' in the 'self.layers' dict or create a new layer if it doesn't already exist in the dict. 
        If a new layer is created it is created as QgsVectorLayer(layer_type, layer_name, 'memory') where 'layer_type' and 'layer_name' are the provided 
        parameters, and setting 'attribute_fields' as the created layers QgsFields. If a layer is created it is added to the tree_item.layer_group.layer_list list
        and to the self.layers dict."""
        layer_key = self.get_layer_key(group_name, layer_name, tree_item.tree_level_layer_id)
                    
        layer = self.layers.get(layer_key)
        if layer is None: # The layer has not yet been created and added to the dict -> create and add before adding the feature
            layer = QgsVectorLayer(layer_type, layer_name, 'memory')
            self.layers[layer_key] = layer
            tree_item.layer_group.layer_list.append(layer)
            layer.dataProvider().addAttributes(attribute_fields)
            layer.updateFields()
        
        return layer

    def finished(self, result):
        """The result is handled by the calling class using the emitted result_done_signal signal"""
        pass
                
    def cancel(self):
        """User canceled the create layers task"""
        QgsMessageLog.logMessage(f'Task "{self.description()}" was canceled', self.message_category, Qgis.Info)
        super().cancel()