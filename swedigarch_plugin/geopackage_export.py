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
"""geopackage_export"""
from time import sleep
from .utils_classes import Site
import os
import io
import gc
import sqlite3
from contextlib import closing
from datetime import datetime
import traceback
import psycopg2
import pandas as pd
from osgeo import gdal
from PyQt5.QtCore import QDir, QFile
from typing import Callable
from qgis.core import QgsProject, QgsVectorLayer, QgsRasterLayer, QgsRasterPipe, QgsRectangle, QgsDataSourceUri, QgsWkbTypes, QgsVectorFileWriter, QgsRasterFileWriter, QgsLayerMetadata, QgsCoordinateReferenceSystem, QgsCoordinateTransformContext
from swedigarch_plugin.symbol_builder import SymbolBuilder
from swedigarch_plugin import export_utils
from .symbol_builder import SymbolBuilder
from . import utils as Utils
from .constant import Intrasis, RetCode, WriterError

def export_to_geopackage(host:int, port:int, user_name:str, password:str, databases:[str], export_folder:str, overwrite:bool, csv:bool, callback:Callable = None, detailed_print_outs:bool = True, log_file:io.TextIOWrapper = None):
    """Main GeoPackage export function, also can run CSV export if csv is True"""
    export_ok_count = 0
    if callback is None:
        print("callback saknas!")
        return RetCode.ARGUMENT_ERROR, export_ok_count

    rights_error = False
    # This controlls if all layers are combined into one features table och exported as separate layers by geom type.
    combine_layers = True
    default_connection_string = f"dbname='postgres' host={host} user={user_name} password={password} port={port}"
    try:
        conn = psycopg2.connect(default_connection_string)
        #print(f"Connection established: {default_connection_string}")
        conn.close()

    except Exception as err:
        callback(None, "Connection error connecting to db: postgres", err)
        return RetCode.GENERIC_DB_CONNECTION_ERROR, export_ok_count

    db_ret = False
    try:
        current_retcode = RetCode.EXPORT_OK
        max_length = len(max(databases, key=len))
        count = 0 # Number of completed databases
        progress = 0 # Progress of the the export of all databases (except current one)
        for database in databases:
            ret = callback(progress) # Check if export has been canceled
            if ret is False: # export have been canceled
                conn.close() # Clean up and exit
                return RetCode.TERMINATED_BY_QGIS, export_ok_count

            connection_string = f"dbname={database} host={host} user={user_name} password={password} port={port} application_name=swedigarch_export"
            conn = psycopg2.connect(connection_string)

            padded_db_name = database.ljust(max_length + 2)
            if verify_database(conn) is False:
                current_retcode = RetCode.DATABASE_IS_NOT_INTRASIS_DB
                callback(None, None, f"Database {database} is not an Intrasis database, skipping")
                if log_file is not None:
                    log_file.write(f'{padded_db_name} Is not an Intrasis database, skipping\n')
                continue

            ret = callback(progress, None)
            if ret is False: # export has been canceled
                conn.close() # Clean up and exit
                return RetCode.TERMINATED_BY_QGIS, export_ok_count

            output_file = os.path.join(export_folder, f"{database.lower()}.gpkg")
            delete_on_faliure = not QFile(output_file).exists()
            if delete_on_faliure is False and overwrite:
                delete_on_faliure = True

            db_ret, error_msg, rights_error = export_database(conn, host, port, user_name, password, database, len(databases), progress, export_folder, overwrite, combine_layers, callback, detailed_print_outs)
            if db_ret:
                export_ok_count += 1
                print(f'export_database(db: {database}) db_ret: {db_ret}')
            else:
                print(f'export_database(db: {database}) db_ret: {db_ret} error: {error_msg} rights_error: {rights_error}')
                current_retcode = RetCode.UNKNOWN_ERROR
                callback(None, None, error_msg)

            if log_file is not None:
                if db_ret:
                    log_file.write(f'{padded_db_name} Exported OK\n')
                elif error_msg is not None:
                    if error_msg == 'Skipped because GeoPackage file already exist':
                        log_message = error_msg
                    else:
                        log_message = f'Error during export: {error_msg}'                    
                    log_file.write(f'{padded_db_name} {log_message}\n')
                else:
                    log_file.write(f'{padded_db_name} Unknown error during export!\n')

            conn.close()
            count += 1
            progress = (count / len(databases)) * 100
            message = f"Export of database {database} done"
            if db_ret is False:
                message = None
                output_file = os.path.join(export_folder, f"{database.lower()}.gpkg")
                if delete_on_faliure:
                    QFile.remove(output_file)
            ret = callback(progress - 5, message)
            if ret is False: # export has been canceled
                conn.close() # Clean up and exit
                return RetCode.TERMINATED_BY_QGIS, export_ok_count

        if log_file is not None and len(databases) > 1 and not csv:
            now = datetime.now()
            date_time = now.strftime('%Y-%m-%d %H:%M:%S')
            if export_ok_count == len(databases):
                log_file.write(f'\nExport done ({date_time}), {len(databases)} Databases Exported {export_ok_count }')
            else:
                log_file.write(f'\nExport done ({date_time}),\nSucceeded with exporting {export_ok_count} of {len(databases)} Databases.')
            log_file.close()
        print(f'export_database() db_ret: {db_ret}, rights_error: {rights_error}')
        if db_ret is False and len(databases) == 1:
            if rights_error:
                return RetCode.DATABASE_ACCESS_ERROR, export_ok_count
            return current_retcode, export_ok_count
        return current_retcode, export_ok_count
    except Exception as err:
        traceback.print_exc()
        callback(None, "Exception in export_to_geopackage()", err)
        log_file.write(f'Fatal error in export script: {err}')
        log_file.close()
        return RetCode.UNKNOWN_ERROR, export_ok_count

