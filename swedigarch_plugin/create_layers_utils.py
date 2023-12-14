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
"""Utils module for creating qgis layers"""
from typing import Tuple, Union
from qgis.core import QgsMessageLog, QgsField, QgsFields, Qgis, QgsExpression, QgsFeatureRequest, QgsVectorLayer, QgsGeometry
from PyQt5.QtCore import QVariant
import traceback
import pandas as pd
from . import utils as Utils
    
MESSAGE_CATEGORY = 'CreateLayers'

def get_attribute_fields_and_values(gpkg_path:str, object_id:int, class_name:str, subclass_name:str, class_subclass_attributes:dict) -> Tuple[QgsFields, list]:
    """Get a QgsFields list with fields, having correct data types, for provided class/subclass combination and a list of corresponding attribute values for provided object_id"""
    attribute_fields, attribute_names = get_attribute_fields_for_class_subclass_combination(gpkg_path, class_name, subclass_name, class_subclass_attributes)
    attribute_values = get_attribute_values(gpkg_path, object_id)
    matched_attribute_values = match_attribute_values_with_attribute_names(attribute_names, attribute_values)
    
    return attribute_fields, matched_attribute_values

def get_attribute_field_key(attribute_label:str, is_class:str, data_type:str, is_unit:bool) -> str:
    """Return key for attribute field"""
    unit = ""
    if is_unit:
        unit = "_Enhet"

    return f"{attribute_label}_{is_class}_{data_type}{unit}"

def get_attribute_list_for_class_subclass_combination(gpkg_path:str, 
                                                        class_name:str, 
                                                        subclass_name:str) -> Union[pd.DataFrame, None]:
    """Get a pandas data frame of all attributes (attributes columns attribute_label, data_type and class) for a class/sublcass combination"""
    subclass_where_clause = f"= '{subclass_name}'"
    if Utils.is_empty_string_or_none(subclass_name):
        subclass_where_clause = "IS NULL"
    
    sql = f"SELECT attribute_label, attribute_unit, class, data_type FROM {Utils.ATTRIBUTES_TABLE_NAME} WHERE object_id IN (SELECT object_id FROM (SELECT object_id, COUNT(*) AS num_attributes FROM attributes WHERE object_id IN (SELECT object_id FROM objects WHERE Class = '{class_name}' AND SubClass {subclass_where_clause}) GROUP BY object_id ORDER BY num_attributes DESC LIMIT 1) t)"
    data_frame_attributes = Utils.get_data_frame_from_gpkg(gpkg_path, sql)
    
    if data_frame_attributes is None or data_frame_attributes.empty:
        return None
    
    return data_frame_attributes

def get_attribute_fields_for_class_subclass_combination(gpkg_path:str, class_name:str, subclass_name:str, class_subclass_attributes:dict) -> Tuple[QgsFields, list]:
    """Get a list of all attribute fields for a class/subclass combination and a list of attribute keys. Attributes from attributes table are ordered by attribute_label, class, data_type columns"""
    # Only get attribute fields by querying the geopackage if it hasn't already been done for this combination of class/subclass
    key_attributes_dict = f"{class_name}_{subclass_name}"
    if key_attributes_dict in class_subclass_attributes:
        row = class_subclass_attributes[key_attributes_dict]
        return row[0], row[1]
    
    attribute_fields = QgsFields()
    attribute_names = []
    attributes = get_attribute_list_for_class_subclass_combination(gpkg_path, class_name, subclass_name)
    
    attribute_fields.append(QgsField('IntrasisId', QVariant.Int))
    attribute_names.append('IntrasisId')
    attribute_fields.append(QgsField('object_id', QVariant.Int))
    attribute_names.append('object_id')
    attribute_fields.append(QgsField('name', QVariant.String))
    attribute_names.append('name')
    attribute_fields.append(QgsField('class', QVariant.String))
    attribute_names.append('class')
    attribute_fields.append(QgsField('subclass', QVariant.String))
    attribute_names.append('subclass')

    if attributes is None:
        # Store the attribute fields for this combination of class/subclass in a dictonary for next time it is needed
        class_subclass_attributes[key_attributes_dict] = (attribute_fields, attribute_names)
        return attribute_fields, attribute_names
    
    attributes_sorted = attributes.sort_values(by=['attribute_label','class','data_type'])
    
    for idx, row in attributes_sorted.iterrows():
        attribute_name = row['attribute_label']
        attribute_unit = row['attribute_unit']
        data_type = row['data_type']
        is_class_attribute = row['class']
        key = get_attribute_field_key(attribute_name, is_class_attribute, data_type, False)
        qvariant_type = Utils.get_qvariant_type_from_attribute_data_type(data_type)
        field = QgsField(attribute_name, qvariant_type)
        field.setName(f"{attribute_name}_{idx}")
        field.setAlias(attribute_name)
        attribute_fields.append(field)
        attribute_names.append(key)
        if not Utils.is_empty_string_or_none(attribute_unit):
            field = QgsField( f"{attribute_name}_Enhet", QVariant.String )
            field.setName(f"{attribute_name}_Enhet_{idx}")
            field.setAlias(f"{attribute_name}_Enhet")
            attribute_fields.append(field)
            attribute_names.append(get_attribute_field_key(attribute_name, is_class_attribute, data_type, True))

    # Store the attribute fields for this combination of class/subclass in a dictonary for next time it is needed
    class_subclass_attributes[key_attributes_dict] = (attribute_fields, attribute_names)
    return attribute_fields, attribute_names

