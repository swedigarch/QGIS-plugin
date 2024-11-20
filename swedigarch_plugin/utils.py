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
"""Utils module"""

import os
from typing import Tuple, Literal, Union
import struct
from enum import Enum
import sqlite3
import traceback
import psycopg2
import pandas as pd
from .utils_classes import Site
from contextlib import closing
from qgis.core import QgsProject, QgsWkbTypes, QgsCoordinateReferenceSystem, QgsDataSourceUri, QgsFeature, QgsMapLayer, QgsVectorLayer, QgsRasterLayer, QgsMapLayerType, QgsGeometry, QgsMessageLog, Qgis, QgsLayerTreeGroup
from PIL import Image, ImageDraw
from PyQt5.QtCore import Qt, QVariant, QRect
from PyQt5.QtGui import QIcon, QImage, QPixmap
from .constant import Intrasis
from .utils_classes import IconType, SymbolException
from .striprtf import rtf_to_text

OBJECTS_TABLE_NAME = "objects"
OBJECT_RELATIONS_TABLE_NAME= "object_relations"
ATTRIBUTES_TABLE_NAME = "attributes"

def get_attributes_data_for_object_id(message_log_category:str, gpkg_path:str, object_id:int) -> Union[pd.DataFrame, None]:
    """Get a data frame containing columns for attribute_label, attribute_value, attribute_unit, class, data_type for provided object_id from the attributes table in the geopackage 'gpkg_path'"""
    sql = f"SELECT attribute_label, attribute_value, attribute_unit, class, data_type FROM {ATTRIBUTES_TABLE_NAME} WHERE object_id = {object_id}"
    data_frame = get_data_frame_from_gpkg(gpkg_path, sql)

    # Check that result has correct dimensions before returning
    if len(data_frame) <=  0:
        return None
    if len(data_frame.columns) != 5:
        message = f"get_attributes_data_for_object_id: Incorrect number of columns found for object_id {object_id}"
        QgsMessageLog.logMessage(message, message_log_category, Qgis.Critical)
        print(message)
        return None

    return data_frame


def get_objects_data_for_object_id(message_log_category:str, gpkg_path:str, object_id:int) -> Union[pd.DataFrame, None]:
    """Get result set from the objects table containing columns for IntrasisId, Name, Class, SubClass, Color for provided object_id from the objects table in the geopackage 'gpkg_path'"""
    sql = f"SELECT IntrasisId, Name, Class, SubClass, Color FROM {OBJECTS_TABLE_NAME} WHERE object_id = {object_id}"
    data_frame = get_data_frame_from_gpkg(gpkg_path, sql)

    # Check that result has correct dimensions before returning
    if len(data_frame) <= 0:
        return None
    if len(data_frame) >  1:
        message = f"get_objects_data_for_object_id: More than one record found for object_id {object_id}"
        QgsMessageLog.logMessage(message, message_log_category, Qgis.Critical)
        print(message)
        return None
    if len(data_frame.columns) != 5:
        message = f"get_objects_data_for_object_id: Incorrect number of columns found for object_id {object_id}"
        QgsMessageLog.logMessage(message, message_log_category, Qgis.Critical)
        print(message)
        return None

    return data_frame

def try_fix_attribute_value(attribute_value:str, qvariant_data_type:QVariant) -> Union[Tuple[Literal[True], QVariant], Tuple[Literal[False], None]]:
    """Try to fix attribute_value so it can be converted to the QVariant data type. If successful True,
    QVariant value is returned otherwise False, None. Currently only fix QVariant.Double is supported (replace , with .)"""

    if qvariant_data_type == QVariant.Double:
        attribute_value = attribute_value.replace(',', '.')
        qvariant_attribute = QVariant(attribute_value)
        if qvariant_attribute.convert(qvariant_data_type):
            return True, qvariant_attribute

    return False, None

def get_qvariant_type_from_attribute_data_type(data_type:str) -> QVariant:
    """Returns QVariant data type based on the data_type parameter value"""
    if data_type.lower() == "integer" or data_type.lower() == "counter":
        return QVariant.Int
    elif data_type.lower() == "boolean":
        return QVariant.Bool
    elif data_type.lower() == "date":
        return QVariant.String
    elif data_type.lower() == "decimal":
        return QVariant.Double
    else:
        return QVariant.String

