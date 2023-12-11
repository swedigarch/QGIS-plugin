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
"""export_geopackage_to_csv"""
import sqlite3
from contextlib import closing
import psycopg2
import pandas as pd
import os
import csv
import tempfile
import zipfile
import shutil
from pathlib import Path
from osgeo import gdal
from osgeo import ogr
import traceback
from time import sleep
from PyQt5.QtCore import QDir, QFile
from qgis.core import QgsProject, QgsVectorLayer, QgsRasterLayer, QgsRasterPipe, QgsDataSourceUri, QgsWkbTypes, QgsVectorFileWriter, QgsRasterFileWriter, QgsLayerMetadata, QgsCoordinateReferenceSystem, QgsCoordinateTransformContext
from . import utils as Utils
from .constant import Intrasis, RetCode, WriterError

def export_geopackage_to_csv(gpkg_file:str) -> tuple[RetCode, str, str]:
    """Export given GeoPackage to CSV files, packed in .zip file"""
    try:
        if QFile(gpkg_file).exists() is False:
            print(f'GeoPackage: {gpkg_file} does not exist')
            return -1, None, None

        export_folder = os.path.dirname(gpkg_file)

        conn = sqlite3.connect(gpkg_file)
        cursor = conn.cursor()
        cursor.execute('SELECT table_name FROM gpkg_contents where data_type = \'features\'')
        records = cursor.fetchall()
        cursor.close()
        print(f'Found {len(records)} Features to export')
        features = [item[0] for item in records]
        print(f'Features {features}')
        conn.close()

        db_name = Path(gpkg_file).stem
        output_filename = os.path.join(export_folder, f"{db_name.lower()}")

        to_delete_files = []

        # Create a temporary folder to create the files in before compressing them all to a .zip file
        with tempfile.TemporaryDirectory() as tmpdirname:
            # Export feature tables
            for feature in features:
                output_file = os.path.join(tmpdirname, f"{feature.lower()}.csv")
                print(f'exporting layer {feature}')
                include_fid = feature != 'project_information'
                print(f'feature: {feature} include_fid: {include_fid}')
                export_layer_view(gpkg_file, feature, output_file, include_fid)
                if feature != 'project_information':
                    to_delete_files.append(f"{feature.lower()}.csv")

            output_file = os.path.join(tmpdirname, "features.csv")
            export_features(features, tmpdirname, output_file)

            with closing(sqlite3.connect(gpkg_file)) as conn:
                # Export plain tables
                export_table(conn, 'attributes', tmpdirname)
                export_table(conn, 'attribute_relations', tmpdirname)
                export_table(conn, 'objects', tmpdirname)
                export_table(conn, 'object_relations', tmpdirname)
                conn.commit()

            # write documentation.txt
            csv_doc = Utils.load_resource('csv_documentation.txt')
            csv_doc_fileame = os.path.join(tmpdirname, "documentation.txt")
            f = open(csv_doc_fileame, "w", encoding='UTF-8')
            f.write(csv_doc)
            f.close()

            for file in to_delete_files:
                file_name = os.path.join(tmpdirname, file)
                if QFile(file_name).exists():
                    QFile.remove(file_name)
            shutil.make_archive(output_filename, 'zip', tmpdirname)

        print(f'GeoPackage {gpkg_file} (CSV) exported to {output_filename}.zip')
        return RetCode.EXPORT_OK, None, f'{output_filename}.zip'

    except Exception as err:
        traceback.print_exc()
        error_msg = f'Exception in export_geopackage_to_csv(): {err}'
        print(error_msg)
        return RetCode.UNKNOWN_ERROR, error_msg, None

def export_features(features:[str], tmpdirname:str, output_file:str) -> None:
    """Export all features to combined features CSV"""
    print('Exporting table features')
    with open(output_file, 'w', encoding='UTF-8', newline='') as file:
        writer = csv.writer(file, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        headers_writen = False
        exclude_column_indices = [0] # Remove fid
        for feature in features:
            if feature == 'project_information':
                continue

            view_csv_file = os.path.join(tmpdirname, f"{feature.lower()}.csv")
            with open(view_csv_file, 'r', encoding='UTF-8', newline='') as in_csv:
                csv_reader = csv.reader(in_csv, delimiter=';')
                if headers_writen:
                    next(csv_reader)
                else:
                    headers_writen = True
                writer.writerows(
                    [col for idx, col in enumerate(row)
                    if idx not in exclude_column_indices]
                    for row in csv_reader)

def export_layer_view(gpkg_file:str, layer_name:str, output_file:str, include_fid:bool = True) -> None:
    """Export given layer view to CSV"""
    gpkg_ds = ogr.Open(gpkg_file, 0)
    layer = gpkg_ds.GetLayerByName(layer_name)
    with open(output_file, 'w', encoding='UTF-8', newline='') as file:
        writer = csv.writer(file, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        columns = []
        #print(f'export_layer_view() layer_name: {layer_name} include_fid: {include_fid}')
        if include_fid:
            columns.append('fid')
        layer_def = layer.GetLayerDefn()
        field_count = layer_def.GetFieldCount()
        have_pk = False
        idxPk = -1
        for i in range(field_count):
            field_def = layer_def.GetFieldDefn(i)
            name = field_def.GetName()
            if include_fid or name != 'pk':
                columns.append(name)
            elif name == 'pk':
                have_pk = True
                idxPk = i

        columns.append('geom')
        # write column headers
        writer.writerow(columns)

        fid = 0
        for ft in layer:
            values = []
            if include_fid:
                values.append(str(fid))
                fid += 1
            for idx in range(field_count):
                if not have_pk or idxPk != idx:
                    values.append(str(ft.GetField(idx)))

            geom = ft.GetGeometryRef()
            wkt = geom.ExportToWkt()
            values.append(wkt)
            writer.writerow(values)
    gpkg_ds = None

def export_table(conn:sqlite3.Connection, table_name:str, output_dir:str) -> None:
    """Export plain table to CSV"""
    print(f'Exporting table {table_name}')
    output_file = os.path.join(output_dir, f"{table_name.lower()}.csv")
    db_df = pd.read_sql_query(f'SELECT * FROM {table_name}', conn)
    db_df.to_csv(output_file, index=False)
