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
"""Export Utils module"""
from datetime import datetime
from dataclasses import dataclass
import os
import tempfile
import sqlite3
import traceback
import pandas as pd
import psycopg2
from contextlib import closing
from qgis.core import QgsCoordinateReferenceSystem, QgsRectangle
from .striprtf import rtf_to_text
from . import utils as Utils

@dataclass
class Raster:
    """Raster file, for Intrasis Raster GeoObject"""
    def __init__(self, temp_file:str, row):
        self.temp_file = temp_file
        self.intrasis_id = row.PublicId
        self.geo_object_id = row.GeoObjectId
        self.srid = row.srid
        self.length = row.length


def update_features_geometry_type(gpkg_file:str):
    """Function to update geometry type after layer export, to allow QGIS to se the separate layer types in features."""
    with closing(sqlite3.connect(gpkg_file)) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE gpkg_geometry_columns SET geometry_type_name = 'GEOMETRY'")
        conn.commit()
        cur.close()

def save_layer_style(gpkg_file:str, create_table:bool, layer_name:str, qml:str, detailed_print_outs:bool=True) -> None:
    """Save layer symbols style to layer_styles table"""
    try:
        if detailed_print_outs:
            print(f"save_layer_style({gpkg_file}, {create_table}, {layer_name})")
        with closing(sqlite3.connect(gpkg_file)) as conn:
            cur = conn.cursor()
            #print(f"save_layer_style() Connected to SQLite {gpkg_file}  layer_name: {layer_name}")
            if create_table:
                sql = Utils.load_resource("sql/create_layer_styles_table.sql")
                cur.execute(sql)
                conn.commit()
                cur = conn.cursor()
            cur.execute("INSERT INTO layer_styles (f_table_catalog, f_table_schema, f_table_name, f_geometry_column, styleName, styleQML, useAsDefault, description, owner, ui) VALUES('', '', ?, 'geom', ?, ?, true, 'Default Intrasis style', '', '')",
                        (layer_name, layer_name, qml))
            conn.commit()
            cur.close()
    except Exception as ex:
        traceback.print_exc(ex)
        print(f"Error in save_layer_style() {ex}")

def add_geometry_type_view(gpkg_file:str, ext:QgsRectangle, layer_name:str, srid:int):
    """Create View to features table for given geometry_type and define it in the GPKG package to make it work"""
    try:
        with closing(sqlite3.connect(gpkg_file)) as conn:
            cur = conn.cursor()
            cur.execute(f"CREATE VIEW {layer_name} AS SELECT f.fid, o.IntrasisId, f.object_id, o.Name, o.Class, o.SubClass, f.SymbolId, f.GeoObjectId, f.spatial_type, f.geom FROM features f JOIN objects o ON f.object_id = o.Object_id AND spatial_type = '{layer_name}'")
            if layer_name == "Point":
                cur.execute(f"INSERT INTO gpkg_geometry_columns VALUES('Point', 'geom', 'POINT', {srid}, 1, 1)")
            if layer_name == "Multipoint":
                cur.execute(f"INSERT INTO gpkg_geometry_columns VALUES('Multipoint', 'geom', 'MULTIPOINT', {srid}, 1, 1)")
            elif layer_name == "Polyline":
                cur.execute(f"INSERT INTO gpkg_geometry_columns VALUES('Polyline', 'geom', 'MULTILINESTRING', {srid}, 1, 1)")
            elif layer_name == "Polygon":
                cur.execute(f"INSERT INTO gpkg_geometry_columns VALUES('Polygon', 'geom', 'MULTIPOLYGON', {srid}, 1, 1)")
            conn.commit()

            cur = conn.cursor()
            cur.execute("INSERT INTO gpkg_contents VALUES(?, 'features', ?, '', datetime(), ?, ?, ?, ?, ?)",
                        (layer_name, layer_name, ext.xMinimum(), ext.yMinimum(), ext.xMaximum(), ext.yMaximum(), srid))
            conn.commit()
            cur.close()
    except Exception as ex:
        traceback.print_exc()
        print(f"Error in add_geometry_type_view() {ex}")


def if_missing_create_gpkg_extensions(gpkg_file:str):
    """Create table gpkg_extensions if it is missing"""
    try:
        with closing(sqlite3.connect(gpkg_file)) as conn:
            cur = conn.cursor()
            sql = Utils.load_resource('sql/create_gpkg_extensions_table.sql')
            cur.execute(sql)
            conn.commit()
            cur.close()
    except Exception as ex:
        traceback.print_exc()
        print(f"Error in add_geometry_type_view() {ex}")


def insert_spatial_ref_sys_definition(connection_string:str, gpkg_file:str, srid:int):
    """insert spatial_ref_sys for give srid"""
    try:
        srtext = Utils.load_spatial_ref_sys_definition(connection_string, srid)
        #print(f"srtext: {srtext}")
        crs = QgsCoordinateReferenceSystem(f"EPSG:{srid}")
        with closing(sqlite3.connect(gpkg_file)) as conn:
            cur = conn.cursor()
            sql = f"INSERT INTO gpkg_spatial_ref_sys VALUES('{crs.description()}', {srid}, 'EPSG', {srid}, '{srtext}', '')"
            print("sql: {sql}")
            cur.execute(sql)
            conn.commit()
            cur.close()
    except Exception as ex:
        traceback.print_exc()
        print(f"Error in insert_spatial_ref_sys_definition() {ex}")


