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
"""GeoPackageBulkExportTask"""

import os
import traceback
import time
from datetime import datetime
from .geopackage_export import export_to_geopackage
from .export_geopackage_to_csv import export_geopackage_to_csv
from qgis.gui import QgsMessageBar
from qgis.core import (QgsApplication, QgsTask, QgsMessageLog, Qgis)
from PyQt5.QtCore import QFile
from qgis.utils import iface
from .constant import RetCode

MESSAGE_CATEGORY = 'GeoPackageExportTask'

class GeoPackageBulkExportMainTask(QgsTask):
    """Subclass to QgsTask that handles bulk export to geopackage"""
    def __init__(self, description, host, port, user_name, password, export_folder, overwrite, csv, databases, subclasses_to_exclude=None):
        super().__init__(description, QgsTask.CanCancel)
        self.log_file = None
        self.databases = databases
        self.total_number_of_databases = len(databases)
        self.export_ok_count = 0
        self.host = host
        self.port = port
        self.user_name = user_name
        self.password = password
        self.export_folder = export_folder
        self.overwrite = overwrite
        self.csv = csv
        self.databases_in_progress_dict = dict()
        self.subclasses_to_exclude = subclasses_to_exclude
        # Get longest database name
        self.max_length = len(max(databases, key=len))
        self.setProgress(0)
        print('GeoPackageBulkExportMainTask() init() done.')

    def get_percent_databases_exported(self):
        """Get percent done"""
        done = self.total_number_of_databases  - (len(self.databases) + len(self.databases_in_progress_dict))
        return (done / self.total_number_of_databases) * 100

    def get_next_database_name(self, subtask_id):
        """Callback that gets called from subtasks to receive new db name (or cancel)"""
        if subtask_id in self.databases_in_progress_dict: #Subtask is done with the export it was working on
            self.databases_in_progress_dict.pop(subtask_id)

        self.setProgress(self.get_percent_databases_exported()) #Set current progress

        if self.isCanceled() or len(self.databases) == 0: # Return None if all databses are exported or export is canceled
            return None

        #Get next database and assign to calling subtask
        next_db_name = self.databases.pop(0)
        self.databases_in_progress_dict[subtask_id] = next_db_name
        return next_db_name

    def create_subtasks(self, description, number_of_subtasks):
        """create subtasks"""

        now = datetime.now()
        date_tag = now.strftime('%Y-%m-%d_%H-%M-%S')
        bulk_log_filename = os.path.join(self.export_folder, f'bulk_export_{date_tag}.log')
        self.log_file = open(bulk_log_filename, "w", encoding='utf-8')
        date_time = now.strftime('%Y-%m-%d %H:%M:%S')
        self.log_file.write(f'Bulk export of {len(self.databases)} databases to directory \"{self.export_folder}\" started: {date_time}\n\n')
        QgsMessageLog.logMessage(f'Starting bulkexport of {len(self.databases)} databases', MESSAGE_CATEGORY, Qgis.Info)
        print(f'create_subtasks(number_of_subtasks: {number_of_subtasks}) num databases: {len(self.databases)}')

        for i in range(0, number_of_subtasks):
            subtask = GeoPackageBulkExportSubtask(description, self.host, self.port, self.user_name, self.password, self.export_folder, self.overwrite, self.csv, self.max_length, self.write_log_line, self.get_next_database_name, self.export_status_callback, self.subclasses_to_exclude)
            self.addSubTask(subtask, [], QgsTask.ParentDependsOnSubTask) #Make sure the main task is run only after all subtasks are done

    def write_log_line(self, message):
        """Write log line to log file"""
        self.log_file.write(message)

    def export_status_callback(self, database, result, message = None):
        """Callback that gets called from subtasks to send export status of a database"""
        padded_db_name = database.ljust(self.max_length + 2)
        if result:
            self.export_ok_count += 1
            self.log_file.write(f'{padded_db_name} Exported OK\n')
            QgsMessageLog.logMessage(f"Database {database} Exported OK", MESSAGE_CATEGORY, Qgis.Info)
            return
        elif message is not None:
            if "is not an Intrasis database" in message:
                self.log_file.write(f'{padded_db_name} {self.tr("Is not an Intrasis database, skipping")}\n')
                QgsMessageLog.logMessage(f'Database {database} {self.tr("Is not an Intrasis database, skipping")}', MESSAGE_CATEGORY, Qgis.Critical)
            else:
                if message == 'Skipped because GeoPackage file already exist':
                    log_message = message
                else:
                    log_message = f'Error during export: {message}'
                self.log_file.write(f'{padded_db_name} {log_message}\n')
                QgsMessageLog.logMessage(f" {database} {log_message}", MESSAGE_CATEGORY, Qgis.Critical)
        else:
            self.log_file.write(f'{padded_db_name} Unknown error during export!\n')

    def run(self): #Will run after all subtasks (i.e. all actual exporting tasks) are done
        """main task run"""
        try:
            print(f"Main Task {self.description()}: run")
            if len(self.databases) > 0:
                return False
            else:
                return True
        except Exception as err:
            print(f"Exception from export_to_geopackage() Exception: {err}")
            QgsMessageLog.logMessage(f"Exception from export_to_geopackage() Exception: {err}", MESSAGE_CATEGORY, Qgis.Info)
            return False

    def finished(self, result):
        """Task finnished"""
        try:
            now = datetime.now()
            date_time = now.strftime('%Y-%m-%d %H:%M:%S')
            if self.export_ok_count == self.total_number_of_databases:
                msg = f"GeoPackage export {self.description()} completed\n {self.total_number_of_databases} Databases Exported {self.export_ok_count }  result: {result}"
                self.log_file.write(f'\nBulk export done: {date_time}\n{self.total_number_of_databases} Databases Exported {self.export_ok_count }')
            else:
                msg = f"GeoPackage export {self.description()} completed\nSucceeded with exporting {self.export_ok_count} of {self.total_number_of_databases} Databases"
                self.log_file.write(f'\nBulk export done: {date_time}\nSucceeded with exporting {self.export_ok_count} of {self.total_number_of_databases} Databases.')
            self.log_file.close()
            print(msg)
            #QgsMessageLog.logMessage(msg, MESSAGE_CATEGORY, Qgis.Info)
            QgsMessageLog.logMessage(msg, MESSAGE_CATEGORY, Qgis.Success)
            iface.messageBar().pushMessage("Complete", "GeoPackage export completed", Qgis.Success, 10)
        except Exception as err:
            print(f'Exception in GeoPackageBulkExportMainTask.finished(): {err}')

    def cancel(self):
        """Task Canceled"""
        QgsMessageLog.logMessage(f"GeoPackage export {self.description()} was canceled", MESSAGE_CATEGORY, Qgis.Info)
        print('GeoPackageBulkExportMainTask.cancel()')
        traceback.print_stack()
        super().cancel()