def get_geometries_for_object_id(gpkg_path: str, object_id: int) -> dict:
    """Get geometry dict for given object_id and geopackage 'gpkg_path', where the geometry types are the dict keys"""
    sql = f'SELECT geom, spatial_type FROM features WHERE object_id = {object_id}'
    data_frame = get_data_frame_from_gpkg(gpkg_path, sql)
    geometries = {}

    for row in data_frame.values:
        # Skip header and get the wkb
        wkb = []
        if len(row[0]) > 56: # Skip 56 bytes (Header size and Have Z and M value)
            wkb = row[0][56:]
        else: # If point object skip only 8 bytes (Point type doesn't have full geopackage header length before geometry start)
            wkb = row[0][8:]

        geom_type = row[1]
        geom = QgsGeometry()
        geom.fromWkb(wkb)

        if geom_type in geometries:
            geometries[geom_type].append(geom)
        else:
            geometries[geom_type] = [geom]

    return geometries

def get_srid_per_table_name(gpkg_path:str) -> Union[dict, None]:
    """Get geopackage srids from 'gpkg_path' as a dict where the geopackage table names are the keys"""
    sql = "SELECT table_name, srs_id FROM gpkg_geometry_columns"
    data_frame = get_data_frame_from_gpkg(gpkg_path, sql)

    if len(data_frame.values) <= 0:
        return None
    if len(data_frame.columns) != 2:
        return None

    srids = {}
    for row in data_frame.values:
        srids.update({row[0]: row[1]})

    return srids

def get_all_selected_features_and_gpkg_paths(object_id_attribute_name:str = 'object_id') -> Tuple[dict, list]:
    """Returns a dictionary of all selected features and their gpkg paths, and a list of (unique) geopackage paths for the selected features"""
    gpkg_paths = []
    selected_features = dict()
    layers = QgsProject.instance().mapLayers().values()
    for layer in layers:
        if layer.type() == QgsMapLayerType.VectorLayer:
            features = layer.selectedFeatures()
            if features is not None and features != []:
                source = layer.source()
                gpkg_path = get_path_from_gpkg_source(source)
                if gpkg_path is not None:
                    if is_intrasis_gpkg_export(gpkg_path):
                        gpkg_paths.append(gpkg_path)
                        for feature in features:
                            if feature.fieldNameIndex(object_id_attribute_name) >= 0 and feature not in selected_features:
                                selected_features.update({feature : gpkg_path})

    return selected_features, list(dict.fromkeys(gpkg_paths))

def get_data_frame_from_gpkg(gpkg_file:str, sql:str) -> pd.DataFrame:
    """Get result pandas data_frame for given sql from gpkg_file"""
    try:
        with closing(sqlite3.connect(gpkg_file)) as conn:
            data_frame = pd.read_sql(sql, conn)
        return data_frame
    except Exception as ex:
        traceback.print_exc()
        print(f"Error in get_data_frame_from_gpkg() {ex}  sql: {sql}")

def get_path_from_gpkg_source(source:str) -> str:
    """Get the path from a geopackage source. If 'source' is not a geopackage source None is returned"""
    idx = source.lower().find('.gpkg|')
    is_gpkg = idx != -1
    if is_gpkg:
        return source[0:idx+5]
    else:
        return None

def is_nan(x) -> bool:
    """Check if x is NaN"""
    return x != x

def wkb_type_to_layer(wkb_type:QgsWkbTypes) -> tuple[str,str]:
    """Convert wkbType to layer_name and filter_string"""
    layer_name = ""
    filter_string = ""
    if wkb_type == QgsWkbTypes.PointZM:
        layer_name = "Point"
        filter_string = "'POINT'"
    elif wkb_type == QgsWkbTypes.MultiPointZM:
        layer_name = "Multipoint"
        filter_string = "'MULTIPOINT'"
    elif wkb_type == QgsWkbTypes.MultiLineStringZM:
        layer_name = "Polyline"
        filter_string = "'LINESTRING','MULTILINESTRING'"
    elif wkb_type == QgsWkbTypes.MultiPolygonZM:
        layer_name = "Polygon"
        filter_string = "'POLYGON','MULTIPOLYGON'"
    else:
        raise SymbolException(f"Unknown wkb_type: {wkb_type}")
    return layer_name, filter_string