def store_attributes(cur:sqlite3.Cursor, data_frame:pd.DataFrame):
    """Store attributes from loaded data_frame (class [subClass]) to features and attributes table"""
    try:
        sql = "UPDATE objects SET attributes = ? WHERE object_id = ?"
        sql_insert = "INSERT INTO attributes (object_id, attribute_label, attribute_value, attribute_unit, class, data_type) VALUES(?, ?, ?, ?, ?, ?)"

        grouped = data_frame.groupby(["object_id"])
        for object_id, group in grouped:
            attributes = ""
            values = []
            current_object_id = 0
            for row in group.itertuples(index=False):
                if current_object_id == 0:
                    current_object_id = row.object_id
                if row.Value is not None:
                    value = row.Value
                else:
                    value = ""
                if row.LongText and row.Text is not None:
                    try:
                        value = rtf_to_text(row.Text)
                    except UnicodeEncodeError as ex:
                        traceback.print_exc()
                        print(f"Error in rtf_to_text() object_id: {object_id} {ex}")
                        value = "<invalid rtf>"
                    attr_value = f"{row.Label}: {value}"
                    cur.execute(sql_insert, (row.object_id, row.Label, value, '', row.Class, row.DataType))
                elif Utils.is_empty_string_or_none(row.Unit):
                    attr_value = f"{row.Label}: {value}"
                    cur.execute(sql_insert, (row.object_id, row.Label, value, '', row.Class, str(row.DataType)))
                else:
                    attr_value = f"{row.Label}: {value} {row.Unit}"
                    cur.execute(sql_insert, (row.object_id, row.Label, value, row.Unit, row.Class, row.DataType))
                values.append(attr_value)
            attributes = ','.join(values)
            cur.execute(sql, (attributes, current_object_id))
    except Exception as ex:
        traceback.print_exc()
        print(f"Error in store_attributes() {ex}")
        cur.execute("ROLLBACK;")

def fetch_and_save_raster_file(conn:psycopg2.extensions.connection, row) -> Raster:
    """Fetch and save raster to temp file"""
    try:
        sql = f"SELECT ST_AsGDALRaster(the_raster, 'GTiff') as rasttiff FROM \"GeoObject\" WHERE \"ObjectId\" = {row.GeoObjectId}"
        cursor = conn.cursor()
        cursor.execute(sql)
        raster = cursor.fetchone()[0]
        temp_file = ""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            #print(f"temp file: {tmp.name}" )
            tmp.write(raster)
            temp_file = tmp.name
        new_temp_file = f"{temp_file}.tiff"
        os.rename(temp_file, new_temp_file)
        return Raster(new_temp_file, row)
    except Exception as ex:
        traceback.print_exc()
        print(f"Error in fetch_and_save_raster_file() {ex}")
        return None

def insert_gpkg_relation(gpkg_file:str, base_table:str, base_column:str, rel_table:str, rel_column:str, rel_name:str, mapping_name:str):
    """Insert row into table gpkgext_relations"""
    sql = f"INSERT INTO gpkgext_relations (base_table_name, base_primary_column, related_table_name, related_primary_column, relation_name, mapping_table_name) VALUES('{base_table}', '{base_column}', '{rel_table}', '{rel_column}', '{rel_name}', '{mapping_name}')"
    with closing(sqlite3.connect(gpkg_file)) as conn:
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        cur.close()

def create_geometry_to_geometry_relations(gpkg_file:str, geometry1:str, geometry2:str, detailed_print_outs:bool=True):
    """Create and populate geometry to geometry relations table"""
    sql = Utils.load_resource('sql/create_object_relations_table.sql')
    rel_table_name = f"{geometry1.lower()}_{geometry2.lower()}_relations"
    sql = sql.replace("object_relations", rel_table_name)
    Utils.execute_sql_in_gpkg(gpkg_file, sql) # Create new geometry1 to geometry2 relations table
    sql = f"INSERT INTO {rel_table_name} (base_id, related_id, base_text, related_text) SELECT base_id, related_id, base_text, related_text FROM object_relations WHERE base_id IN (SELECT object_id FROM {geometry1}) AND related_id IN(SELECT object_id FROM {geometry2})"
    Utils.execute_sql_in_gpkg(gpkg_file, sql) # Populate relations table with data from big object_relations table
    if detailed_print_outs:
        print(f"{geometry1} to {geometry2} relations table {rel_table_name} created")
    insert_gpkg_relation(gpkg_file, geometry1, "object_id", geometry2, "object_id", "features", rel_table_name)

def create_log_file_name(folder_name:str, pre_name:str) -> str:
    """Create a log filename based on given parameters and current timestamp"""
    now = datetime.now()
    date_tag = now.strftime('%Y-%m-%d_%H-%M-%S')
    log_filename = os.path.join(folder_name, f'{pre_name}_{date_tag}.log')
    return log_filename