def export_database(conn:psycopg2.extensions.connection, host:str, port:int, user_name:str, password:str, database:str, db_count:int, progress:int, export_folder:str, overwrite:bool, combine_layers:bool, callback:Callable, detailed_print_outs:bool=True) -> tuple[bool,str,bool]:
    """Function to export from given connection to new GeoPackage in export_folder"""
    # Returns: db_ret, error_msg, rights_error (bool, string, bool)
    db_progress = 0 # Progress of the export of this database
    curr_progress = progress + db_progress / db_count
    ret = callback(curr_progress - 5, f"Starting export of {database}")
    if ret is False: # export have been canceled
        return False, None, False

    try:
        output_file = os.path.join(export_folder, f"{database.lower()}.gpkg")
        print(f'export_database() output_file {output_file} exist: {QFile(output_file).exists()} overwrite: {overwrite}\n')
        if QFile(output_file).exists():
            if overwrite is False:
                return False, 'Skipped because GeoPackage file already exist', False
            print(f'QFile.remove({output_file})')
            QFile.remove(output_file)
            if QFile(output_file).exists():
                print(f"Remove failed for file: {output_file}")
                return False, f'Remove failed for file: {output_file}, skipping', False

        print(f"Exporting db: {database} to: {output_file}")

        gp_conn = None
        #region "Export features, symbology and create layer views"

        # -1 är default falback_value för srid (-1: undefined Cartesian coordinate reference systems)
        srid, db_error, rights_error = Utils.get_database_srid(conn, -1, detailed_print_outs)
        if db_error is not None:
            if detailed_print_outs:
                print(f'Error exporting database: {database}  Database error: {db_error} in database: {database}')
                callback(None, f'Error exporting database: {database}', f"Database error: {db_error} in database: {database}")
            else:
                callback(None, None, db_error)
            print(f'export_database() get_database_srid() error: {db_error}')
            return False, db_error, rights_error

        site, db_error, rights_error = Utils.get_database_site(conn, detailed_print_outs)
        if db_error is not None:
            callback(None, f'Error exporting database: {database}', f"Database error: {db_error} in database: {database}")
            print(f'export_database() get_database_site() error: {db_error}')
            return False, db_error, rights_error

        #if detailed_print_outs:
            #print(f"Site: {site.site_id} {site.name_value}")

        wkb_types, db_error, rights_error  = list_geom_types_to_export(conn, callback)
        if db_error is not None:
            callback(None, f'Error exporting database: {database}', f"Database error: {db_error} in database: {database}")
            print(f'export_database() get_database_site() error: {db_error}')
            return False, db_error, rights_error

        #print(f'len(wkb_types): {len(wkb_types)}')
        if len(wkb_types) == 0:
            print('returning: Database has no geometries, skipping')
            return False, 'Database has no geometries, skipping', False

        layer_names = []
        # One per geometry type + one for non geometries, then double that for all attributes
        layer_export_steps = (len(wkb_types) + 1) * 2
        if detailed_print_outs:
            print(f"wkb_types: {wkb_types} Count {len(wkb_types)}")
        layers_done = 0

        for wkb_type in wkb_types:
            #print(f"Exporting layer with wkb_type: {wkb_type} Count {len(wkb_types)}")
            layer_name, filter_string, ext = export_postgis_layer_to_gpkg(host, port, user_name, password, database, output_file, wkb_type, srid, combine_layers, callback, detailed_print_outs)

            if combine_layers:
                export_utils.add_geometry_type_view(output_file, ext, layer_name, srid)

            layer_names.append(layer_name)
            if detailed_print_outs:
                print(f"Layer {layer_name} exported ...")
            layers_done += 1
            db_progress = (layers_done / layer_export_steps) * 100
            #print(f"progress: {progress}  db_progress: {db_progress} db_count: {db_count}")
            curr_progress = progress + db_progress / db_count
            message = None
            if detailed_print_outs:
                message = f"Lager {layer_name} exporterat till GeoPackage"
            callback(curr_progress - 5, message)

        export_project_information(host, port, user_name, password, database, site, output_file, srid, callback)

        gc.collect() # To free up QgsVectorLayer and close its connection.

        #region "export all objects to objects table"
        export_objects(conn, output_file, callback)

        export_utils.if_missing_create_gpkg_extensions(output_file)

        sql = "INSERT INTO gpkg_extensions VALUES('objects', null, 'attributes', 'http://www.geopackage.org/spec120/#attributes', 'read-write')"
        Utils.execute_sql_in_gpkg(output_file, sql)
        #endregion

        sb = SymbolBuilder(conn, detailed_print_outs)
        if combine_layers:
            # update geometry type after layer export, to allow QGIS to se the separate layer types in features.
            # Make table features not be seen as a layer, so QGIS will only add view layers.

            print(f'wkb_types.count: {len(wkb_types)}')
            if len(wkb_types) > 0: # Only if database has geometries
                # To make symbols auto loaded in QGIS we need to delete features from gpkg_contents
                Utils.execute_sql_in_gpkg(output_file, "DELETE FROM gpkg_contents WHERE table_name = 'features'")

                # If we need to fully follow "OGC GeoPackage Related Tables Extension" we need to keep features in gpkg_contents but then QGIS will not load symbols.
                # Use this UPDATE command instead of the DELETE above to follow "GeoPackage Related Tables Extension"
                #Utils.execute_sql_in_gpkg(output_file, "UPDATE gpkg_contents SET data_type = 'attributes' WHERE table_name = 'features'")

                Utils.execute_sql_in_gpkg(output_file, "DELETE FROM gpkg_geometry_columns WHERE table_name = 'features'")

            qml = sb.build_symbols_for_layer("")
            export_utils.save_layer_style(output_file, True, "features", qml, detailed_print_outs)
            for wkb_type in wkb_types:
                layer_name, filter_string = SymbolBuilder.wkb_type_to_layer(wkb_type)
                qml = sb.build_symbols_for_layer(filter_string)
                export_utils.save_layer_style(output_file, False, layer_name, qml, detailed_print_outs)
                sql = f"INSERT INTO gpkg_extensions VALUES('{layer_name}', 'geom', 'gpkg_rtree_index', 'http://www.geopackage.org/spec120/#extension_rtree', 'write-only')"
                Utils.execute_sql_in_gpkg(output_file, sql)
            #export_utils.insert_spatial_ref_sys_definition(connection_string, output_file, srid)
        else:
            first = True
            for wkb_type in wkb_types:
                layer_name, filter_string = SymbolBuilder.wkb_type_to_layer(wkb_type)
                qml = sb.build_symbols_for_layer(filter_string)
                export_utils.save_layer_style(output_file, first, layer_name, qml, detailed_print_outs)
                sql = f"INSERT INTO gpkg_extensions VALUES('{layer_name}', 'geom', 'gpkg_rtree_index', 'http://www.geopackage.org/spec120/#extension_rtree', 'write-only')"
                Utils.execute_sql_in_gpkg(output_file, sql)
                first = False
        #endregion

        staf_meta_id = Utils.get_meta_id(conn, Intrasis.CLASS_STAFF_META_ID)
        geo_obj_meta_id = Utils.get_meta_id(conn, Intrasis.CLASS_GEOOBJECT_META_ID)
        export_raster_layer_to_gpkg(conn, f"{staf_meta_id}, {geo_obj_meta_id}", output_file, srid, callback)

        gc.collect() # To free up QgsVectorLayer and close its connection.

        #region "Export attributes"
        sql = Utils.load_resource('sql/create_attributes_table.sql')
        Utils.execute_sql_in_gpkg(output_file, sql)
        sql = "INSERT INTO gpkg_extensions VALUES('attributes', null, 'attributes', 'http://www.geopackage.org/spec120/#attributes', 'read-write')"
        Utils.execute_sql_in_gpkg(output_file, sql)
        attr_steps = layer_export_steps / 2
        sql = Utils.load_resource('sql/select_classes_to_export.sql')
        sql = sql.replace("__EXCLUDE_META_IDS__", f"{staf_meta_id}, {geo_obj_meta_id}")
        data_frame = pd.read_sql(sql, conn)
        cls_count = len(data_frame)
        attr_inc = attr_steps / cls_count

        with closing(sqlite3.connect(output_file)) as gp_conn:
            gp_conn.enable_load_extension(True)
            cur = gp_conn.cursor()

            # To be able to update features table we need to load this extension
            cur.execute("SELECT load_extension(\"mod_spatialite\");")
            # Do update inside a transaction to speed up
            cur.execute("BEGIN TRANSACTION;")

            for row in data_frame.itertuples(index=False):
                export_class_attributes(conn, cur, row.ClassId, row.SubClassId, callback, detailed_print_outs)
                layers_done = layers_done + attr_inc
                db_progress = (layers_done / layer_export_steps) * 100
                curr_progress = progress + db_progress / db_count
                ret = callback(None) # Check if export has been canceled
                if ret is False: # export have been canceled
                    conn.close() # Clean up and exit
                    return False, False, False
            cur.execute("COMMIT;")
            cur.close()
            gp_conn.commit()
        #endregion

            db_error, rights_error = export_relations(conn, gp_conn, output_file, detailed_print_outs)
            if db_error is not None:
                gp_conn.close()
                callback(None, None, db_error)
                return False, db_error, rights_error

            # Add attribute_objects index to table attributes to speed up operations
            Utils.execute_sql_in_gpkg(output_file, 'CREATE INDEX attribute_objects ON attributes (object_id);')

    except psycopg2.errors.InsufficientPrivilege as ipex:
        if gp_conn is not None:
            gp_conn.close()
        print(f'InsufficientPrivilege: in load_class_symbols(): {str(ipex).rstrip()}')
        return False, f'{str(ipex).rstrip()}', True
    except Exception as err:
        print(f'export_database() Exception: {err}')
        if gp_conn is not None:
            gp_conn.close()
        traceback.print_exc()
        callback(None, "Error in export_database()", err)
        print('export_database() Exception: {err}')
        return False, f'{err}', False
    print(f"Export db done: {database} to: {output_file}")
    return True, False, False