def get_used_symbol_ids(gpkg_file:str, layer_name:str) -> list:
    """List all used SymbolId"""
    symbol_ids = []
    with closing(sqlite3.connect(gpkg_file)) as conn:
        cur = conn.cursor()
        sql = f'SELECT DISTINCT SymbolId FROM {layer_name} ORDER BY SymbolId;'
        cur.execute(sql)
        data = cur.fetchall()
        symbol_ids = [rows[0] for rows in data]
    print(f'get_used_symbol_ids() symbol_ids: {symbol_ids}')
    return symbol_ids

def load_resource(file_name:str) -> str:
    """Load local resource file"""
    __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
    with open(os.path.join(__location__, file_name), encoding="utf-8") as f:
        text = f.read()
    return text

def save_text(file_name:str, text:str):
    """Save txt to file"""
    __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
    with open(os.path.join(__location__, file_name), encoding="utf-8") as f:
        f.write(text)

def execute_sql_in_gpkg(gpkg_file:str, sql:str):
    """Execute the given SQL code inte the given gpkg_file"""
    try:
        with closing(sqlite3.connect(gpkg_file)) as conn:
            conn.execute(sql)
            conn.commit()
    except Exception as ex:
        traceback.print_exc()
        print(f"Error in execute_sql_in_gpkg() {ex}  sql: {sql}")

def convert_pil_to_pixmap(image):
    """Convert PIL Image to QPixmap. Work around to avoid using PIL since since the toqpixmap() has been the source of deprecation warnings and errors in some QGIS versions."""
    if image.mode == "RGB":
        r, g, b = image.split()
        image = Image.merge("RGB", (b, g, r))
    elif image.mode == "RGBA":
        r, g, b, a = image.split()
        image = Image.merge("RGBA", (b, g, r, a))
    # Convert to raw data
    data = image.tobytes("raw", image.mode)
    q_image = QImage(data, image.size[0], image.size[1], QImage.Format_ARGB32 if image.mode == "RGBA" else QImage.Format_RGB888)
    pixmap = QPixmap.fromImage(q_image)
    return pixmap

def create_qicon_object(db_color:int, icon_type:'IconType') -> QIcon:
    """Create QIcon from image"""
    img = create_object_color_icon(db_color, icon_type)
    pixmap = convert_pil_to_pixmap(img)
    img_qicon = QIcon(pixmap)
    return img_qicon

def create_object_color_icon(db_color:int, icon_type:IconType) -> Image:
    """Creates an image with the given object color and image type."""
    try:
        icon = Image.new("RGBA", (16, 16), (255, 255, 255, 0))
        draw = ImageDraw.Draw(icon)
        rgb = struct.pack("i", db_color)

        if IconType.CIRCLE == icon_type:
            draw.ellipse([3, 3, 12, 12], fill=(rgb[0], rgb[1], rgb[2]))
            draw.ellipse([3, 3, 12, 12], fill=None, outline="Black")

        if IconType.SQUARE == icon_type:
            draw.rectangle([2, 3, 13, 14], fill=None, outline="Black")
            draw.rectangle([2, 3, 12, 13], fill=(rgb[0], rgb[1], rgb[2]))
            draw.rectangle([1, 2, 12, 13], fill=None, outline="Black")

        return icon
    except Exception as ex:
        traceback.print_exc()
        print(f"Error in create_object_color_image() {ex}")
        return None

def is_empty_string_or_none(value:str) -> bool:
    """Test if value is empty string or none"""
    if value is None or value == "":
        return True
    return False

def is_not_blank(input_string):
    """Test if the given string is Not None or empty string (spaces included)"""
    if input_string and input_string.strip():
        #input_string is not None AND is not empty or blank
        return True
    #input_string is None OR is empty or blank
    return False