def get_attribute_values(gpkg_path:str, object_id:int) -> Union[list, None]:
    """Get attribute field values from objects and attributes table for given 'object_id'. Attributes from attributes table are ordered by attribute_label, class, data_type columns"""
    attribute_values = []

    # Objects table
    object_attributes = Utils.get_objects_data_for_object_id(MESSAGE_CATEGORY, gpkg_path, object_id)
    if object_attributes is None:
        return None
    
    try:
        attribute_values.append(('IntrasisId', int(object_attributes["IntrasisId"][0])))
        attribute_values.append(('object_id', object_id))
        if Utils.is_empty_string_or_none(object_attributes["SubClass"][0]):
            attribute_values.append(('name', None))
        else:
            attribute_values.append(('name', str(object_attributes["Name"][0])))
        attribute_values.append(('class', str(object_attributes["Class"][0])))
        if Utils.is_empty_string_or_none(object_attributes["SubClass"][0]):
            attribute_values.append(('subclass', None))
        else:
            attribute_values.append(('subclass', str(object_attributes["SubClass"][0])))

    except Exception as ex:
        traceback.print_exc()
        print(f"Error in get_attribute_values() {ex}")
        return None

    # Attributes table
    attributes = Utils.get_attributes_data_for_object_id(MESSAGE_CATEGORY, gpkg_path, object_id)
    if attributes is None: #If there are no rows in the attributes table for current object_id return
        return attribute_values
    
    attributes_sorted = attributes.sort_values(by=['attribute_label','class','data_type'])
            
    for _, row in attributes_sorted.iterrows():
        attribute_name = row['attribute_label']
        attribute_unit = row['attribute_unit']
        attribute_value = row['attribute_value']
        data_type = row['data_type']
        is_class_attribute = row['class']

        qvariant_type = Utils.get_qvariant_type_from_attribute_data_type(data_type)

        if Utils.is_empty_string_or_none(attribute_value): # Attribute is empty - set value to None
            attribute_value = None
        else:
            # Convert attribute value to desired data_type
            qvariant_value = QVariant(attribute_value)
            if qvariant_value.convert(qvariant_type):
                attribute_value = qvariant_value
            else: # Attribute value could not be converted. Try to fix, otherwise send out message and set to None
                fixed, fixed_value = Utils.try_fix_attribute_value(attribute_value, qvariant_type)
                if fixed:
                    attribute_value = fixed_value
                else:
                    message = f"Attribute value {attribute_value} for attribute {attribute_name} could not be converted to {data_type} for object_id {object_id}. Value set to NULL in layer export."
                    QgsMessageLog.logMessage(message, MESSAGE_CATEGORY, Qgis.Critical)
                    attribute_value = None

        attribute_values.append((get_attribute_field_key(attribute_name, is_class_attribute, data_type, False), attribute_value))

        if not Utils.is_empty_string_or_none(attribute_unit):
            attribute_values.append((get_attribute_field_key(attribute_name, is_class_attribute, data_type, True), attribute_unit))
            
    return attribute_values

def match_attribute_values_with_attribute_names(attribute_names:list, attribute_values:list) -> list:
    """Match the sorted attribute values and keys lists where attribute_values is a list of tuples consisting of (key, value), creating null attributes if there are missing 
    attributes. Both lists must be sorted the same way."""
    checked_values = []
    idx = 0
    max_idx = len(attribute_values)
    
    for attr_name in attribute_names:
        if idx < max_idx:
            row = attribute_values[idx]
            if row[0] == attr_name:
                checked_values.append(row[1])
                idx += 1
            else:
                checked_values.append(None)
        else:
            checked_values.append(None)
    
    return checked_values

def object_is_in_layer(layer: QgsVectorLayer, object_id: int, geom:QgsGeometry = None) -> bool:
    """Return True if given 'object_id' is in given 'layer', False otherwise. If geometry 'geom' is provided the geometries of the features in 
    layer is compared to 'geom' and True is only returned if both the 'object_id' and the geometries are the equal, and False otherwise"""
    # If the layer is None the object is not in the layer
    if layer is None:
        return False
    
    #Get features based on selected object id
    expr = QgsExpression(f"object_id={object_id}")
    features = layer.dataProvider().getFeatures(QgsFeatureRequest(expr))
    # If the layer has no features with object_id return False
    if not features:
        return False

    # Check the geometries to decide if the found features are equal to object_id and geom
    for feature in features:
        if feature.hasGeometry() and geom is not None:
                if geom.asWkt() == feature.geometry().asWkt():
                    return True
        # If there are no geometries to check - return True
        else:
            return True

    # Did not find any features having the provided object_id and geom
    return False