def export_postgis_layer_to_gpkg(host:str, port:int, user_name:str, password:str, database:str, output_file:str, wkb_type, srid:int, combine_layers:bool, callback:Callable, detailed_print_outs:bool=True) -> tuple[str,str,QgsRectangle]:
    """Export geometry type layer to GeoPackage, """
    uri = QgsDataSourceUri()
    uri.setConnection(host, port, database, user_name, password)
    uri.disableSelectAtId(True)
    uri.setWkbType(wkb_type)
    uri.setKeyColumn("fid")
    #callback(None, f"export_postgis_layer_to_gpkg({database}, {output_file}, {wkb_type})")
    layer_name, filter_string = SymbolBuilder.wkb_type_to_layer(wkb_type)
    sql = Utils.load_resource("sql/layer_query.sql")
    sql = sql.replace("SPATIAL_TYPE", layer_name)
    if srid > 0:
        sql = sql.replace("__GEOM_COLUMN__", f"ST_SetSRID(ST_Multi(go.the_geom), {srid})")
    else:
        sql = sql.replace("__GEOM_COLUMN__", "ST_Multi(go.the_geom)")
    sql = sql.replace("GEOM_FILTER_STRING", filter_string)
    if QgsWkbTypes.PointZM == wkb_type:
        sql = sql.replace("ST_Multi(go.the_geom)", "go.the_geom")
    #print(f'sql: {sql}')
    uri.setDataSource('','(' + sql + ')','geom','','fid')
    layer = QgsVectorLayer(uri.uri(), layer_name, 'postgres')
    crs = QgsCoordinateReferenceSystem(f"EPSG:{srid}")
    layer.setCrs(crs)
    if layer.isValid() is False and detailed_print_outs:
        print(f"Layer {layer_name} created isValid: {layer.isValid()}")

    metadata = QgsLayerMetadata()
    metadata.setTitle('Intrasis GeoPackage export')
    metadata.setAbstract('Intrasis database export')
    metadata.setLicenses(['l1', 'l2'])
    metadata.setKeywords({
        'Intrasis Export': ['GeoPackage export'],
        'gmd:topicCategory': ['Intrasis']
    })

    try:
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = 'GPKG'
        options.fileEncoding = "UTF-8"
        options.includeZ = True
        if combine_layers:
            options.layerName = "features"
        else:
            options.layerName = layer_name
        options.saveMetadata = True
        options.layerMetadata = metadata
        if QFile(output_file).exists(): # If exist set to create layer or merge in existing gpkg file.
            if combine_layers:
                options.actionOnExistingFile = QgsVectorFileWriter.AppendToLayerNoNewFields
            else:
                options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
        #write_result, error_message, new_file, new_layer =
        QgsVectorFileWriter.writeAsVectorFormatV3(layer, output_file, QgsProject.instance().transformContext(), options)
        extent = QgsRectangle(layer.extent())
        #print(f'layer.source(): {layer.source()}')
        layer.disconnect()
        del layer
        layer = None
        del uri
        uri = None
        #print(f"QgsVectorFileWriter.writeAsVectorFormatV3({output_file}) done  combine_layers: {combine_layers}")
        return layer_name, filter_string, extent
    except Exception as err:
        traceback.print_exc()
        callback(None, "Error in export_postgis_layer_to_gpkg()", err)