def get_database_srid(conn:psycopg2.extensions.connection, falback_value:int, detailed_print_outs:bool=True) -> tuple[int,str,bool]:
    """Fetch Coordinate System srid from System object in Intrasis database"""
    try:
        sql = load_resource('sql/select_system_srid.sql')
        with conn.cursor() as cursor:
            cursor.execute(sql)
            db_value = cursor.fetchone()[0]
            if db_value is not None:
                srid = int(db_value)
                if detailed_print_outs:
                    print(f"srid: {srid}")
        return srid, None, False
    except psycopg2.errors.InsufficientPrivilege as ipex:
        if detailed_print_outs:
            print(f'InsufficientPrivilege: when trying to fetch srid: {str(ipex).rstrip()}')
        return falback_value, f'{str(ipex).rstrip()}', True
    except Exception as ex:
        traceback.print_exc()
        print(f"Error in get_database_srid() {ex}")
        return falback_value, None, False

def get_database_site(conn:psycopg2.extensions.connection, detailed_print_outs:bool) -> tuple[Site, str, bool]:
    """Fetch the site object from the database"""
    sql = load_resource('sql/select_site_object.sql')
    try:
        meta_id = get_meta_id(conn, Intrasis.CLASS_SITE_META_ID)
        sql = sql.replace("__META_ID__", f"{meta_id}")
        data_frame = pd.read_sql(sql, conn)
        return Site(conn, data_frame), None, False
    except psycopg2.errors.InsufficientPrivilege as ipex:
        if detailed_print_outs:
            print(f'InsufficientPrivilege: when trying to fetch site: {str(ipex).rstrip()}')
        return None, f'{str(ipex).rstrip()}', True
    except Exception as ex:
        traceback.print_exc()
        print(f"Error in get_database_site() {ex}")
        return None, f'{str(ex).rstrip()}', False

def get_meta_id(conn:psycopg2.extensions.connection, system_meta_id:int) -> int:
    """Lockup the system defined meta_id to get local version"""
    with conn.cursor() as cursor:
        cursor.execute(f"SELECT \"MetaId\" FROM \"SysDefs\" WHERE \"SystemId\" = {int(system_meta_id)}")
        meta_id = cursor.fetchone()[0]
    if meta_id is not None:
        return int(meta_id)
    return int(system_meta_id)

def load_spatial_ref_sys_definition(connection_string:str, srid:int) -> str:
    """Load spatial_ref_sys definition for given srid"""
    try:
        sql = f"select srtext from spatial_ref_sys where auth_name = 'EPSG' AND srid = {srid}"
        conn = psycopg2.connect(connection_string)
        db_result = pd.read_sql(sql, conn)
        return db_result.iloc[0]["srtext"]
    except Exception as ex:
        print(f"Error in load_spatial_ref_sys_definition() {ex}")

def load_attribute_def_for_class(conn:psycopg2.extensions.connection, class_id:int, sub_class_id:int = None):
    """Load classes to export"""
    try:
        sql = load_resource('sql/select_attibute_def_for_class.sql')
        if sub_class_id is None:
            sql =  sql.replace("__", f" = {class_id}")
        else:
            sql =  sql.replace("__", f" IN({class_id}, {sub_class_id})")
        #print(f"sql: {sql}")
        data_frame = pd.read_sql(sql, conn)
        return data_frame['MetaId'].str.cat(sep=', ')
    except Exception as ex:
        print(f"Error in load_attribute_def_for_class() {ex}")

def parse_sslmode(sslmode:str) -> tuple[str,str]:
    """Parase ssl mode string to value and connection string text"""
    if sslmode in ("SslPrefer", "prefer"):
        sslmode = "prefer"
        sslmode_text = " sslmode=prefer"
    elif sslmode in ("SslDisable", "disable"):
        sslmode = "disable"
        sslmode_text = " sslmode=disable"
    elif sslmode in ("SslAllow", "allow"):
        sslmode = "allow"
        sslmode_text = " sslmode=allow"
    elif sslmode in ("SslRequire", "require"):
        sslmode = "require"
        sslmode_text = " sslmode=require"
    elif sslmode in ("SslVerifyCa", "verify-ca"):
        sslmode = "verify-ca"
        sslmode_text = " sslmode=verify-ca"
    elif sslmode in ("SslVerifyFull", "verify-full"):
        sslmode = "verify-full"
        sslmode_text = " sslmode=verify-full"
    else:
        sslmode = QgsDataSourceUri.SslMode.SslDisable
        sslmode_text = ""
    return sslmode, sslmode_text