class GeoPackageBulkExportSubtask(QgsTask):
    """Subclass to QgsTask that handles bulk export to geopackage"""
    def __init__(self, description, host, port, user_name, password, export_folder, overwrite, csv, max_length, write_log_line, get_next_database_name, export_status_callback, subclasses_to_exclude=None):
        super().__init__(description, QgsTask.CanCancel)
        #self.master_task = master_task
        self.get_next_database_name_callback = get_next_database_name
        #object.__getattribute__(master_task, 'get_next_database_name_callback')
        self.export_status_callback = export_status_callback
        #object.__getattribute__(master_task, 'export_status_callback')
        self.database = None
        self.current_database = None
        self.last_database = None
        self.host = host
        self.port = port
        self.user_name = user_name
        self.password = password
        self.export_folder = export_folder
        self.overwrite = overwrite
        self.csv = csv
        self.max_length = max_length
        self.write_log_line = write_log_line
        self.last_error = None
        self.subclasses_to_exclude = subclasses_to_exclude

    def callback(self, progress = None, message = None, error = None):
        """Callback function called from the geopackage_export script."""
        if error is not None:
            #QgsMessageLog.logMessage(f"Error: {error}", MESSAGE_CATEGORY, Qgis.Critical)
            #print(f'SubTask error: {error}')
            self.last_error = error

        # Ignore all messages from subtask, only log messages from the main bulk export
        #if message is not None:
            #QgsMessageLog.logMessage(f"Subtask: {message}", MESSAGE_CATEGORY, Qgis.Info)

        if self.isCanceled():
            print('SubTask isCanceled!')
            return False

        return True

    def run(self):
        """run export"""
        try:
            ret = RetCode.EXPORT_OK
            while True: #run until there is no new database returned from the main task callback function
                self.database = self.get_next_database_name_callback(id(self))
                if self.database is None:
                    return True
                else:
                    #QgsMessageLog.logMessage(f"GeoPackage Export of db \"{self.database}\" Started", MESSAGE_CATEGORY, Qgis.Info)
                    self.last_error = None

                    output_file = os.path.join(self.export_folder, f"{self.database.lower()}.gpkg")
                    delete_on_faliure = not QFile(output_file).exists()
                    if delete_on_faliure is False and self.overwrite:
                        delete_on_faliure = True

                    ret, export_ok_count = export_to_geopackage(self.host, self.port, self.user_name, self.password, [self.database], self.export_folder, self.overwrite, self.csv, self.callback, detailed_print_outs=False, subclasses_to_exclude=self.subclasses_to_exclude)
                    print(f'GeoPackageBulkExportSubtask.run() export_to_geopackage({self.database}) ret: {ret}  self.last_error: {self.last_error}')
                    geo_package_file = os.path.join(self.export_folder, f"{self.database.lower()}.gpkg")
                    if ret == RetCode.EXPORT_OK:
                        self.export_status_callback(self.database, True, None)
                    else:
                        print(f'before export_status_callback({self.database}, False, {self.last_error})')
                        self.export_status_callback(self.database, False, self.last_error)
                        if QFile(geo_package_file).exists():
                            if delete_on_faliure:
                                print(f'GeoPackageBulkExportSubtask.run() export failed, export file {geo_package_file} still exist, deleting it')
                                QFile.remove(geo_package_file)
                                if QFile(geo_package_file).exists():
                                    print(f"Remove failed for file: {geo_package_file}")

                    if (ret == RetCode.EXPORT_OK or self.last_error == 'Skipped because GeoPackage file already exist') and self.csv:
                        output_filename = os.path.join(self.export_folder, f"{self.database.lower()}.zip")
                        need_csv_export = not QFile(output_filename).exists()
                        if not need_csv_export:
                            gpkg_stat_info = os.stat(geo_package_file)
                            csv_stat_info = os.stat(output_filename)
                            gpkg_mod_time = datetime.fromtimestamp(gpkg_stat_info.st_mtime)
                            csv_mod_time = datetime.fromtimestamp(csv_stat_info.st_mtime)
                            csv_export_old = gpkg_mod_time > csv_mod_time # Only overwrite CSV export if GeoPackage is newer

                        padded_db_name = self.database.ljust(self.max_length + 2)
                        if need_csv_export or csv_export_old:
                            ret_code, error_msg, output_filename = export_geopackage_to_csv(geo_package_file)
                            if ret_code == RetCode.EXPORT_OK:
                                self.write_log_line(f'{padded_db_name} CSV export OK  ({output_filename})\n')
                            else:
                                self.write_log_line(f'{padded_db_name} Error during CSV export: {error_msg}\n')
                        elif not csv_export_old:
                            message = f'{padded_db_name} Skipping CSV export, because existing CSV export is newer than the GeoPackage.\n'
                            QgsMessageLog.logMessage(message, MESSAGE_CATEGORY, Qgis.Info)
                            self.write_log_line(message)
                    else:
                        print(f'ret: {ret}  self.last_error: {self.last_error} self.csv: {self.csv}')

                    self.last_database = self.database
                    #QgsMessageLog.logMessage(f"Export of {self.database} done, ret : {ret}", MESSAGE_CATEGORY, Qgis.Info)
        except Exception as err:
            traceback.print_exc()
            print(f"Exception from export_to_geopackage() Exception: {err}")
            QgsMessageLog.logMessage(f"Exception from export_to_geopackage() Exception: {err}", MESSAGE_CATEGORY, Qgis.Info)
            return False

    def report_export_status(self, database, ret, last_error):
        """Report back export status"""
        if ret == RetCode.EXPORT_OK:
            self.export_status_callback(database, True, None)
        else:
            self.export_status_callback(database, False, last_error)

    def finished(self, result):
        """Task finished"""
        print(f"Subtask with last db: {self.last_database} finished with result: {result}")
        #self.export_status_callback(self.last_database, result, self.last_error)
        self.last_error = None

    def cancel(self):
        """Task Canceled"""
        if self.database == 'S19901001' or self.last_database == 'S19901001':
            print(f'GeoPackageBulkExportSubtask::cancel() self.database: {self.database}  self.last_database: {self.last_database}')
            traceback.print_stack()
        QgsMessageLog.logMessage(f"GeoPackage export {self.description()} was canceled", MESSAGE_CATEGORY, Qgis.Info)
        super().cancel()