def export_raster_layer_to_gpkg(conn:psycopg2.extensions.connection, meta_ids:str, output_file:str, srid:int, callback:Callable) -> None:
    """Export raster geometries as separate raster layers with geo_object_id in name"""
    try:
        sql = Utils.load_resource('sql/select_raster_object_info.sql')
        sql = sql.replace("__EXCLUDE_META_IDS__", meta_ids)
        data_frame = pd.read_sql(sql, conn)
        rasters = []
        coord_transform_context = QgsCoordinateTransformContext()
        for row in data_frame.itertuples(index=False):
            raster = export_utils.fetch_and_save_raster_file(conn, row)
            rasters.append(raster)
            if os.path.isfile(raster.temp_file) is False:
                print(f"raster file {raster.temp_file} does NOT exist for PublicId: {raster.intrasis_id}, GeoObjectId: {raster.geo_object_id}, length: {raster.length}")
                continue

            raster_layer = QgsRasterLayer(raster.temp_file, 'Raster', 'gdal')
            if raster_layer.isValid() is False:
                print(f"raster_layer.isValid: {raster_layer.isValid()} for PublicId: {raster.intrasis_id}, GeoObjectId: {raster.geo_object_id}, length: {raster.length}")
                continue

            provider = raster_layer.dataProvider()
            pipe = QgsRasterPipe()
            ret = pipe.set(provider.clone())
            #print(f"ret1: {ret}")

            raster_layer_name = f"raster_{raster.geo_object_id}"
            fw = QgsRasterFileWriter(output_file)
            fw.setOutputFormat('gpkg')
            fw.setCreateOptions([f"RASTER_TABLE={raster_layer_name}", 'APPEND_SUBDATASET=_YES'])

            ret = fw.writeRaster(pipe,
                                provider.xSize(),
                                provider.ySize(),
                                provider.extent(),
                                provider.crs(), coord_transform_context)
            if ret != 0:
                write_error = WriterError(ret)
                callback(None, f"Failed to export raster: PublicId: {raster.intrasis_id}, GeoObjectId: {raster.geo_object_id}, length: {raster.length} Error: {write_error}")
                print(f"Failed to export raster: PublicId: {raster.intrasis_id}, GeoObjectId: {raster.geo_object_id}, length: {raster.length} Error: {write_error}")

            QgsProject.instance().removeMapLayer(raster_layer)
            fw = None
            pipe = None
            raster_layer = None
        for raster in rasters:
            os.remove(raster.temp_file)
            extra_file = f"{raster.temp_file}.aux.xml"
            if os.path.isfile(extra_file):
                os.remove(extra_file)
    except Exception as err:
        traceback.print_exc()
        callback(None, "Error in export_raster_layer_to_gpkg()", err)

