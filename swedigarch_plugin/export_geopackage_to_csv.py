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
"""export_geopackage_to_csv"""
from .tempfile import TemporaryDirectory
import sqlite3
from contextlib import closing
import psycopg2
import pandas as pd
import os
import csv
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
        db_name = os.path.splitext(os.path.basename(gpkg_file))[0]
        tmpfolder = TemporaryDirectory(prefix=f'{db_name}_', ignore_cleanup_errors=True)
        tmpdirname = tmpfolder.name
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

        archive_file = f'{output_filename}.zip'
        threadsafe_make_archive(archive_file, tmpdirname)

        try:
            #print(f'Cleanup tmpfolder, archive_file: {archive_file} tmpdirname: {tmpdirname}')
            tmpdirname = None
            tmpfolder.cleanup()
            tmpfolder = None
        except Exception:
            pass

        print(f'GeoPackage {gpkg_file} (CSV) exported to {archive_file}')
        return RetCode.EXPORT_OK, None, f'{output_filename}.zip'

    except Exception as err:
        traceback.print_exc()
        error_msg = f'Exception in export_geopackage_to_csv({gpkg_file}): {err}'
        print(error_msg)
        return RetCode.UNKNOWN_ERROR, error_msg, None

def threadsafe_make_archive(zip_name: str, path: str):
    """Thread safe alternative to shutil.make_archive"""
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(path):
            for file in files:
                zip_file.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), path))

def export_features(features:list[str], tmpdirname:str, output_file:str) -> None:
    """Export all features to combined features CSV"""
    print('Exporting table features')

    csv.field_size_limit(2500000)
    with open(output_file, 'w', encoding='UTF-8', newline='') as file:
        writer = csv.writer(file, delimiter=';', quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
        headers_writen = False
        for feature in features:
            if feature == 'project_information':
                continue

            print(f'export_features() feature: {feature}')
            view_csv_file = os.path.join(tmpdirname, f"{feature.lower()}.csv")
            with open(view_csv_file, 'r', encoding='UTF-8', newline='') as in_csv:
                csv_reader = csv.reader(in_csv, delimiter=';')
                if headers_writen:
                    next(csv_reader)
                else:
                    headers_writen = True

                first_row = True
                for row in csv_reader:
                    if not first_row:
                        new_row = []
                        # Remove fid by starting att idx 1
                        new_row.append(int(row[1]))
                        new_row.append(int(row[2]))
                        new_row.append(row[3])
                        new_row.append(row[4])
                        new_row.append(row[5])
                        if row[6] is None or row[6] == 'None': # SymbolId is NULL in Intrasis DB
                            #print(f'row[1]: {row[1]} row[2]: {row[2]}')
                            new_row.append(-1)
                        else:
                            new_row.append(int(row[6]))
                        new_row.append(int(row[7]))
                        new_row.append(row[8])
                        new_row.append(row[9])
                    else:
                        new_row = row[1:]
                    first_row = False
                    writer.writerow(new_row)


def export_layer_view(gpkg_file:str, layer_name:str, output_file:str, include_fid:bool = True) -> None:
    """Export given layer view to CSV"""
    gpkg_ds = ogr.Open(gpkg_file, 0)
    layer = gpkg_ds.GetLayerByName(layer_name)
    with open(output_file, 'w', encoding='UTF-8', newline='') as file:
        writer = csv.writer(file, delimiter=';', quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
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
    db_df.to_csv(output_file, index=False, sep=';', quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