def is_intrasis_gpkg_export(gpkg_file:str) -> bool:
    """Verify that the given GeoPackage is a real 'Intrasis GeoPackage export'"""
    try:
        with closing(sqlite3.connect(gpkg_file)) as conn:
            cur = conn.cursor()
            # This tests that the metadata is correct
            cur.execute('SELECT count(*) FROM gpkg_metadata where metadata like \'%Intrasis GeoPackage export%\'')
            metadata = cur.fetchall()[0][0]
            if not metadata == 1:
                print('is_intrasis_gpkg_export() gpkg_metadata does not indicate an \'Intrasis GeoPackage export\'')
            cur.close()
            cur = conn.cursor()
            # This verifies that 10 mandatory tables are present
            sql = load_resource("sql/gpkg_is_intrasis_export.sql")
            cur.execute(sql)
            table_count = cur.fetchall()[0][0]
            if not table_count == 10:
                print(f'is_intrasis_gpkg_export() Did not fing the required 10 tables, only found {table_count}')
        return metadata == 1 and table_count == 10
    except Exception:
        # Any error/Exception means it's not an Intrasis GeoPackage
        return False

def layer_is_in_gpkg(layer:QgsMapLayer) -> tuple[bool,str]:
    """Determin if layer i stored in a GeoPackage and then return the path"""
    idx = -1
    is_gpkg = True
    gpkg_path = ""
    source = layer.source()
    if isinstance(layer, QgsVectorLayer):
        idx = source.lower().find('.gpkg|')
        is_gpkg = idx != -1
        if is_gpkg:
            gpkg_path = source[0:idx+5]
    elif isinstance(layer, QgsRasterLayer):
        idx = source.lower().find('.gpkg:')
        is_gpkg = idx != -1
        if is_gpkg:
            gpkg_path = source[0:idx+5]
            if gpkg_path.upper().startswith('GPKG:'):
                gpkg_path = gpkg_path[5:]

    return is_gpkg, gpkg_path

def find_geo_packages_from_selected_features() -> dict:
    """Returns a list of (unique) geopackage paths for all geopackages that have at least one selected feature"""
    object_id_field_name = 'object_id'
    gpkg_files = {}
    layers = QgsProject.instance().mapLayers().values()
    for layer in layers:
        if layer.type() == QgsMapLayerType.VectorLayer:
            features = layer.selectedFeatures()
            if features is not None and features != []:
                is_gpkg, gpkg_path = layer_is_in_gpkg(layer)
                if not is_gpkg or not is_intrasis_gpkg_export(gpkg_path):
                    continue
                num_selected_features = get_number_of_selected_features_without_duplicates(features, object_id_field_name)
                if gpkg_path not in gpkg_files:
                    gpkg_files[gpkg_path] = num_selected_features
                else:
                    gpkg_files[gpkg_path] = gpkg_files[gpkg_path] + num_selected_features

    return gpkg_files

def get_number_of_selected_features_without_duplicates(features:[QgsFeature], object_id_field_name:str) -> int:
    """Returns number of selected features after duplicates (features with same object_id) has been removed"""
    object_id_list = []
    for feature in features:
        fields = feature.fields()

        index_object_id = fields.lookupField(object_id_field_name)
        if index_object_id < 0: # The feature has no object_id attribute, continue to the next feature
            continue
        object_id = feature.attribute(object_id_field_name)
        if object_id not in object_id_list: # Avoid duplicates
            object_id_list.append(object_id)

    return len(object_id_list)

def find_geo_packages() -> dict:
    """Find all GeoPackages we have loaded data from, and a count of the number of layer loaded from each."""
    layers = QgsProject.instance().mapLayers().values()
    #print(f'{len(layers)} Layers to check')
    gpkg_files = {}
    for layer in layers:
        #source = layer.source()
        is_gpkg, gpkg_path = layer_is_in_gpkg(layer)
        #print(f'Name: \"{layer.name()}\" is_gpkg: {is_gpkg} path: {gpkg_path}')
        if not is_gpkg:
            continue

        if gpkg_path not in gpkg_files:
            gpkg_files[gpkg_path] = 1
        else:
            gpkg_files[gpkg_path] = gpkg_files[gpkg_path] + 1
    return gpkg_files