def export_objects(conn:psycopg2.extensions.connection, output_file:str, callback:Callable) -> None:
    """Export all objects to objects table, with Staf and GeoObject filtered out"""
    try:
        sql = Utils.load_resource('sql/create_objects_table.sql')
        Utils.execute_sql_in_gpkg(output_file, sql)
        with closing(sqlite3.connect(output_file)) as gp_conn:
            sql = Utils.load_resource('sql/select_objects.sql')
            staf_meta_id = Utils.get_meta_id(conn, Intrasis.CLASS_STAFF_META_ID)
            geo_obj_meta_id = Utils.get_meta_id(conn, Intrasis.CLASS_GEOOBJECT_META_ID)
            sql = sql.replace("__EXCLUDE_META_IDS__", f"{staf_meta_id}, {geo_obj_meta_id}")
            data_frame = pd.read_sql(sql, conn)
            data_frame.to_sql(name='objects', con = gp_conn, if_exists='append', index=False)
            gp_conn.commit()
    except Exception as err:
        traceback.print_exc()
        callback(None, "Error in export_objects()", err)

def export_none_geometry_objects(host:str, port:int, user_name:str, password:str, conn:psycopg2.extensions.connection, database:str, output_file:str, srid:int, callback:Callable) -> tuple[int, int]:
    """export none geometry objects"""
    try:
        uri = QgsDataSourceUri()
        uri.setConnection(host, port, database, user_name, password)
        uri.disableSelectAtId(True)
        uri.setWkbType(QgsWkbTypes.PointZM)
        uri.setKeyColumn("fid")
        message = None
        callback(None, message)
        sql = Utils.load_resource('sql/no_geom_layer_query.sql')
        staf_meta_id = Utils.get_meta_id(conn, Intrasis.CLASS_STAFF_META_ID)
        geo_obj_meta_id = Utils.get_meta_id(conn, Intrasis.CLASS_GEOOBJECT_META_ID)
        sql = sql.replace("__EXCLUDE_META_IDS__", f"{staf_meta_id}, {geo_obj_meta_id}")
        sql = sql.replace("__SRID__", f"{srid}")
        uri.setDataSource('','(' + sql + ')','geom','','fid')
        layer = QgsVectorLayer(uri.uri(), 'NoneGeoms', 'postgres')
        crs = QgsCoordinateReferenceSystem(f"EPSG:{srid}")
        layer.setCrs(crs)
        if layer.isValid() is False:
            print(f"Non geometry layer created isValid: {layer.isValid()}")
            return -1, -1

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = 'GPKG'
        options.fileEncoding = "UTF-8"
        options.includeZ = True
        options.layerName = "features"
        options.saveMetadata = False
        options.actionOnExistingFile = QgsVectorFileWriter.AppendToLayerNoNewFields
        write_result, error_message, new_file, new_layer = QgsVectorFileWriter.writeAsVectorFormatV3(layer, output_file, QgsProject.instance().transformContext(), options)
        #print(f"QgsVectorFileWriter.writeAsVectorFormatV3() done  write_result: {write_result}, error_message: {error_message}, new_layer: {new_layer}")
        layer.disconnect()
        del layer
        layer = None
        del uri
        uri = None        
        return staf_meta_id, geo_obj_meta_id
    except Exception as err:
        traceback.print_exc()
        callback(None, "Error in export_none_geometry_objects()", err)

