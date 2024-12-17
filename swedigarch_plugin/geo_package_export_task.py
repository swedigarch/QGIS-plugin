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
"""GeoPackageExportTask"""

#from export import *
import os
import traceback
from datetime import datetime
from qgis.utils import iface
from qgis.gui import QgsMessageBar
from qgis.core import QgsTask, QgsMessageLog, Qgis
from PyQt5.QtCore import QFile
from .constant import RetCode
from .geopackage_export import export_to_geopackage, export_simplified_gpkg
from .export_geopackage_to_csv import export_geopackage_to_csv

MESSAGE_CATEGORY = 'GeoPackageExportTask'

class GeoPackageExportTask(QgsTask):
    """Subclass to QgsTask that handles normal export, where dabases are exported one by one.""" 

    def __init__(self, description, host, port, user_name, password, databases, export_folder, overwrite:bool, csv:bool, simplified:bool, detailed_print_outs=True, subclasses_to_exclude=None):
        super().__init__(description, QgsTask.CanCancel)
        self.log_file = None
        self.host = host
        self.port = port
        self.user_name = user_name
        self.password = password
        self.databases = databases
        self.export_folder = export_folder
        self.overwrite = overwrite
        self.csv = csv
        self.simplified = simplified
        self.total = 0
        self.iterations = 0
        self.exception = None
        self.detailed_print_outs = detailed_print_outs
        self.last_log_line = None
        self.subclasses_to_exclude = subclasses_to_exclude
        self.setProgress(0)
        if self.detailed_print_outs:
            print("GeoPackageExportTask.init()")

    def callback(self, progress:int = None, message:str = None, error:str = None) -> bool:
        """Callback function called from the geopackage_export script."""
        #print(f"callback(progress: {progress}, message: {message}, error: {error})")
        if error is not None:
            QgsMessageLog.logMessage(f"Export error: {error}", MESSAGE_CATEGORY, Qgis.Critical)

        if message is not None:
            QgsMessageLog.logMessage(f"Export script: {message}", MESSAGE_CATEGORY, Qgis.Info)

        if progress is not None and progress != "":
            if progress < 0:
                progress = 0
            self.setProgress(progress)

        if self.isCanceled():
            return False

        return True

    def run(self):
        """Actual export work"""
        try:
            self.setProgress(0)

            now = datetime.now()
            date_tag = now.strftime('%Y-%m-%d_%H-%M-%S')
            bulk_log_filename = os.path.join(self.export_folder, f'export_{date_tag}.log')

            with open(bulk_log_filename, "w", encoding='utf-8') as log_file:
                date_time = now.strftime('%Y-%m-%d %H:%M:%S')
                log_file.write(f'Export of {len(self.databases)} database to directory \"{self.export_folder}\" started: ({date_time})\n\n')

                if self.detailed_print_outs:
                    print("GeoPackageExportTask.run()")
                QgsMessageLog.logMessage("GeoPackage Export Task Started", MESSAGE_CATEGORY, Qgis.Info)
                ret, export_ok_count, log_excluded_subclasses = export_to_geopackage(self.host, self.port, self.user_name, self.password, self.databases, self.export_folder, self.overwrite, self.csv, self.simplified,
                                                                                    self.callback, self.detailed_print_outs, log_file, self.subclasses_to_exclude)
                QgsMessageLog.logMessage(f"GeoPackage export done, ret : {ret}", MESSAGE_CATEGORY, Qgis.Info)
                max_length = len(max(self.databases, key=len))
                if self.csv:
                    print('Starting CSV export')
                    self.callback(90, "Starting CSV export")
                    for database in self.databases:
                        geo_package_file = os.path.join(self.export_folder, f"{database.lower()}.gpkg")
                        output_filename = os.path.join(self.export_folder, f"{database.lower()}.zip")
                        need_csv_export = not QFile(output_filename).exists()
                        csv_export_old = False
                        if not need_csv_export:
                            gpkg_stat_info = os.stat(geo_package_file)
                            csv_stat_info = os.stat(output_filename)
                            gpkg_mod_time = datetime.fromtimestamp(gpkg_stat_info.st_mtime)
                            csv_mod_time = datetime.fromtimestamp(csv_stat_info.st_mtime)
                            csv_export_old = gpkg_mod_time > csv_mod_time # Only overwrite CSV export if GeoPackage is newer

                        padded_db_name = database.ljust(max_length + 2)
                        if need_csv_export or csv_export_old:
                            ret_code, error_msg, output_filename = export_geopackage_to_csv(geo_package_file)
                            if ret_code == RetCode.EXPORT_OK:
                                log_file.write(f'\n{padded_db_name} CSV export OK  ({output_filename})\n')
                                #log_file.write(f'SubClass(es) that were excluded: {self.subclasses_to_exclude}\n{padded_db_name} CSV export OK  ({output_filename})\n')
                            else:
                                log_file.write(f'{padded_db_name} Error during CSV export: {error_msg}\n')
                        elif not csv_export_old:
                            message = f'{padded_db_name} Skipping CSV export, because existing CSV export is newer than the GeoPackage.\n'
                            QgsMessageLog.logMessage(message, MESSAGE_CATEGORY, Qgis.Info)
                            log_file.write(message)

                    if not self.simplified:
                        self.callback(100, "CSV Export done")
                    else:
                        self.callback(95, "CSV Export done")

                if self.simplified:
                    self.callback(95, "Starting Simplified export")
                    for database in self.databases:
                        padded_db_name = database.ljust(max_length + 2)
                        gpkg_path = os.path.join(self.export_folder, f"{database.lower()}.gpkg")
                        ret_code, error_msg, output_filename = export_simplified_gpkg(gpkg_path)
                        if ret_code == RetCode.EXPORT_OK:
                            log_file.write(f'{padded_db_name} Simplified GPKG export OK\n')
                        else:
                            log_file.write(f'{padded_db_name} Error during simplified GPKG export: {error_msg}\n')
                    self.callback(100, "Simplified Export done")

                if self.csv or self.simplified: # CSV or simplified export enabled, then we need to log the final result here
                    now = datetime.now()
                    total_number_of_databases = len(self.databases)
                    date_time = now.strftime('%Y-%m-%d %H:%M:%S')
                    if export_ok_count == total_number_of_databases:
                        log_file.write(f'\nExport done: {date_time}\n{total_number_of_databases} Databases Exported, with no error')
                    else:
                        log_file.write(f'\nExport done: {date_time}\nSucceeded with exporting {export_ok_count} of {total_number_of_databases} Databases.')

            return ret == RetCode.EXPORT_OK
        except Exception as err:
            traceback.print_exc()
            print(f"Exception from export_to_geopackage() Exception: {err}")
            QgsMessageLog.logMessage(f"Exception from export_to_geopackage() Exception: {err}", MESSAGE_CATEGORY, Qgis.Info)
            return False

    def finished(self, result:str):
        """Task finnished"""
        print(f'GeoPackageExportTask.finished() csv: {self.csv}')
        msg = f"GeoPackage export {self.description()} completed\n {self.total} Databases Exported  result: {result}"
        print(msg)
        QgsMessageLog.logMessage(msg, MESSAGE_CATEGORY, Qgis.Info)
        QgsMessageLog.logMessage(msg, MESSAGE_CATEGORY, Qgis.Success)
        iface.messageBar().pushMessage("Complete", "GeoPackage export completed", 0, 10) # QgsMessageBar.Success replaced with 0 value

    def cancel(self):
        """Task Canceled"""
        QgsMessageLog.logMessage(f"GeoPackage export {self.description()} was canceled", MESSAGE_CATEGORY, Qgis.Info)
        super().cancel()