def get_data_from_gpkg(gpkg_file:str, return_type:int, no_subclass_string:str='No SubClass') -> [str,str,str]:
    """Fetch data of give type from GeoPackage'"""
    try:
        with closing(sqlite3.connect(gpkg_file)) as conn:
            cur = conn.cursor()

            #Ta fram kolumner via table_info kommandot
            if return_type == 0:
                cur.execute('PRAGMA table_info(objects)')
                table_description = cur.fetchall()
                #print([fields[1] for fields in table_description])
                cur.close()

            #Ta fram data "Class"
            if return_type == 1:
                cur.execute('SELECT DISTINCT Class FROM objects')
                data = cur.fetchall()
                #print([rows[0] for rows in data])
                cur.close()

            #Ta fram data objects-tabell filtrerad på Class
            if return_type == 2:
                cur.execute('SELECT * FROM attributes WHERE object_id IN (SELECT object_id FROM objects WHERE Class IN (\'Prov\'))')
                data = cur.fetchall()
                #print(data)
                cur.close()
            #Ta fram data till pandas dataframe
            if return_type == 3:
                dataframe = pd.read_sql_query('SELECT * FROM attributes WHERE object_id IN (SELECT object_id FROM objects WHERE Class IN (\'Prov\'))', conn)
                return dataframe
            #Ta fram klasser, subklasser
            if return_type == 4:
                #för att få översättningsstöd
                #no_subclass_string = '\'test No SubClass\''
                #cur.execute('SELECT Class, group_concat(SubClasses) AS SubClass FROM ( SELECT DISTINCT Class, SubClass || \'\' as SubClasses FROM objects) GROUP BY Class')
                #för att även få med NULL som 'NULL', 20230515: ändrat till | som separator
                #cur.execute('SELECT Class, group_concat(SubClasses, \'|\') AS SubClass FROM ( SELECT DISTINCT Class, CASE WHEN SubClass IS NULL THEN \'No SubClass\' ELSE SubClass END  as SubClasses FROM objects) GROUP BY Class')
                #print('SELECT Class, group_concat(SubClasses, \'|\') AS SubClass FROM ( SELECT DISTINCT Class, CASE WHEN SubClass IS NULL THEN \''+ no_subclass_string +'\' ELSE SubClass END  as SubClasses FROM objects) GROUP BY Class')
                cur.execute('SELECT Class, group_concat(SubClasses, \'|\') AS SubClass FROM ( SELECT DISTINCT Class, CASE WHEN SubClass IS NULL THEN \''+ no_subclass_string +'\' ELSE SubClass END  as SubClasses FROM objects) GROUP BY Class')


                data_classes_subclasses = cur.fetchall()
                #print(data_classes_subclasses)
                cur.execute('SELECT DISTINCT Class FROM objects')
                data = cur.fetchall()
                data_classes = [rows[0] for rows in data]
                cur.execute('SELECT DISTINCT SubClass FROM objects')
                data_subclasses = cur.fetchall()
                cur.close()
                return [data_classes_subclasses, data_classes, data_subclasses]
    except Exception as ex:
        print(f"Error in get_data_from_gpkg {ex}")
        return False

def expand_group(group) -> None:
    '''Expands group and the contents inside the group, all childgroups and all layers'''
    print(group)
    root = QgsProject.instance().layerTreeRoot()
    node_of_group = root.findGroup(group)
    node_of_group.setExpanded(False) #Must be set false first time or it will not work?
    node_of_group.setExpanded(True)
    child_groups = get_child_groups(node_of_group)
    for group in child_groups:
        #print(group.name())
        group.setExpanded(True)
    layers = node_of_group.findLayers()
    for layer in layers:
        layer.setExpanded(True)

def get_child_groups(group):
    '''Get all child groups'''
    # iterate over the children of the group node
    child_groups = []
    for child in group.children():
    # check if the child is a group node
        if isinstance(child, QgsLayerTreeGroup):
        # append the child group to the list
            child_groups.append(child)
        # recursive call to get nested groups
            get_child_groups(child)
    return child_groups