def export_project_information(host:str, port:int, user_name:str, password:str, database:str, site:Site, output_file:str, srid:int, callback:Callable) -> None:
    """Export project_information as point feature in new layer 'project_information'"""
    print('export_project_information(...)')
    uri = QgsDataSourceUri()
    uri.setConnection(host, port, database, user_name, password)
    uri.disableSelectAtId(True)
    uri.setWkbType(QgsWkbTypes.PointZM)
    uri.setKeyColumn("fid")

    sql = Utils.load_resource('sql/create_project_info_layer.sql')

    proj_info = f'\'{site.site_id}\' as \"SiteId\"'
    fields = site.get_fields()
    for field in fields:
        value = site.get_field_value(field)
        if Utils.is_empty_string_or_none(value):
            value = ""
        else:
            value = value.replace("\'", "\'\'") # Escape single quote chars in value string
        proj_info += f', \'{value}\' as \"{field}\"'

    #print(f'proj_info: {proj_info}')
    attr = f" 1 as pk, {proj_info}"
    sql = sql.replace("__ATTR__", attr)
    #print(f"sql: {sql}")
    uri.setDataSource('','(' + sql + ')','geom','','fid')
    layer = QgsVectorLayer(uri.uri(), "ProjInfo", 'postgres')
    crs = QgsCoordinateReferenceSystem(f"EPSG:{srid}")
    layer.setCrs(crs)
    if layer.isValid() is False:
        sql1 = sql # Save old SQL to log both tested if none worked
        # Test with older name of fuction ST_Force2D (ST_Force_2D)
        sql = sql.replace('ST_Force2D', 'ST_Force_2D')
        uri.setDataSource('','(' + sql + ')','geom','','fid')
        layer = QgsVectorLayer(uri.uri(), "ProjInfo", 'postgres')
        layer.setCrs(crs)
        if layer.isValid() is False:
            # Still failed, log both tested SQL codes.
            print(f"Layer ProjInfo created isValid: {layer.isValid()}")
            print(f"SQL1: {sql1}")
            print(f"SQL2: {sql}")
            return

    try:
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = 'GPKG'
        options.fileEncoding = "UTF-8"
        options.includeZ = True
        options.layerName = "project_information"
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
        QgsVectorFileWriter.writeAsVectorFormatV3(layer, output_file, QgsProject.instance().transformContext(), options)
        layer.disconnect()
        del layer
        layer = None
        del uri
        uri = None
    except Exception as err:
        traceback.print_exc()
        callback(None, "Error in export_project_information()", err)

def export_class_attributes(conn:psycopg2.extensions.connection, cur:sqlite3.Cursor, class_id:int, sub_class_id:int, callback:Callable, detailed_print_outs:bool=True) -> None:
    """Export attributes for class (and SubClass if sub_class_id has value) and write them to the GeoPackage"""
    try:
        sql = Utils.load_resource('sql/select_object_attributes.sql')
        if Utils.is_nan(sub_class_id) or sub_class_id is None:
            sql =  sql.replace("__CLASS__", f" {class_id} AND o.\"SubClassId\" is NULL")
            sql = sql.replace("__CLS_IDS__", f"{class_id}")
            sql = sql.replace("__ORDERING__", "")
            if detailed_print_outs:
                print(f"Attribute export for ClassId: {class_id}, SubClassId: NULL")
        else:
            sql = sql.replace("__CLASS__", f" {class_id} AND o.\"SubClassId\" = {sub_class_id}")
            sql = sql.replace("__CLS_IDS__", f"{class_id}, {sub_class_id}")
            sql = sql.replace("__ORDERING__", f", am.\"ObjectDefId\" = {sub_class_id}")
            if detailed_print_outs:
                print(f"Attribute export for ClassId: {class_id}, SubClassId: {sub_class_id}")
        data_frame = pd.read_sql(sql, conn)
        export_utils.store_attributes(cur, data_frame)
    except Exception as err:
        traceback.print_exc()
        callback(None, "Error in export_postgis_layer_to_gpkg()", err)

def export_relations(conn:psycopg2.extensions.connection, gp_conn:sqlite3.Connection, output_file:str, detailed_print_outs:bool=True) -> tuple[str, bool]:
    """Export relations between objects from Intrasis db"""
    try:
        #region Export relations
        sql = Utils.load_resource('sql/create_gpkgext_relations_table.sql')
        Utils.execute_sql_in_gpkg(output_file, sql)
        sql = Utils.load_resource('sql/create_object_relations_table.sql')
        Utils.execute_sql_in_gpkg(output_file, sql)
        sql = Utils.load_resource('sql/create_attribute_relations_table.sql')
        Utils.execute_sql_in_gpkg(output_file, sql)
        sql = "INSERT INTO gpkg_extensions VALUES('gpkgext_relations', NULL, 'related_tables', 'http://www.geopackage.org/18-000.html', 'read-write')"
        Utils.execute_sql_in_gpkg(output_file, sql)
        sql = "INSERT INTO gpkg_extensions VALUES('object_relations', NULL, 'related_tables', 'http://www.geopackage.org/18-000.html', 'read-write')"
        Utils.execute_sql_in_gpkg(output_file, sql)
        sql = "INSERT INTO gpkg_extensions VALUES('attribute_relations', NULL, 'related_tables', 'http://www.geopackage.org/18-000.html', 'read-write')"
        Utils.execute_sql_in_gpkg(output_file, sql)

        export_utils.insert_gpkg_relation(output_file, "objects", "object_id", "objects", "object_id", "features", "object_relations")
        export_utils.insert_gpkg_relation(output_file, "objects", "object_id", "attributes", "attribute_id", "simple_attributes", "attribute_relations")

        # Read relations information from Intrasis DB and store in GeoPackage
        sql = Utils.load_resource('sql/select_object_relations.sql')
        data_frame = pd.read_sql(sql, conn)
        data_frame.to_sql(name='object_relations', con = gp_conn, if_exists='append', index=False)
        gp_conn.close()

        # Remove relations to objects not exported. (because that class whas filtered out like personel)
        Utils.execute_sql_in_gpkg(output_file, "DELETE FROM object_relations WHERE base_id not IN (SELECT object_id FROM objects);")

        # Fill attributes_relations
        Utils.execute_sql_in_gpkg(output_file, "INSERT INTO attribute_relations (related_id, base_id) SELECT attribute_id, object_id FROM attributes;")

        #endregion
        return None, False
    except psycopg2.errors.InsufficientPrivilege as ipex:
        print(f'InsufficientPrivilege: when exporting relations: {str(ipex).rstrip()}')
        return f'{str(ipex).rstrip()}', True
    except Exception as err:
        print(f'export_relations() {str(err).rstrip()}')
        traceback.print_exc()
        return f'{str(err).rstrip()}', False

def verify_database(conn) -> bool:
    """Verify that the database is an Intrasis database"""
    sql = Utils.load_resource("sql/is_intrasis_db_check.sql")
    cursor = conn.cursor()
    cursor.execute(sql)
    result = cursor.fetchone()[0]
    cursor.close()
    return result == "Intrasis DB"

def list_geom_types_to_export(conn, callback:Callable) -> tuple[list[QgsWkbTypes], str, bool]:
    """Fetch Geometry types in database to export"""
    try:
        db_result = pd.read_sql("SELECT DISTINCT geometrytype(the_geom) FROM \"GeoObject\" WHERE geometrytype(the_geom) is NOT NULL", conn)
        lst_items = db_result["geometrytype"]
        wkt_types = []
        for row in lst_items:
            if row == "POINT":
                wkt_types.append(QgsWkbTypes.PointZM)
            elif row == "MULTIPOINT":
                wkt_types.append(QgsWkbTypes.MultiPointZM)
            elif row == "LINESTRING" or row == "MULTILINESTRING":
                if QgsWkbTypes.MultiLineStringZM not in wkt_types:
                    wkt_types.append(QgsWkbTypes.MultiLineStringZM)
            elif row == "POLYGON" or row == "MULTIPOLYGON":
                if QgsWkbTypes.MultiPolygonZM not in wkt_types:
                    wkt_types.append(QgsWkbTypes.MultiPolygonZM)
        return wkt_types, None, False
    except psycopg2.errors.InsufficientPrivilege as ipex:
        print(f'InsufficientPrivilege: when trying to fetch srid: {str(ipex).rstrip()}')
        return wkt_types, f'{str(ipex).rstrip()}', True
    except Exception as err:
        traceback.print_exc()
        callback(None, "Error in list_geom_types_to_export()", err)
        return [], f'{str(err).rstrip()}', False
