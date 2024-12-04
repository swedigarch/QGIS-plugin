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

import os
import sqlite3
import string
import typing
import traceback
from xmlrpc.client import Boolean
import numpy as np
from qgis.core import (
  QgsSettings,
  QgsTask,
  Qgis,
  QgsApplication,
  QgsMessageLog,
  QgsVectorFileWriter, QgsVectorLayer, QgsField, QgsFeature, QgsProject, QgsFields
)
from qgis.PyQt import uic, QtWidgets
from PyQt5.QtWidgets import QDialogButtonBox, QMessageBox, QDialog
from PyQt5.QtCore import QVariant ,QAbstractTableModel, QModelIndex, Qt
import pandas as pd
import processing
from . import utils as Utils
from . import browse_relations_utils as BrowseRelationsUtils
from . import class_subclass_browser_utils as ClassSubclassBrowserUtils
from .select_geo_package_dalog import SelectGeoPackageDialog
from .help_dialog import HelpDialog
from .class_subclass_browser_parent_id_dialog import ClassSubclassBrowserParentIdDialog
######################################
#from . import browse_relations_utils as browse_relations_utils
######################################
MESSAGE_CATEGORY = 'Class_Subclass_Browser'

'''This loads your .ui file so that 
PyQt can populate your plugin with the elements from Qt Designer'''
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'intrasis_analysis_browse_class_subclass.ui'))

class IntrasisAnalysisBrowseTablesDialog(QtWidgets.QDialog, FORM_CLASS):
    """Browse tables dialog"""
    def __init__(self, parent=None):
        """Constructor."""
        super(IntrasisAnalysisBrowseTablesDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        #Prepare variables
        self.setupUi(self)
        self.selected_gpkg_name = None
        self.selected_gpkg = None
        self.archeological_classes = None
        self.current_gpkg = None
        self.selected_gpkg_string = None
        self.export_folder = None
        self.class_subclass_attributes = None
        #Set titles and prepare for translation
        self.title_string = None
        self.pushButton_read_to_table.setText(self.tr("Load Table"))
        self.pushButton_load_to_map.setText(self.tr("Create Layer"))
        self.pushButton_export_as_chart.setText(self.tr("Save Table As..."))
        self.buttonBox_close_help.button(
            QDialogButtonBox.StandardButton.Close).setText(self.tr("Close"))
        self.buttonBox_close_help.button(
            QDialogButtonBox.StandardButton.Help).setText(self.tr("Help"))
        self.subclass_items_dict = {'All Objects':self.tr('All Objects')
                                    ,'Every SubClass':self.tr('All SubClasses')
                                    , 'No SubClass':self.tr('No SubClass')}
        ############################################################
        self.pb_open_parent_id_dialog.setText(self.tr("Generate ParentId"))
        self.pb_open_parent_id_dialog.clicked.connect(self.generate_parent_id_task)
        self.pb_open_parent_id_dialog.setEnabled(False)
        ############################################################
        #Pushbutton logics
        self.pushButton_read_to_table.setEnabled(False)
        self.pushButton_export_as_chart.setEnabled(False)
        self.comboBox_class.currentIndexChanged.connect(
            self.update_combobox_subclass)
        self.comboBox_class.currentIndexChanged.connect(
            self.enable_button_read_to_table)
        self.comboBox_subclass.currentIndexChanged.connect(
            self.enable_button_read_to_table)
        self.pushButton_read_to_table.setEnabled(False)
        self.pb_open_parent_id_dialog.setEnabled(False)
        self.pushButton_read_to_table.clicked.connect(
            self.start_task_load_table)
        self.pushButton_export_as_chart.clicked.connect(self.export_as_chart)
        self.pushButton_load_to_map.setEnabled(False)
        self.pushButton_load_to_map.clicked.connect(self.load_to_qgis_layer)
        self.buttonBox_close_help.rejected.connect(self.closed)
        self.rejected.connect(self.closed)
        self.buttonBox_close_help.helpRequested.connect(self.on_help_clicked)
        self.label_num_loaded_objects_info.setText('')

    def on_help_clicked(self):
        """Show Help dialog"""
        HelpDialog.show_help("ClassSubclassDialog")

    def generate_parent_id_task(self) -> bool:
        self.pb_open_parent_id_dialog.setEnabled(False)
        globals()['Create Relations Table'] = QgsTask.fromFunction('Create_Relations_Table_Task'
                                                          , self.generate_parent_id
                                                          , on_finished=self.handle_result_generate_parent_id
                                                          #, objects=objects_dataframe.copy(deep=True)
                                                          #, fields=fields_to_keep
                                                          #, group=group_name
                                                          #, layer_name=temp_layername)
                                                          )
        QgsApplication.taskManager().addTask(globals()['Create Relations Table'])

        return True

    def generate_parent_id(self, task:QgsTask):
        """Show dialog for generating parent id to objects without geometry"""
        task.setProgress(1)
        object_id_data_frame = self.class_subclass_attributes.objects_dataframe.copy()
        child_id_string = object_id_data_frame['object_id'].tolist()
        child_id_string = ', '.join(map(str, child_id_string))
        #relation_table = ClassSubclassBrowserUtils.get_relation_dataframe(self.current_gpkg, child_id_string)
        #relation_tableX = ClassSubclassBrowserUtils.get_relation_dataframeX(self.current_gpkg, child_id_string)
        relation_tableX = ClassSubclassBrowserUtils.get_relation_dataframeZ(self.current_gpkg, child_id_string, task)
        #task.setProgress(33)

        parent_id_string_df = ClassSubclassBrowserUtils.get_unique_id_string(relation_tableX, 'child_id','parent_class','ParentId')
        #print(parent_id_string_df.head(2))
        relation_tableX = pd.merge(relation_tableX, parent_id_string_df[['child_id', 'parent_class', 'ParentIdString']], how='left', on=['child_id', 'parent_class'])
        task.setProgress(75)

        grand_parent_id_string_df = ClassSubclassBrowserUtils.get_unique_id_string(relation_tableX, 'child_id','grand_parent_class','GrandParentId')
        relation_tableX = pd.merge(relation_tableX, grand_parent_id_string_df[['child_id', 'grand_parent_class', 'GrandParentIdString']], how='left', on=['child_id', 'grand_parent_class'])
        task.setProgress(77)

        great_grand_parent_id_string_df = ClassSubclassBrowserUtils.get_unique_id_string(relation_tableX, 'child_id','great_grand_parent_class','GreatGrandParentId')
        relation_tableX = pd.merge(relation_tableX, great_grand_parent_id_string_df[['child_id', 'great_grand_parent_class', 'GreatGrandParentIdString']], how='left', on=['child_id', 'great_grand_parent_class'])
        task.setProgress(80)
        relation_tableX['parent_count'] = relation_tableX.groupby(['child_id', 'parent_class'])['parent_id'].transform('nunique')
        task.setProgress(85)
        relation_tableX['grand_parent_count'] = relation_tableX.groupby(['child_id', 'grand_parent_class'])['grand_parent_id'].transform('nunique')
        task.setProgress(90)
        relation_tableX['great_grand_parent_count'] = relation_tableX.groupby(['child_id', 'great_grand_parent_class'])['great_grand_parent_id'].transform('nunique')
        #relation_tableX['parent_count'] = relation_tableX.groupby(['child_id', 'parent_class'])['parent_class'].transform('count')
        #relation_tableX['grand_parent_count'] = relation_tableX.groupby(['child_id', 'grand_parent_class'])['grand_parent_class'].transform('count')
        #relation_tableX['great_grand_parent_count'] = relation_tableX.groupby(['child_id', 'great_grand_parent_class'])['great_grand_parent_class'].transform('count')
        
        #relation_tableX['parenthierarchycount'] = relation_tableX.groupby(['parenthierarchy']).transform('count')
        relation_tableX['parenthierarchy_count'] = relation_tableX.groupby('parenthierarchy')['parenthierarchy'].transform('size')
        #print(relation_tableX.columns.tolist())
        #print(relation_table.columns.tolist())
        #relation_tableX = relation_tableX.drop_duplicates(subset=['parent_class','grand_parent_class','great_grand_parent_class'])[['parent_class','grand_parent_class','great_grand_parent_class','parenthierarchy','parenthierarchy_count']]
        task.setProgress(95)

        child_class_string = ClassSubclassBrowserUtils.get_child_class(self.current_gpkg, child_id_string)
        #parent_dialog_df = relation_table.drop_duplicates(subset=['parent_class','grand_parent_class','great_grand_parent_class'])[['parent_class','grand_parent_class','great_grand_parent_class','parenthierarchy','parenthierarchy_count']]
        parent_dialog_df = relation_tableX.drop_duplicates(subset=['parent_class','grand_parent_class','great_grand_parent_class'])[['parent_class','grand_parent_class','great_grand_parent_class','parenthierarchy','parenthierarchy_count']]

        QgsMessageLog.logMessage(
            f'Creating Relation Table {task.description()}'
            ,MESSAGE_CATEGORY
            , Qgis.Info)
        task.setProgress(100)
        QgsMessageLog.logMessage(f'Finished {task.description()}: {task.progress()}'
                                 ,MESSAGE_CATEGORY, Qgis.Info)
        #return [relation_table, child_class_string, parent_dialog_df]
        if task.isCanceled():
            self.stopped(task)
            return None
        return [relation_tableX, child_class_string, parent_dialog_df]

    def stopped(self, task):
        QgsMessageLog.logMessage(
        'Task "{name}" was cancelled'.format(name=task.description()),
        MESSAGE_CATEGORY, Qgis.Info)
    
    def handle_result_generate_parent_id(self, exception, result):
        if exception is None:
            if result is None:
                message_text = self.tr('''Completed with no exception and no result (probably manually canceled by the user)''')
                QgsMessageLog.logMessage(
                    message_text,
                    MESSAGE_CATEGORY, Qgis.Warning)
                self.pb_open_parent_id_dialog.setEnabled(True)
            else:
                relation_table = result[0]
                child_class_string = result[1]
                parent_dialog_df = result[2]
                parent_id_dlg = ClassSubclassBrowserParentIdDialog(parent_dialog_df, child_class_string)
                parent_id_dlg.tableView_parent.setModel(TableModelParenID(table_data=parent_dialog_df))
                parent_id_dlg.tableView_parent.setSortingEnabled(True)
                parent_id_dlg.tableView_parent.resizeColumnsToContents()
                self.pb_open_parent_id_dialog.setEnabled(True)
                def handle_custom_signal(settings):
                    print(f"fick dessa data: {settings}")
                    print(f"self.parent_id_dlg.settings: {parent_id_dlg.settings}")
                    values = parent_id_dlg.settings
                    self.create_parent_id_based_on_chosen_relation(values, relation_table)
                parent_id_dlg.customSignal.connect(handle_custom_signal)
                parent_id_dlg.show(self)
                
        #self.create_parent_id_based_on_chosen_relation(self.data, relation_table)
                #if self.parent_id_dlg.exec_() == QDialog.Accepted:
                #    values = self.parent_id_dlg.settings
                #    self.create_parent_id_based_on_chosen_relation(values, relation_table)
                #if self.parent_id_dlg.exec_() == QDialog.Accepted:
                #    values = self.parent_id_dlg.settings
                #    self.create_parent_id_based_on_chosen_relation(values, relation_table)
        else:
            QgsMessageLog.logMessage(f"Exception: {exception}",
                                 MESSAGE_CATEGORY, Qgis.Critical)
            self.pb_open_parent_id_dialog.setEnabled(True)
            raise exception

    def create_parent_id_based_on_chosen_relation(self, values, relation_table):
        #print(f"Received values: {values} Start extracting relations")
        chosen_parentid = None
        multiple_parents = ''
        multiple_grandparents = ''
        multiple_greatgrandparents = ''
        if(len(values[0])>0 and len(values[1])==0 and len(values[2])==0):
            chosen_parentid = 'filtrering på parent'
            #resultat = relation_table.query(f"parent_class == '{values[0]}'")[['child_id','parent_id', 'ParentId', 'parent_count', 'parenthierarchy','ParentIdString']]
            resultat = relation_table.query(f"parent_class == '{values[0]}'")[['child_id','parent_id', 'ParentId', 'parent_count','ParentIdString']]
            resultat.drop_duplicates(inplace=True)
            resultat['log'] = 'OK'
            resultat['ParentClass'] = values[0]
            resultat.loc[resultat['parent_count'] > 1, 'log'] = 'Flera träffar detekterade'
            #för att kunna hantera missing value behöver Int64 används
            resultat['parent_id'] = resultat['parent_id'].astype('Int64')
            resultat['ParentId'] = resultat['ParentId'].astype('Int64')
            resultat.loc[resultat['parent_count'] > 1, ['parent_id','ParentId']] = pd.NA
            if (resultat['parent_count'] != 1).any():
                multiple_parents = 'flera parents'
            #resultat.drop(columns=['parent_id','parent_count'], inplace=True)
        if(len(values[0])>0 and len(values[1])>0 and len(values[2])==0):
            chosen_parentid = 'filtrering på parent och grandparent'
            #resultat = relation_table.query(f"parent_class == '{values[0]}' and grand_parent_class =='{values[1]}'")[['child_id','parent_id','grand_parent_id', 'ParentId','GrandParentId', 'parent_count','grand_parent_count', 'parenthierarchy','ParentIdString','GrandParentIdString']]
            resultat = relation_table.query(f"parent_class == '{values[0]}' and grand_parent_class =='{values[1]}'")[['child_id','parent_id','grand_parent_id', 'ParentId','GrandParentId', 'parent_count','grand_parent_count','ParentIdString','GrandParentIdString']]
            resultat.drop_duplicates(inplace=True)
            resultat['log'] = 'OK'
            resultat['ParentClass'] = values[0]
            resultat['GrandParentClass'] = values[1]
            resultat.loc[resultat['parent_count'] > 1, 'log'] = 'Flera träffar detekterade'
            resultat.loc[resultat['grand_parent_count'] > 1, 'log'] = 'Flera träffar detekterade'
            resultat['parent_id'] = resultat['parent_id'].astype('Int64')
            resultat['ParentId'] = resultat['ParentId'].astype('Int64')
            resultat['grand_parent_id'] = resultat['grand_parent_id'].astype('Int64')
            resultat['GrandParentId'] = resultat['GrandParentId'].astype('Int64')
            resultat.loc[resultat['parent_count'] > 1, ['parent_id','ParentId','grand_parent_id','GrandParentId']] = pd.NA
            resultat.loc[resultat['grand_parent_count'] > 1, ['grand_parent_id','GrandParentId']] = pd.NA
            if (resultat['parent_count'] != 1).any():
                multiple_parents = 'flera parents, '
            if (resultat['grand_parent_count'] != 1).any():
                multiple_grandparents = 'flera grand parents'
            #resultat.drop(columns=['parent_id','parent_count','grand_parent_id','grand_parent_count'], inplace=True)
        
        if(len(values[0])>0 and len(values[1])>0 and len(values[2])>0):
            chosen_parentid = 'filtrering på parent, grandparent och greatgrandparent'
            #resultat = relation_table.query(f"parent_class == '{values[0]}' and grand_parent_class =='{values[1]}' and great_grand_parent_class =='{values[2]}'")[['child_id','parent_id','grand_parent_id','great_grand_parent_id', 'ParentId','GrandParentId','GreatGrandParentId', 'parent_count','grand_parent_count','great_grand_parent_count', 'parenthierarchy','ParentIdString','GrandParentIdString','GreatGrandParentIdString']]
            resultat = relation_table.query(f"parent_class == '{values[0]}' and grand_parent_class =='{values[1]}' and great_grand_parent_class =='{values[2]}'")[['child_id','parent_id','grand_parent_id','great_grand_parent_id', 'ParentId','GrandParentId','GreatGrandParentId', 'parent_count','grand_parent_count','great_grand_parent_count','ParentIdString','GrandParentIdString','GreatGrandParentIdString']]
            resultat.drop_duplicates(inplace=True)
            resultat['log'] = 'OK'
            resultat['ParentClass'] = values[0]
            resultat['GrandParentClass'] = values[1]
            resultat['GreatGrandParentClass'] = values[2]
            resultat.loc[resultat['parent_count'] > 1, 'log'] = 'Flera träffar detekterade'
            resultat.loc[resultat['grand_parent_count'] > 1, 'log'] = 'Flera träffar detekterade'
            resultat.loc[resultat['great_grand_parent_count'] > 1, 'log'] = 'Flera träffar detekterade'
            resultat['parent_id'] = resultat['parent_id'].astype('int64')
            resultat['ParentId'] = resultat['ParentId'].astype('Int64')
            resultat['grand_parent_id'] = resultat['grand_parent_id'].astype('int64')
            resultat['GrandParentId'] = resultat['GrandParentId'].astype('Int64')
            resultat['great_grand_parent_id'] = resultat['great_grand_parent_id'].astype('int64')
            resultat['GreatGrandParentId'] = resultat['GreatGrandParentId'].astype('Int64')
            resultat.loc[resultat['parent_count'] > 1, ['parent_id','ParentId','grand_parent_id','GrandParentId','great_grand_parent_id','GreatGrandParentId']] = pd.NA
            resultat.loc[resultat['grand_parent_count'] > 1, ['grand_parent_id','GrandParentId','great_grand_parent_id','GreatGrandParentId']] = pd.NA
            resultat.loc[resultat['great_grand_parent_count'] > 1, ['great_grand_parent_id','GreatGrandParentId']] = pd.NA
            if (resultat['parent_count'] != 1).any():
                multiple_parents = 'flera parents, '
            if (resultat['grand_parent_count'] != 1).any():
                multiple_grandparents = 'flera grand parents, '
            if (resultat['great_grand_parent_count'] != 1).any():
                multiple_greatgrandparents = 'flera great grand parents'
            #resultat.drop(columns=['parent_id','parent_count','grand_parent_id','grand_parent_count','great_grand_parent_id','great_grand_parent_count'], inplace=True)
        #print(chosen_parentid)
        resultat.drop_duplicates(inplace=True)
        #print(resultat)

        if (len(multiple_parents) > 0 or len(multiple_grandparents) > 0 or len(multiple_greatgrandparents) > 0):
            # Skapa meddelanderutan
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            #msg.setText("Observera!")
            msg.setText(f"Observera! För minst ett objekt detekterades {multiple_parents}\n{multiple_grandparents}\n{multiple_greatgrandparents}")
            #msg.setInformativeText(f"Observera! För minst ett objekt detekterades {multiple_parents}{multiple_grandparents}{multiple_greatgrandparents}")
            msg.setWindowTitle("Varning")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.adjustSize()
            # Visa meddelanderutan och vänta på att användaren klickar OK
            msg.exec_()

        #Remove columns not necessary to layer attributes table:
        columns_to_remove=['parent_id','parent_count','grand_parent_id','grand_parent_count','great_grand_parent_id','great_grand_parent_count']
        resultat.drop(columns=[col for col in columns_to_remove if col in resultat.columns], inplace=True)
        #resultat.drop(columns=['parent_id','parent_count','grand_parent_id','grand_parent_count','great_grand_parent_id','great_grand_parent_count'], inplace=True)
        #resultat.drop(columns=['parent_id','parent_count'], inplace=True)

        self.load_layer_with_parent_id_to_qgis_layer(resultat)

    def showEvent(self, event):
        """DialogShow event, returns selected databases to top list."""
        super(IntrasisAnalysisBrowseTablesDialog, self).showEvent(event)
        self.title_string = "Intrasis Class/Subclass Browser "
        self.setWindowTitle(self.tr(self.title_string))
        self.init_gui()

    def init_gui(self):
        '''Initialise GUI'''
        self.setWindowTitle(self.tr(self.title_string
                                    +self.selected_gpkg_string))

    def closeEvent(self, event):
        """The close dialog event (QCloseEvent)"""
        point = self.pos()
        settings = QgsSettings()
        settings.setValue("SwedigarchGeotools/dialog_position", point)
        self.comboBox_class.clear()
        self.comboBox_subclass.clear()
        self.selected_gpkg_name = None
        self.selected_gpkg = None
        self.current_gpkg = None
        self.label_num_loaded_objects_info.setText('')
        if self.class_subclass_attributes is not None:
            try:
                self.class_subclass_attributes.clear_qtablewidget()
                print(self.tr("analysis dialog closed"))
            except Exception as ex:
                QgsMessageLog.logMessage(f'Table not cleared {ex}'
                                 ,MESSAGE_CATEGORY, Qgis.Info)
                traceback.print_exc()
                print(f"Error in {ex}")
        print(self.tr("analysis dialog closed"))

    def closed(self):
        """The close dialog event (QCloseEvent)"""
        self.comboBox_class.clear()
        self.comboBox_subclass.clear()
        self.selected_gpkg_name = None
        self.selected_gpkg = None
        self.current_gpkg = None
        self.pushButton_read_to_table.setEnabled(False)
        self.pb_open_parent_id_dialog.setEnabled(False)
        self.pushButton_load_to_map.setEnabled(False)
        self.pushButton_export_as_chart.setEnabled(False)
        self.label_num_loaded_objects_info.setText('')
        try:
            self.class_subclass_attributes.clear_qtablewidget()
            print(self.tr("analysis dialog closed"))
        except Exception as ex:
            print(self.tr("analysis dialog closed")+f' {ex}')

    def show_messagebox_no_loaded_gpkg(self, icon):
        """Show a message box to inform user that intrasis
        geopackage must be loaded before opening class/subclasss browser"""
        msg_box = QMessageBox()
        #msg_box.setWindowIcon(icon)
        msg_box.setWindowTitle(self.tr("No intrasis geopackage loaded"))
        msg_box.setText(self.tr("To view data in the Class/Subclass browser one or more Intrasis Geopackages must be loaded"))
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.exec()

    def check_if_intrasis_geopackage_is_loaded(self) -> bool:
        '''Check if Intrasis Geopackage is loaded in QGIS'''
        intrasis_gpkg_loaded = False
        gpkg_files = Utils.find_geo_packages()
        gpkg_files_paths = list(gpkg_files.keys())

        for gpkg_file in gpkg_files_paths:

            if Utils.is_intrasis_gpkg_export(gpkg_file) is True:
                intrasis_gpkg_loaded = True

        return intrasis_gpkg_loaded

    def select_and_activate_intrasis_geopackage(self) -> bool:
        '''Activate loaded Intrasis geopackage if single
        , if multiple loaded activate SelectGeoPackageDialog'''
        user_select_klicked = False
        gpkg_files = Utils.find_geo_packages()
        gpkg_files_paths = list(gpkg_files.keys())
        gpgk_files_intrasis = []
        for gpkg_file in gpkg_files_paths:

            if Utils.is_intrasis_gpkg_export(gpkg_file) is True:
                gpgk_files_intrasis.append(gpkg_file)

        if self.selected_gpkg_name is None or len(gpgk_files_intrasis) > 1:
            selected_gpkg_path_and_name = ''
        #get selected gpkg, activate selected
            #if len(gpgk_files_intrasis) > 1
            if len(gpgk_files_intrasis) > 1 and self.selected_gpkg is None :
                sel_dlg = SelectGeoPackageDialog()
                if sel_dlg.exec_():
                    selected_gpkg_path_and_name = sel_dlg.selected_geo_package
                    user_select_klicked = True

            if len(gpgk_files_intrasis) == 1:
                self.selected_gpkg = gpgk_files_intrasis
                selected_gpkg_path_and_name = gpgk_files_intrasis[0]
                user_select_klicked = True

            if len(gpgk_files_intrasis) == 0:
                print(self.tr('No intrasis geopackage(s) loaded'))

            #Get Intrasis geopackage name
            if len(selected_gpkg_path_and_name) > 0:
                self.archeological_classes = Utils.get_data_from_gpkg(
                    selected_gpkg_path_and_name,
                    4,
                    no_subclass_string=self.subclass_items_dict['No SubClass'])
                self.update_combobox_class()
                self.selected_gpkg_string = selected_gpkg_path_and_name.split('/')[-1].split('.')[0]
                self.current_gpkg = selected_gpkg_path_and_name
        return user_select_klicked

    def load_layer_with_parent_id_to_qgis_layer(self, resultat) -> bool:
        '''Creates QGIS layers from Class/Subclass browser data by 
        joining the browser data with geometry layers objects that 
        do not hold geometry is created as table without geometry'''

        #self.disable_load_to_map()
        objects_dataframe_ = None
        objects_dataframe_ = self.class_subclass_attributes.objects_dataframe.copy()
        objects_dataframe_.reset_index(drop=True, inplace=True)
        objects_dataframe_.set_index('object_id')

        # Merging with a left join
        objects_dataframe_ = pd.merge(objects_dataframe_, resultat, left_on='object_id', right_on='child_id', how='left')
        objects_dataframe_.set_index('object_id')
        objects_dataframe_.drop_duplicates(inplace=True)

        #Remove columns not necessary to layer attributes table:
        objects_dataframe_.drop(columns=['child_id'], inplace=True)

        #Create layer groups QGIS Table of contents "TOC"
        selected_gpkg_name = self.current_gpkg.split('/')[-1]
        group_name="Class_Subclass"+'.'+selected_gpkg_name.rsplit('.',1)[0]
        root = QgsProject.instance().layerTreeRoot()
        group_already_exist = 0
        if len(root.findGroups()) > 0:
            for group in root.findGroups():
                if group.name() == group_name:
                    group_already_exist = 1
        if len(root.findGroups()) == 0:
            group = root.insertGroup(0, group_name)
        if group_already_exist == 0:
            group = root.insertGroup(0, group_name)
        if group_already_exist == 1:
            Utils.expand_group(group_name)
        #set layer name
        temp_layername = self.class_subclass_attributes.temp_layername

        #Create layer ("table") with no geometry
        if len(objects_dataframe_.index) > 0:
            globals()['Create non geometry layer with ParentId'] = QgsTask.fromFunction(
                'load_to_qgis_layer_task_2'
                , self.create_non_spatial_parentid_layer
                , on_finished=self.add_non_geo_layer
                , objects=objects_dataframe_.copy(deep=True)
                , group=group_name
                , layer_name=temp_layername)
            QgsApplication.taskManager().addTask(globals()['Create non geometry layer with ParentId'])

        return True

    def load_to_qgis_layer(self) -> bool:
        '''Creates QGIS layers from Class/Subclass browser data by 
        joining the browser data with geometry layers objects that 
        do not hold geometry is created as table without geometry'''

        self.disable_load_to_map()
        #Get GeoObjectId
        conn = sqlite3.connect(self.current_gpkg)
        geo_object_id_dataframe = None
        objects_dataframe_ = None
        objects_dataframe = None
        #Select all objects that has geometry
        sql_query_string_objects_with_geometry = 'select object_id,GeoObjectId,spatial_type from (SELECT o.object_id, f.GeoObjectId, f.spatial_type, CASE WHEN f.object_id IS NULL THEN 0 ELSE 1 END AS hasgeometry FROM objects o LEFT JOIN features f ON o.object_id = f.object_id) where hasgeometry == 1'
        geo_object_id_dataframe = pd.read_sql_query(sql_query_string_objects_with_geometry, conn)

        #Select all objects that have no geometry
        sql_query_string_objects_with_no_geometry ='select object_id from(SELECT o.object_id, f.GeoObjectId,CASE WHEN f.object_id IS NULL THEN 0 ELSE 1 END AS hasgeometry FROM objects o LEFT JOIN features f ON o.object_id = f.object_id) where hasgeometry == 0'
        object_id_no_geometry = pd.read_sql_query(sql_query_string_objects_with_no_geometry, conn)
        conn.close()
        objects_dataframe_ = self.class_subclass_attributes.objects_dataframe.copy()
        objects_dataframe_.reset_index(drop=True, inplace=True)
        objects_dataframe_.set_index('object_id')

        #Get fields "attribute names" to end result
        fields_to_keep = list(objects_dataframe_.columns.values.tolist())

        #Create layer groups QGIS Table of contents "TOC"
        selected_gpkg_name = self.current_gpkg.split('/')[-1]
        group_name="Class_Subclass"+'.'+selected_gpkg_name.rsplit('.',1)[0]
        root = QgsProject.instance().layerTreeRoot()
        group_already_exist = 0
        if len(root.findGroups()) > 0:
            for group in root.findGroups():
                if group.name() == group_name:
                    group_already_exist = 1
        if len(root.findGroups()) == 0:
            group = root.insertGroup(0, group_name)
        if group_already_exist == 0:
            group = root.insertGroup(0, group_name)
        if group_already_exist == 1:
            Utils.expand_group(group_name)
        #set layer name
        temp_layername = self.class_subclass_attributes.temp_layername

        #Create layer ("table") with no geometry
        if not object_id_no_geometry.empty:
            non_geo_df = self.class_subclass_attributes.objects_dataframe.copy()
            object_id_no_geo = list(object_id_no_geometry['object_id'])
            objects_dataframe_non_geo = non_geo_df.query(
                'object_id in @object_id_no_geo').copy()
            if len(objects_dataframe_non_geo.index) > 0:
                globals()['Create non geometry layer'] = QgsTask.fromFunction(
                    'load_to_qgis_layer_task'
                    , self.create_non_spatial_layer
                    , on_finished=self.add_non_geo_layer
                    , objects=objects_dataframe_non_geo.copy(deep=True)
                    , group=group_name
                    , layer_name=temp_layername)

                QgsApplication.taskManager().addTask(globals()['Create non geometry layer'])


        #Create layer(s) with geometry
        if not geo_object_id_dataframe.empty:
            geo_df = self.class_subclass_attributes.objects_dataframe.copy()
            geo_df.reset_index(drop=True, inplace=True)
            geo_df.set_index('object_id')
            object_id_geo = list(geo_object_id_dataframe['object_id'])
            objects_dataframe_geo = geo_df.query('object_id in @object_id_geo').copy()
            geo_object_id_dataframe = geo_object_id_dataframe.set_index('object_id')
            fields_to_keep.append('GeoObjectId')
            fields_to_keep.append('spatial_type')

            try:
                objects_dataframe = objects_dataframe_geo.join(geo_object_id_dataframe, on='object_id', how='left')
            except Exception as ex:
                QgsMessageLog.logMessage(f'{ex}'
                                 ,MESSAGE_CATEGORY, Qgis.Info)
                objects_dataframe = objects_dataframe_geo.merge(geo_object_id_dataframe, on='object_id', how='left')
            if len(objects_dataframe) > 0:
                #Create a QgsTask from a function mainly to prevent QGIS becoming unresponsive
                #The task is set into globals()['Create geometry layer'], this was the only way
                #to get it working at all. Examples in pyqgis cookbook did not work. Since QgsTask
                #Will run as as thread separate from the main thread it is important that the functions
                #do not access objects on the QGIS main thread or objects in other threads or QGIS will
                #behave unpredictable and crash. Also Pandas dataframes must be deep copied.
                globals()['Create geometry layer'] = QgsTask.fromFunction('Create_spatial_layer_task'
                                                          , self.create_spatial_layer
                                                          , on_finished=self.add_geo_layer
                                                          , objects=objects_dataframe.copy(deep=True)
                                                          , fields=fields_to_keep
                                                          , group=group_name
                                                          , layer_name=temp_layername)
                QgsApplication.taskManager().addTask(globals()['Create geometry layer'])

        return True

    def create_non_spatial_parentid_layer(self, task:QgsTask, objects:pd.DataFrame
                                 , group:str, layer_name:str) -> list[QgsVectorLayer,str,str]: #används fields?
        '''Create layer that contain no geometries'''
        QgsMessageLog.logMessage(f'Started task {task.description()}'
                                 ,MESSAGE_CATEGORY, Qgis.Info)
        task.setProgress(1)
        objects_dataframe = objects
        group_name = group
        #Create layer name
        temp_layername = layer_name
        #Create a memory layer without geometry ("table")
        #Important that QgsVectorLayer is not yet in the QGIS table of contents or QGIS will crash
        temp = None
        temp = QgsVectorLayer("none","nongeo","memory")
        temp_data = None
        temp_data = temp.dataProvider()

        #Enter layer editing mode so that the layer can be filled with data
        temp.startEditing()
        objects_dataframe_colnames = list(objects_dataframe.columns.values.tolist())
        attribute_datatypes = dict(zip(objects_dataframe_colnames, [QVariant.String]*len(objects_dataframe_colnames)))
        #Get datatypes attribute from self.class_subclass_attributes object, note .copy()
        #If not copied the attributes_datatypes_dict will not be a separate object and will cause problems
        attributes_datatypes_dict = self.class_subclass_attributes.attributes_datatypes_dict.copy()

        if len(attributes_datatypes_dict) != 0:
            for attrib in attributes_datatypes_dict:
                if attrib is not None:
                    attributes_datatypes_dict[attrib] = Utils.get_qvariant_type_from_attribute_data_type(attributes_datatypes_dict[attrib])
        #Because not all datatypes exist in self.class_subclass_attributes.attributes_datatypes_dict
        #only datatypes from attributes.datatypes the rest of the datatypes is set here 
        attribute_datatypes['IntrasisId'] = QVariant.Int
        attribute_datatypes['object_id'] = QVariant.Int
        attribute_datatypes['Name'] = QVariant.String
        attribute_datatypes['Class'] = QVariant.String
        attribute_datatypes['SubClass'] = QVariant.String
        #Update the dictionary of datatypes
        for attrib in attributes_datatypes_dict:
            try:
                attribute_datatypes[attrib] = attributes_datatypes_dict[attrib]
            except Exception as ex:
                QgsMessageLog.logMessage(f'Failed to set datatype of {attrib} from attributes.data_type defaulting to string {ex}'
                                         ,MESSAGE_CATEGORY, Qgis.Info)

        #Set datatypes of objects_dataframe according to the datatypes in attribute_datatypes
        #If setting of datatype fails, datatype is not changed. A common problem is handling
        #of missing values. For instance not all numpy datatypes that is used in a Pandas dataframe
        #can handle missing values if datatype is integer and contains missing values it must be converted
        #to Int64 or float64 to be able to hold missing values as NaN
        #print(f"objects_dataframe datatypes: {objects_dataframe.dtypes}")
        for col in objects_dataframe.columns:
            if attribute_datatypes[col] in [QVariant.Int]:
                try:
                    objects_dataframe[col] = pd.to_numeric(objects_dataframe[col], errors='coerce')
                except Exception as ex:
                    #print('int')
                    #objects_dataframe[col] = objects_dataframe[col].astype('Int64')
                    objects_dataframe.astype({col: 'Int64'}).dtypes
                    QgsMessageLog.logMessage(f'Numeric conversion failed, attribute {col} {ex} NaN introduced'
                                             ,MESSAGE_CATEGORY, Qgis.Info)

            if attribute_datatypes[col] in [QVariant.Double]:
                try:
                    objects_dataframe[col] =  objects_dataframe[col].apply(float)
                except Exception as ex:
                    #print(f'double {col}')
                    objects_dataframe[col] = pd.to_numeric(objects_dataframe[col], errors='coerce')
                    #print('double')
                    QgsMessageLog.logMessage(f'Numeric conversion failed attribute, {col} {ex} NaN introduced'
                                             ,MESSAGE_CATEGORY, Qgis.Info)

            if attribute_datatypes[col] in [QVariant.Date]:
                try:
                    objects_dataframe[col] = pd.to_datetime(objects_dataframe[col],errors='coerce')
                except Exception as ex:
                    #print('date')
                    QgsMessageLog.logMessage(f'Date/time conversion failed attribute, {col} {ex} NaN introduced'
                                             ,MESSAGE_CATEGORY, Qgis.Info)


            if attribute_datatypes[col] in [QVariant.Bool]:
                try:
                    objects_dataframe[col] = objects_dataframe[col].astype(bool,errors='ignore')
                except Exception as ex:
                    #print('bool')
                    QgsMessageLog.logMessage(f'Boolean conversion failed attribute, {col} {ex} NaN introduced'
                                             ,MESSAGE_CATEGORY, Qgis.Info)

        #Create attribute fields for the QGS layer
        col_dict = dict(zip(objects_dataframe.columns, objects_dataframe.dtypes.apply(lambda x: x.name)))

        #QGIS feature is limited to QVariant types
        type_map = {'Int64':QVariant.Int,'int64':QVariant.Int
                    ,'int32':QVariant.Int,'float64':QVariant.Double
                    ,'object':QVariant.String, 'bool':QVariant.Bool
                    ,'datetime64[ns]':QVariant.Date}
        attribute_fields = QgsFields()
        objects_dataframe_colnames = list(objects_dataframe.columns.values.tolist())
        for col_name in objects_dataframe_colnames:
            field = QgsField(str(col_name), type_map[col_dict[col_name]])
            attribute_fields.append(field)
        temp_data.addAttributes(attribute_fields)
        temp.updateFields()
        progressbarlength = 100
        total = len(objects_dataframe.index)
        increment = 10
        i = 1
        QgsMessageLog.logMessage(f'Starting feature creation: {task.description()}'
                                 ,MESSAGE_CATEGORY, Qgis.Info)
        #The features to the QGIS layer is created with a for loop
        #Create QGS features and set attributes
        i = 1
        #for ob in str_objects:
        for index, row in objects_dataframe.iterrows():
            feature = QgsFeature()
            feature.setFields(attribute_fields)
            progress = (progressbarlength*i) / total
            if int(progress) > increment:
                task.setProgress(int((progressbarlength*i)/total))
                increment += 10
            for column in objects_dataframe.columns:
                if pd.isna(row[column]):
                    feature.setAttribute(column, None)
                else:
                    feature.setAttribute(column, row[column])
            temp_data.addFeature(feature)
            i = i+1
            # Check if the task is cancelled
            if task.isCanceled():
                # Log a message and return None
                QgsMessageLog.logMessage(f'Task was canceled: {task.description()}'
                                         ,MESSAGE_CATEGORY, Qgis.Info)
                return None

        QgsMessageLog.logMessage(
            f'Commiting changes {task.description()}'
            ,MESSAGE_CATEGORY
            , Qgis.Info)
        temp.commitChanges()
        task.setProgress(100)
        QgsMessageLog.logMessage(f'Finished {task.description()}: {task.progress()}'
                                 ,MESSAGE_CATEGORY, Qgis.Info)
        #The layer (temp), group_name and temp_layername is returned
        #to on_finished=self.add_geo_layer
        return [temp, group_name, temp_layername]

    def create_non_spatial_layerOLD(self, task:QgsTask, objects:pd.DataFrame
                                 , group:str, layer_name:str) -> list[QgsVectorLayer,str,str]: #används fields?
        '''Create layer that contain no geometries'''
        QgsMessageLog.logMessage(f'Started task {task.description()}'
                                 ,MESSAGE_CATEGORY, Qgis.Info)
        task.setProgress(1)
        objects_dataframe = objects
        #objects_dataframe.drop(columns=['Djup'], inplace=True)
        group_name = group
        #Create layer name
        temp_layername = layer_name
        #Create a memory layer without geometry ("table")
        #Important that QgsVectorLayer is not yet in the QGIS table of contents or QGIS will chrash
        temp = None
        temp = QgsVectorLayer("none","nongeo","memory")
        temp_data = None
        temp_data = temp.dataProvider()

        #Enter layer editing mode so that the layer can be filled with data
        temp.startEditing()
        objects_dataframe_colnames = list(objects_dataframe.columns.values.tolist())
        attribute_datatypes = dict(zip(objects_dataframe_colnames, [QVariant.String]*len(objects_dataframe_colnames)))
        object_id_filter = list(objects_dataframe['object_id'])
        object_id_filter = str(object_id_filter).replace('[', '(').replace(']', ')')
        conn = sqlite3.connect(self.current_gpkg)
        conn.close()
        #Get datatypes attribute from self.class_subclass_attributes object, note .copy()
        #If not copied the attributes_datatypes_dict will not be a separate object and will cause problems
        attributes_datatypes_dict = self.class_subclass_attributes.attributes_datatypes_dict.copy()
        if len(attributes_datatypes_dict) != 0:
            for attrib in attributes_datatypes_dict:
                if attrib is not None:
                    attributes_datatypes_dict[attrib] = Utils.get_qvariant_type_from_attribute_data_type(attributes_datatypes_dict[attrib])
        #Because not all datatypes exist in self.class_subclass_attributes.attributes_datatypes_dict
        #only datatypes from attributes.datatypes the rest of the datatypes is set here 
        attribute_datatypes['IntrasisId'] = QVariant.Int
        attribute_datatypes['object_id'] = QVariant.Int
        attribute_datatypes['Name'] = QVariant.String
        attribute_datatypes['Class'] = QVariant.String
        attribute_datatypes['SubClass'] = QVariant.String

        #Update the dictionary of datatypes
        for attrib in attributes_datatypes_dict:
            try:
                attribute_datatypes[attrib] = attributes_datatypes_dict[attrib]
            except Exception as ex:
                QgsMessageLog.logMessage(f'Failed to set datatype of {attrib} from attributes.data_type defaulting to string {ex}'
                                         ,MESSAGE_CATEGORY, Qgis.Info)


        #Set datatypes of objects_dataframe according to the datatypes in attribute_datatypes
        #If setting of datatype fails, datatype is not changed. A common problem is handling
        #of missing values. For instance not all numpy datatypes that is used in a Pandas dataframe
        #can handle missing values if datatype is integer and contains missing values it must be converted
        #to Int64 or float64 to be able to hold missing values as NaN
        for col in objects_dataframe.columns:
            if attribute_datatypes[col] in [QVariant.Int]:
                try:
                    objects_dataframe[col] = pd.to_numeric(objects_dataframe[col], errors='coerce')
                except Exception as ex:
                    objects_dataframe.astype({col: 'Int64'}).dtypes
                    QgsMessageLog.logMessage(f'Numeric conversion failed, attribute {col} {ex} NaN introduced'
                                             ,MESSAGE_CATEGORY, Qgis.Info)

            if attribute_datatypes[col] in [QVariant.Double]:
                try:
                    #objects_dataframe[col] = objects_dataframe[col].astype('Float64')
                    objects_dataframe[col] =  objects_dataframe[col].apply(float)
                except Exception as ex:
                    #print(f'double: {col}')
                    objects_dataframe[col] = pd.to_numeric(objects_dataframe[col], errors='coerce')
                    QgsMessageLog.logMessage(f'Numeric conversion failed attribute, {col} {ex} NaN introduced'
                                             ,MESSAGE_CATEGORY, Qgis.Info)

            if attribute_datatypes[col] in [QVariant.Date]:
                try:
                    objects_dataframe[col] = pd.to_datetime(objects_dataframe[col],errors='coerce')
                except Exception as ex:
                    QgsMessageLog.logMessage(f'Date/time conversion failed attribute, {col} {ex} NaN introduced'
                                             ,MESSAGE_CATEGORY, Qgis.Info)


            if attribute_datatypes[col] in [QVariant.Bool]:
                try:
                    objects_dataframe[col] = objects_dataframe[col].astype(bool,errors='ignore')
                except Exception as ex:
                    QgsMessageLog.logMessage(f'Boolean conversion failed attribute, {col} {ex} NaN introduced'
                                             ,MESSAGE_CATEGORY, Qgis.Info)


        #Create attribute fields for the QGS layer
        col_dict = dict(zip(objects_dataframe.columns, objects_dataframe.dtypes.apply(lambda x: x.name)))

        #A QGIS feature is limited to QVariant types  
        type_map = {'Int64':QVariant.Int,'int64':QVariant.Int
                    ,'int32':QVariant.Int,'float64':QVariant.Double
                    ,'object':QVariant.String, 'bool':QVariant.Bool
                    ,'datetime64[ns]':QVariant.Date}
        attribute_fields = []
        objects_dataframe_colnames = list(objects_dataframe.columns.values.tolist())
        for col_name in objects_dataframe_colnames:
            field = QgsField(str(col_name), type_map[col_dict[col_name]])
            attribute_fields.append(field)

        temp_data.addAttributes(attribute_fields)
        temp.updateFields()
        progressbarlength = 100
        total = len(objects_dataframe.index)
        increment = 10
        i = 1
        QgsMessageLog.logMessage(f'Starting feature creation: {task.description()}'
                                 ,MESSAGE_CATEGORY, Qgis.Info)
        #The features to the QGIS layer is created with a for loop
        #The attributes are set using a string of values from the objects_dataframe
        # Create concatenated strings of attributes
        str_objects = objects_dataframe.apply(
            lambda x: x.astype(str).tolist(), axis=1).tolist()

        #Create QGS features and set attributes
        i = 1
        for ob in str_objects:
            feature = QgsFeature()
            newrow = ob
            progress = (progressbarlength*i) / total
            if int(progress) > increment:
                task.setProgress(int((progressbarlength*i)/total))
                increment += 10
            feature.setAttributes(newrow)
            temp_data.addFeature(feature)
            i = i+1
            # Check if the task is cancelled
            if task.isCanceled():
                # Log a message and return None
                QgsMessageLog.logMessage(f'Task was canceled: {task.description()}'
                                         ,MESSAGE_CATEGORY, Qgis.Info)
                return None
        QgsMessageLog.logMessage(
            f'Commiting changes {task.description()}'
            ,MESSAGE_CATEGORY
            , Qgis.Info)
        temp.commitChanges()
        task.setProgress(100)
        QgsMessageLog.logMessage(f'Finished {task.description()}: {task.progress()}'
                                 ,MESSAGE_CATEGORY, Qgis.Info)
        #The layer (temp), group_name and temp_layername is returned
        #to on_finished=self.add_geo_layer
        return [temp, group_name, temp_layername]

    def create_non_spatial_layer(self, task:QgsTask, objects:pd.DataFrame
                                 , group:str, layer_name:str) -> list[QgsVectorLayer,str,str]: #används fields?
        '''Create layer that contain no geometries'''
        QgsMessageLog.logMessage(f'Started task {task.description()}'
                                 ,MESSAGE_CATEGORY, Qgis.Info)
        task.setProgress(1)
        objects_dataframe = objects
        #objects_dataframe.drop(columns=['Djup'], inplace=True)
        group_name = group
        #Create layer name
        temp_layername = layer_name
        #Create a memory layer without geometry ("table")
        #Important that QgsVectorLayer is not yet in the QGIS table of contents or QGIS will chrash
        temp = None
        temp = QgsVectorLayer("none","nongeo","memory")
        temp_data = None
        temp_data = temp.dataProvider()

        #Enter layer editing mode so that the layer can be filled with data
        temp.startEditing()
        objects_dataframe_colnames = list(objects_dataframe.columns.values.tolist())
        attribute_datatypes = dict(zip(objects_dataframe_colnames, [QVariant.String]*len(objects_dataframe_colnames)))
        object_id_filter = list(objects_dataframe['object_id'])
        object_id_filter = str(object_id_filter).replace('[', '(').replace(']', ')')
        conn = sqlite3.connect(self.current_gpkg)
        conn.close()
        #Get datatypes attribute from self.class_subclass_attributes object, note .copy()
        #If not copied the attributes_datatypes_dict will not be a separate object and will cause problems
        attributes_datatypes_dict = self.class_subclass_attributes.attributes_datatypes_dict.copy()
        #print(f"len(attributes_datatypes_dict): {len(attributes_datatypes_dict)}")
        if len(attributes_datatypes_dict) != 0:
            for attrib in attributes_datatypes_dict:
                #print(f"attrib: {attrib} type(attrib): {type(attrib)}")
                #print(f"attrib == attrib: {attrib==attrib}")
                #if attrib is not None:
                #    attributes_datatypes_dict[attrib] = Utils.get_qvariant_type_from_attribute_data_type(attributes_datatypes_dict[attrib])
                if attrib == attrib:
                    if attrib is not None:
                        attributes_datatypes_dict[attrib] = Utils.get_qvariant_type_from_attribute_data_type(attributes_datatypes_dict[attrib])
                if attrib != attrib:
                    attributes_datatypes_dict[attrib] = QVariant.String
                if attrib is None:
                    attributes_datatypes_dict[attrib] = QVariant.String

        #Because not all datatypes exist in self.class_subclass_attributes.attributes_datatypes_dict
        #only datatypes from attributes.datatypes the rest of the datatypes is set here 
        attribute_datatypes['IntrasisId'] = QVariant.Int
        attribute_datatypes['object_id'] = QVariant.Int
        attribute_datatypes['Name'] = QVariant.String
        attribute_datatypes['Class'] = QVariant.String
        attribute_datatypes['SubClass'] = QVariant.String

        #Update the dictionary of datatypes
        for attrib in attributes_datatypes_dict:
            try:
                attribute_datatypes[attrib] = attributes_datatypes_dict[attrib]
            except Exception as ex:
                QgsMessageLog.logMessage(f'Failed to set datatype of {attrib} from attributes.data_type defaulting to string {ex}'
                                         ,MESSAGE_CATEGORY, Qgis.Info)


        #Set datatypes of objects_dataframe according to the datatypes in attribute_datatypes
        #If setting of datatype fails, datatype is not changed. A common problem is handling
        #of missing values. For instance not all numpy datatypes that is used in a Pandas dataframe
        #can handle missing values if datatype is integer and contains missing values it must be converted
        #to Int64 or float64 to be able to hold missing values as NaN
        for col in objects_dataframe.columns:
            if attribute_datatypes[col] in [QVariant.Int]:
                try:
                    objects_dataframe[col] = pd.to_numeric(objects_dataframe[col], errors='coerce')
                except Exception as ex:
                    objects_dataframe.astype({col: 'Int64'}).dtypes
                    QgsMessageLog.logMessage(f'Numeric conversion failed, attribute {col} {ex} NaN introduced'
                                             ,MESSAGE_CATEGORY, Qgis.Info)

            if attribute_datatypes[col] in [QVariant.Double]:
                try:
                    #objects_dataframe[col] = objects_dataframe[col].astype('Float64')
                    objects_dataframe[col] =  objects_dataframe[col].apply(float)
                except Exception as ex:
                    #print(f'double: {col}')
                    objects_dataframe[col] = pd.to_numeric(objects_dataframe[col], errors='coerce')
                    QgsMessageLog.logMessage(f'Numeric conversion failed attribute, {col} {ex} NaN introduced'
                                             ,MESSAGE_CATEGORY, Qgis.Info)

            if attribute_datatypes[col] in [QVariant.Date]:
                try:
                    objects_dataframe[col] = pd.to_datetime(objects_dataframe[col],errors='coerce')
                except Exception as ex:
                    QgsMessageLog.logMessage(f'Date/time conversion failed attribute, {col} {ex} NaN introduced'
                                             ,MESSAGE_CATEGORY, Qgis.Info)


            if attribute_datatypes[col] in [QVariant.Bool]:
                try:
                    objects_dataframe[col] = objects_dataframe[col].astype(bool,errors='ignore')
                except Exception as ex:
                    QgsMessageLog.logMessage(f'Boolean conversion failed attribute, {col} {ex} NaN introduced'
                                             ,MESSAGE_CATEGORY, Qgis.Info)


        #Create attribute fields for the QGS layer
        col_dict = dict(zip(objects_dataframe.columns, objects_dataframe.dtypes.apply(lambda x: x.name)))

        #A QGIS feature is limited to QVariant types  
        type_map = {'Int64':QVariant.Int,'int64':QVariant.Int
                    ,'int32':QVariant.Int,'float64':QVariant.Double
                    ,'object':QVariant.String, 'bool':QVariant.Bool
                    ,'datetime64[ns]':QVariant.Date}
        #attribute_fields = []
        attribute_fields = QgsFields()
        objects_dataframe_colnames = list(objects_dataframe.columns.values.tolist())
        for col_name in objects_dataframe_colnames:
            field = QgsField(str(col_name), type_map[col_dict[col_name]])
            attribute_fields.append(field)

        temp_data.addAttributes(attribute_fields)
        temp.updateFields()
        progressbarlength = 100
        total = len(objects_dataframe.index)
        increment = 10
        i = 1
        QgsMessageLog.logMessage(f'Starting feature creation: {task.description()}'
                                 ,MESSAGE_CATEGORY, Qgis.Info)
        #The features to the QGIS layer is created with a for loop
        #The attributes are set using a string of values from the objects_dataframe
        # Create concatenated strings of attributes
        ##str_objects = objects_dataframe.apply(
        ##    lambda x: x.astype(str).tolist(), axis=1).tolist()

        #Create QGS features and set attributes
        i = 1
        #for ob in str_objects:
        for index, row in objects_dataframe.iterrows():
            feature = QgsFeature()
            #newrow = ob
            feature.setFields(attribute_fields)
            progress = (progressbarlength*i) / total
            if int(progress) > increment:
                task.setProgress(int((progressbarlength*i)/total))
                increment += 10
            for column in objects_dataframe.columns:
                if pd.isna(row[column]):
                    feature.setAttribute(column, None)
                else:
                    feature.setAttribute(column, row[column])
            #feature.setAttributes(newrow)
            temp_data.addFeature(feature)
            i = i+1
            # Check if the task is cancelled
            if task.isCanceled():
                # Log a message and return None
                QgsMessageLog.logMessage(f'Task was canceled: {task.description()}'
                                         ,MESSAGE_CATEGORY, Qgis.Info)
                return None
        QgsMessageLog.logMessage(
            f'Commiting changes {task.description()}'
            ,MESSAGE_CATEGORY
            , Qgis.Info)
        temp.commitChanges()
        task.setProgress(100)
        QgsMessageLog.logMessage(f'Finished {task.description()}: {task.progress()}'
                                 ,MESSAGE_CATEGORY, Qgis.Info)
        #The layer (temp), group_name and temp_layername is returned
        #to on_finished=self.add_geo_layer
        return [temp, group_name, temp_layername]

    def add_non_geo_layer(self, exception, result:list[QgsVectorLayer,str,str]) -> None:
        """This is called when create_non_spatial_layer is finished.
        Exception is not None if create_non_spatial_layer raises an exception.
        result is the return value of create_non_spatial_layer
        The reason layers are added here is to avoid accessing objects that lives
        on the main thread from QgsTask which is not allowed."""

        if exception is None:
            if result is None:
                message_text = self.tr('''Completed with no exception and no result (probably manually canceled by the user)''')
                QgsMessageLog.logMessage(
                    message_text,
                    MESSAGE_CATEGORY, Qgis.Warning)
            else:
                #Layers are added to QGIS TOC
                layer=result[0]
                safechars = string.ascii_letters + string.digits + ".-_åäöÅÄÖ"
                defaultchar = '_'
                temp_layername = result[2]
                temp_layername = "".join(c if c in safechars
                                         else defaultchar
                                         for c in temp_layername)
                #print(temp_layername)
                group_name = result[1]
                root = QgsProject.instance().layerTreeRoot()
                current_group = root.findGroup(group_name)
                layer.setName(temp_layername)
                #It is very important to use addMapLayer! If not used QGIS will crash!
                QgsProject.instance().addMapLayer(layer, False)
                current_group.insertLayer(0, layer)
                Utils.expand_group(group_name)
                QgsMessageLog.logMessage(f'Finished adding non-spatial layer: {temp_layername}'
                    ,MESSAGE_CATEGORY, Qgis.Info)

        else:
            QgsMessageLog.logMessage(f"Exception: {exception}",
                                 MESSAGE_CATEGORY, Qgis.Critical)
            raise exception

    def create_spatial_layerOLD(self, task:QgsTask, objects:pd.DataFrame
                             , fields:list, group:str, layer_name:str) -> list[QgsVectorLayer,list,str,str]:
        '''Create layer(s) containing geometry object(s)'''
        QgsMessageLog.logMessage(f'Started task: {task.description()}'
                                 ,MESSAGE_CATEGORY, Qgis.Info)
        task.setProgress(1)
        objects_dataframe = objects
        fields_to_keep = fields
        #Create layer name
        temp_layername = layer_name

        #Create a memory layer without geometry
        temp = None
        temp = QgsVectorLayer("none","geo","memory")
        temp_data = None
        temp_data = temp.dataProvider()

        #Enter editing mode
        temp.startEditing()
        #Create attribute fields
        objects_dataframe_colnames = list(
            objects_dataframe.columns.values.tolist())
        attribute_datatypes = dict(zip(objects_dataframe_colnames
                                       ,[QVariant.String]*len(objects_dataframe_colnames)))
        #Set datatypes
        object_id_filter = list(objects_dataframe['object_id'])
        object_id_filter = str(object_id_filter).replace('[', '(').replace(']', ')')
        conn = sqlite3.connect(self.current_gpkg)
        conn.close()

        attributes_datatypes_dict = self.class_subclass_attributes.attributes_datatypes_dict.copy()

        if len(attributes_datatypes_dict) != 0:
            for attrib in attributes_datatypes_dict:
                #if attrib != None:
                if attrib is not None:
                    attributes_datatypes_dict[attrib] = Utils.get_qvariant_type_from_attribute_data_type(attributes_datatypes_dict[attrib])

        attribute_datatypes['IntrasisId'] = QVariant.Int
        attribute_datatypes['object_id'] = QVariant.Int
        attribute_datatypes['Name'] = QVariant.String
        attribute_datatypes['Class'] = QVariant.String
        attribute_datatypes['SubClass'] = QVariant.String
        attribute_datatypes['GeoObjectId'] = QVariant.Int
        attribute_datatypes['spatial_type'] = QVariant.String

        for attrib in attributes_datatypes_dict:
            try:
                attribute_datatypes[attrib] = attributes_datatypes_dict[attrib]
            except Exception as ex:
                QgsMessageLog.logMessage(f'Failed to set datatype of {attrib} from attributes.data_type defaulting to string {ex}'
                                         ,MESSAGE_CATEGORY, Qgis.Info)

        for col in objects_dataframe.columns:
            if attribute_datatypes[col] in [QVariant.Int]:
                try:
                    objects_dataframe[col] = pd.to_numeric(
                        objects_dataframe[col]
                        ,errors='ignore')
                except Exception as ex:
                    QgsMessageLog.logMessage(
                        f'Numeric conversion failed, attribute: {col} {ex}'
                        ,MESSAGE_CATEGORY
                        , Qgis.Info)
                try:
                    objects_dataframe.astype({col: 'Int64'}).dtypes
                    QgsMessageLog.logMessage(
                        f'Attribute {col} converted to Int64 NaN introduced'
                        ,MESSAGE_CATEGORY
                        , Qgis.Info)
                except Exception as ex:
                    QgsMessageLog.logMessage(
                        f'Numeric conversion failed{col} {ex} NaN introduced'
                        ,MESSAGE_CATEGORY
                        , Qgis.Info)

            if attribute_datatypes[col] in [QVariant.Double]:
                try:
                    objects_dataframe[col] = pd.to_numeric(
                        objects_dataframe[col]
                        ,errors='coerce')
                except Exception as ex:
                    QgsMessageLog.logMessage(f'Numeric conversion failed, attribute {col} {ex} NaN introduced'
                                             ,MESSAGE_CATEGORY, Qgis.Info)

            if attribute_datatypes[col] in [QVariant.Date]:
                try:
                    objects_dataframe[col] = pd.to_datetime(
                        objects_dataframe[col]
                        ,errors='coerce')
                except Exception as ex:
                    QgsMessageLog.logMessage(f'Date/time conversion failed, attribute {col} {ex} NaN introduced'
                                             ,MESSAGE_CATEGORY, Qgis.Info)

            if attribute_datatypes[col] in [QVariant.Bool]:
                try:
                    objects_dataframe[col] = objects_dataframe[col].astype(bool,errors='ignore')
                except Exception as ex:
                    QgsMessageLog.logMessage(f'Boolean conversion failed, attribute {col} {ex} NaN introduced'
                                             ,MESSAGE_CATEGORY, Qgis.Info)

        col_dict = dict(zip(objects_dataframe.columns
                            , objects_dataframe.dtypes.apply(lambda x: x.name)))

        type_map = {'Int64':QVariant.Int,'int64':QVariant.Int
                    ,'int32':QVariant.Int,'float64':QVariant.Double
                    ,'object':QVariant.String, 'bool':QVariant.Bool
                    , 'datetime64[ns]':QVariant.Date}
        attribute_fields = []
        objects_dataframe_colnames = list(objects_dataframe.columns.values.tolist())

        for col_name in objects_dataframe_colnames:
            field = QgsField(str(col_name), type_map[col_dict[col_name]])
            attribute_fields.append(field)
        temp_data.addAttributes(attribute_fields)
        temp.updateFields()

        #Fill attribute table with data
        progressbarlength = 100
        total = len(objects_dataframe.index)
        increment = 10
        i = 1

        QgsMessageLog.logMessage(
            f'Starting feature creation {task.description()}'
            ,MESSAGE_CATEGORY, Qgis.Info)

        #Create concatenated strings of attributes, 
        #Keep it outside of any for loop to improve performance!
        str_objects = objects_dataframe.apply(
            lambda x: x.astype(str).tolist(), axis=1).copy(deep=True).tolist()

        #Set attribute data
        i = 1
        for ob in str_objects:
            feature=QgsFeature()
            newrow = ob
            progress = (progressbarlength*i)/total
            if int(progress) > increment:
                task.setProgress(int((progressbarlength*i)/total))
                increment+=10
            feature.setAttributes(newrow)
            temp_data.addFeature(feature)
            i = i + 1
            if task.isCanceled():
                # Log a message and return None
                QgsMessageLog.logMessage(f'Task was canceled: {task.description()}'
                                         ,MESSAGE_CATEGORY, Qgis.Info)
                return None

        QgsMessageLog.logMessage(
            f'Commiting changes {task.description()}'
            ,MESSAGE_CATEGORY
            , Qgis.Info)
        temp.commitChanges()

        task.setProgress(100)
        return [temp, fields_to_keep, group, temp_layername]

    def create_spatial_layer(self, task:QgsTask, objects:pd.DataFrame
                             , fields:list, group:str, layer_name:str) -> list[QgsVectorLayer,list,str,str]:
        '''Create layer(s) containing geometry object(s)'''
        QgsMessageLog.logMessage(f'Started task: {task.description()}'
                                 ,MESSAGE_CATEGORY, Qgis.Info)
        task.setProgress(1)
        objects_dataframe = objects
        fields_to_keep = fields
        #Create layer name
        temp_layername = layer_name

        #Create a memory layer without geometry
        temp = None
        temp = QgsVectorLayer("none","geo","memory")
        temp_data = None
        temp_data = temp.dataProvider()

        #Enter editing mode
        temp.startEditing()
        #Create attribute fields
        objects_dataframe_colnames = list(
            objects_dataframe.columns.values.tolist())
        attribute_datatypes = dict(zip(objects_dataframe_colnames
                                       ,[QVariant.String]*len(objects_dataframe_colnames)))
        #Set datatypes
        object_id_filter = list(objects_dataframe['object_id'])
        object_id_filter = str(object_id_filter).replace('[', '(').replace(']', ')')
        conn = sqlite3.connect(self.current_gpkg)
        conn.close()

        attributes_datatypes_dict = self.class_subclass_attributes.attributes_datatypes_dict.copy()

        if len(attributes_datatypes_dict) != 0:
            for attrib in attributes_datatypes_dict:
                #if attrib != None:
                #if attrib is not None:
                #    attributes_datatypes_dict[attrib] = Utils.get_qvariant_type_from_attribute_data_type(attributes_datatypes_dict[attrib])
                if attrib == attrib:
                    if attrib is not None:
                        attributes_datatypes_dict[attrib] = Utils.get_qvariant_type_from_attribute_data_type(attributes_datatypes_dict[attrib])
                if attrib != attrib:
                    attributes_datatypes_dict[attrib] = QVariant.String
                if attrib is None:
                    attributes_datatypes_dict[attrib] = QVariant.String

        attribute_datatypes['IntrasisId'] = QVariant.Int
        attribute_datatypes['object_id'] = QVariant.Int
        attribute_datatypes['Name'] = QVariant.String
        attribute_datatypes['Class'] = QVariant.String
        attribute_datatypes['SubClass'] = QVariant.String
        attribute_datatypes['GeoObjectId'] = QVariant.Int
        attribute_datatypes['spatial_type'] = QVariant.String

        for attrib in attributes_datatypes_dict:
            try:
                attribute_datatypes[attrib] = attributes_datatypes_dict[attrib]
            except Exception as ex:
                QgsMessageLog.logMessage(f'Failed to set datatype of {attrib} from attributes.data_type defaulting to string {ex}'
                                         ,MESSAGE_CATEGORY, Qgis.Info)

        for col in objects_dataframe.columns:
            if attribute_datatypes[col] in [QVariant.Int]:
                try:
                    objects_dataframe[col] = pd.to_numeric(
                        objects_dataframe[col]
                        ,errors='ignore')
                except Exception as ex:
                    QgsMessageLog.logMessage(
                        f'Numeric conversion failed, attribute: {col} {ex}'
                        ,MESSAGE_CATEGORY
                        , Qgis.Info)
                try:
                    objects_dataframe.astype({col: 'Int64'}).dtypes
                    QgsMessageLog.logMessage(
                        f'Attribute {col} converted to Int64 NaN introduced'
                        ,MESSAGE_CATEGORY
                        , Qgis.Info)
                except Exception as ex:
                    QgsMessageLog.logMessage(
                        f'Numeric conversion failed{col} {ex} NaN introduced'
                        ,MESSAGE_CATEGORY
                        , Qgis.Info)

            if attribute_datatypes[col] in [QVariant.Double]:
                try:
                    objects_dataframe[col] = pd.to_numeric(
                        objects_dataframe[col]
                        ,errors='coerce')
                except Exception as ex:
                    QgsMessageLog.logMessage(f'Numeric conversion failed, attribute {col} {ex} NaN introduced'
                                             ,MESSAGE_CATEGORY, Qgis.Info)

            if attribute_datatypes[col] in [QVariant.Date]:
                try:
                    objects_dataframe[col] = pd.to_datetime(
                        objects_dataframe[col]
                        ,errors='coerce')
                except Exception as ex:
                    QgsMessageLog.logMessage(f'Date/time conversion failed, attribute {col} {ex} NaN introduced'
                                             ,MESSAGE_CATEGORY, Qgis.Info)

            if attribute_datatypes[col] in [QVariant.Bool]:
                try:
                    objects_dataframe[col] = objects_dataframe[col].astype(bool,errors='ignore')
                except Exception as ex:
                    QgsMessageLog.logMessage(f'Boolean conversion failed, attribute {col} {ex} NaN introduced'
                                             ,MESSAGE_CATEGORY, Qgis.Info)

        col_dict = dict(zip(objects_dataframe.columns
                            , objects_dataframe.dtypes.apply(lambda x: x.name)))

        type_map = {'Int64':QVariant.Int,'int64':QVariant.Int
                    ,'int32':QVariant.Int,'float64':QVariant.Double
                    ,'object':QVariant.String, 'bool':QVariant.Bool
                    , 'datetime64[ns]':QVariant.Date}
        #attribute_fields = []
        attribute_fields = QgsFields()
        objects_dataframe_colnames = list(objects_dataframe.columns.values.tolist())

        for col_name in objects_dataframe_colnames:
            field = QgsField(str(col_name), type_map[col_dict[col_name]])
            attribute_fields.append(field)
        temp_data.addAttributes(attribute_fields)
        temp.updateFields()

        #Fill attribute table with data
        progressbarlength = 100
        total = len(objects_dataframe.index)
        increment = 10
        i = 1

        QgsMessageLog.logMessage(
            f'Starting feature creation {task.description()}'
            ,MESSAGE_CATEGORY, Qgis.Info)

        #Create concatenated strings of attributes, 
        #Keep it outside of any for loop to improve performance!
        ##str_objects = objects_dataframe.apply(
        ##    lambda x: x.astype(str).tolist(), axis=1).copy(deep=True).tolist()

        #Set attribute data
        i = 1
        #for ob in str_objects:
        for index, row in objects_dataframe.iterrows():
            feature=QgsFeature()
            #newrow = ob
            feature.setFields(attribute_fields)
            progress = (progressbarlength*i)/total
            if int(progress) > increment:
                task.setProgress(int((progressbarlength*i)/total))
                increment+=10
            for column in objects_dataframe.columns:
                if pd.isna(row[column]):
                    feature.setAttribute(column, None)
                else:
                    feature.setAttribute(column, row[column])
            #feature.setAttributes(newrow)
            temp_data.addFeature(feature)
            i = i + 1
            if task.isCanceled():
                # Log a message and return None
                QgsMessageLog.logMessage(f'Task was canceled: {task.description()}'
                                         ,MESSAGE_CATEGORY, Qgis.Info)
                return None

        QgsMessageLog.logMessage(
            f'Commiting changes {task.description()}'
            ,MESSAGE_CATEGORY
            , Qgis.Info)
        temp.commitChanges()

        task.setProgress(100)
        return [temp, fields_to_keep, group, temp_layername]

    def add_geo_layer(self, exception, result:list[QgsVectorLayer,list,str,str]) -> None:
        """This is called when create_spatial_layer is finished.
        Exception is not None if create_spatial_layer raises an exception.
        result is the return value of create_spatial_layer
        The objects with geometries are joined with the geometry layers in the GPKG
        using QGIS processing funtions native:joinattributestable and native:retainfields"""

        if exception is None:
            if result is None:
                message_text = self.tr('Completed with no exception and no result (probably manually canceled by the user)')
                QgsMessageLog.logMessage(
                    message_text,
                    MESSAGE_CATEGORY, Qgis.Warning)
            else:
                created_layers=[]
                temp_layername=result[3]
                group_name=result[2]
                root = QgsProject.instance().layerTreeRoot()
                current_group = root.findGroup(group_name)
                fields_to_keep = result[1]
                fields_to_keep.remove('GeoObjectId')

                try:#Get layertype from Intrasis geopackage metadata
                    conn = sqlite3.connect(self.current_gpkg)
                    sql_query_string_feature_tables = """Select table_name from gpkg_contents where data_type = 'features' and table_name != 'project_information' """
                    types = pd.read_sql_query(sql_query_string_feature_tables, conn)
                    vector_layers_in_selected_gpgk = []
                    for layer_name in types['table_name']:
                        layer_source = self.current_gpkg+'|layername=' + layer_name
                        vector_layers_in_selected_gpgk.append(layer_source)
                    conn.close()

                    #Get rasterlayer
                    conn = sqlite3.connect(self.current_gpkg)
                    sql_query_string_raster_tables = """Select identifier from gpkg_contents where data_type = 'tiles'"""
                    #Note rember handle null result
                    raster_file_ids = pd.read_sql_query(sql_query_string_raster_tables, conn)
                    raster_layers_in_selected_gpgk = []
                    for layer_name in raster_file_ids['identifier']:
                        raster_layer_source = self.current_gpkg+'|layername=' + layer_name
                        raster_layers_in_selected_gpgk.append(raster_layer_source)
                    conn.close()
                    for geolay in vector_layers_in_selected_gpgk:

                        #Keep only GeoObjectId, remove all other attributes from geometry layer
                        try:
                            geometry_layer = processing.run(
                                "native:retainfields"
                                , {'INPUT':geolay
                                ,'FIELDS':['GeoObjectId']
                                ,'OUTPUT':'TEMPORARY_OUTPUT'})
                            #Add class subclass attributes to the geometry_layer
                            geom_layer_class_subclass_attribs = processing.run(
                                "native:joinattributestable"
                                , {'INPUT':geometry_layer['OUTPUT']
                                ,'FIELD':'GeoObjectId'
                                ,'INPUT_2':result[0]
                                ,'FIELD_2':'GeoObjectId'
                                ,'FIELDS_TO_COPY':[]
                                ,'METHOD':0,'DISCARD_NONMATCHING':True
                                ,'PREFIX':''
                                ,'OUTPUT':'TEMPORARY_OUTPUT'})

                        except Exception as ex:
                            print(self.tr(f"something went wrong: {ex}, perhaps Invalid join fields?"))
                        try:
                            if geom_layer_class_subclass_attribs['OUTPUT'].featureCount() > 0:
                                geom_layer_class_subclass_attribs = processing.run(
                                    "native:retainfields"
                                    , {'INPUT':geom_layer_class_subclass_attribs['OUTPUT']
                                    ,'FIELDS':fields_to_keep
                                    ,'OUTPUT':'TEMPORARY_OUTPUT'})
                                safechars = string.ascii_letters + string.digits + ".-_åäöÅÄÖ"
                                defaultchar = '_'
                                layername = temp_layername+ '.'+geolay.split('=')[-1]
                                layername = "".join(c if c in safechars
                                         else defaultchar
                                         for c in layername)
                                geom_layer_class_subclass_attribs['OUTPUT'].setName(layername)
                                #It is very important to use addMapLayer! If not used QGIS will crash!
                                QgsProject.instance().addMapLayer(geom_layer_class_subclass_attribs['OUTPUT'], False)
                                current_group.insertLayer(0, geom_layer_class_subclass_attribs['OUTPUT'])
                                created_layers.append(layername)
                        except Exception as ex:
                            print(self.tr(f"could not create layer {ex}"))

                except Exception as ex:
                    print(self.tr('Could not write (all) features')+f'{ex}')
                Utils.expand_group(group_name)
            QgsMessageLog.logMessage(
                f'Finished adding geo-layers {created_layers} into group: {result[3]}'
                ,MESSAGE_CATEGORY
                , Qgis.Info)

        else:
            QgsMessageLog.logMessage(f"Exception: {exception}",
                                 MESSAGE_CATEGORY, Qgis.Critical)
            raise exception

    def start_task_load_table(self) -> None:
        '''Starts task of loading Class/SubClass data'''
        self.pushButton_read_to_table.setEnabled(False)
        globals()['Task_load_table'] = QgsTask.fromFunction(
            'Load table'
            , self.read_class_subclass_attributes
            , on_finished=self.completed_load_table)
        QgsApplication.taskManager().addTask(globals()['Task_load_table'])

    def completed_load_table(self, exception, result=None):
        """This is called when self.read_class_subclass_attributes is finished.
        Exception is not None if self.read_class_subclass_attributes raises an exception.
        result is the return value of self.read_class_subclass_attributes."""
        if exception is None:
            if result is None:
                message_text = self.tr('Completed with no exception and no result (probably manually canceled by the user)')
                QgsMessageLog.logMessage(
                    message_text,
                    MESSAGE_CATEGORY, Qgis.Warning)
            else:
                self.update_number_of_rows_label(self.class_subclass_attributes.get_loaded_rows_info_data_frame())
                self.pb_open_parent_id_dialog.setEnabled(True)
                QgsMessageLog.logMessage(f'Completed task: {result["Read Class Subclass Attributes "]}'
                                         ,MESSAGE_CATEGORY,Qgis.Info)

        else:
            QgsMessageLog.logMessage(f"Exception: {exception}"
                                 ,MESSAGE_CATEGORY, Qgis.Critical)
            raise exception

    def update_number_of_rows_label(self, loaded_rows_info_data_frame:pd.DataFrame) -> None:
        '''Update the QTable widget with number of loaded objects in class subclass browser'''
        total_objects = loaded_rows_info_data_frame['Total loaded objects'].iloc[0]
        objects_with_geometry = loaded_rows_info_data_frame['Objects with Geometry'].iloc[0]
        objects_without_geometry = loaded_rows_info_data_frame['Objects without Geometry'].iloc[0]

        rows_string = self.tr("rows") if total_objects > 1 else self.tr("row")
        with_geometry_string = self.tr("with geometry")
        without_geometry_string = self.tr("without geometry")
        label_text = f"{total_objects} {rows_string} ({objects_with_geometry} {with_geometry_string}, {objects_without_geometry} {without_geometry_string})"

        self.label_num_loaded_objects_info.setText(label_text)

    def read_class_subclass_attributes(self, task:QgsTask) -> dict:
        '''Create object that hold attributes of 
        class and subclass as a QGS Task'''

        self.class_subclass_attributes = populateTableFromGpkg(
           self.tableView_class_browser
           ,self.comboBox_class.currentText()
           ,self.comboBox_subclass.currentText()
           ,self.current_gpkg
           ,subclass_items_dict = self.subclass_items_dict)

        self.class_subclass_attributes.populate_table(task)
        self.class_subclass_attributes.update_qtablewidget(task)

        self.enable_load_to_map()
        self.enable_export_as_chart()
        return {'Read Class Subclass Attributes ': task.description()}

    def create_layer_task(self, task:QgsTask) -> dict:
        '''Create and load QGIS Layers as a QGS Task'''
        self.load_to_qgis_layer()
        self.enable_load_to_map()
        return {'Create QGIS Layers': task.description()}

    def update_combobox_class(self) -> None:
        '''Update and changes Class(es) in combobox'''
        self.comboBox_class.clear()
        class_items = self.archeological_classes[1]
        class_items.insert(0,'-')
        self.comboBox_class.addItems(class_items)

    def update_combobox_subclass(self) -> None:
        '''Update and changes SubClass(es) in combobox'''
        self.comboBox_subclass.clear()
        self.pushButton_read_to_table.setEnabled(False)
        self.pb_open_parent_id_dialog.setEnabled(False)
        self.pushButton_load_to_map.setEnabled(False)
        self.pushButton_export_as_chart.setEnabled(False)
        if len(self.comboBox_class.currentText()) > 0:
            class_current = self.comboBox_class.currentText()

            class_subclass_items = self.archeological_classes[0]

            if class_current != '-':
                subclasses = [item for item in class_subclass_items if class_current in item][0][1]
                if subclasses is None or subclasses == 'NULL':
                    self.comboBox_subclass.addItems(
                        [self.subclass_items_dict['All Objects']
                        ,self.subclass_items_dict['No SubClass']])
                else:
                    subclasses_items = subclasses.split('|')
                    subclasses_items.insert(0,self.subclass_items_dict['All Objects'])
                    #Add "Every SubClass" on if subclasses exists
                    if len(subclasses_items) > 2:
                        subclasses_items.insert(1,self.subclass_items_dict['Every SubClass'])
                    #Move 'No Subclass upwards in combobox'
                    if self.subclass_items_dict['No SubClass'] in subclasses_items:
                        oldindex = subclasses_items.index(
                            self.subclass_items_dict['No SubClass'])
                        subclasses_items.insert(2, subclasses_items.pop(oldindex))
                    self.comboBox_subclass.addItems(subclasses_items)

    def enable_button_read_to_table(self) -> None:
        '''Enables read to table button depending on chosen combobox values'''
        if self.comboBox_class.currentText() == '-':
            self.pushButton_read_to_table.setEnabled(False)
            self.pb_open_parent_id_dialog.setEnabled(False)
            self.pushButton_load_to_map.setEnabled(False)
            self.pushButton_export_as_chart.setEnabled(False)
        if self.comboBox_class.currentText() != '-':
            self.pushButton_read_to_table.setEnabled(True)
            self.pb_open_parent_id_dialog.setEnabled(False)
            self.pushButton_load_to_map.setEnabled(False)
            self.pushButton_export_as_chart.setEnabled(False)

    def enable_load_to_map(self) -> None:
        '''Enable load to map button'''
        self.pushButton_load_to_map.setEnabled(True)

    def disable_load_to_map(self) -> None:
        '''Disable load to map button'''
        self.pushButton_load_to_map.setEnabled(False)

    def enable_export_as_chart(self) -> None:
        '''Enable export as chart button'''
        self.pushButton_export_as_chart.setEnabled(True)

    def export_as_chart(self) -> None:
        '''Exports Class SubClass table as a chart CSV or Excel'''
        settings = QgsSettings()
        self.export_folder = settings.value("IntrasisClassSubClassBrowser/exportFolder", "")
        options = QtWidgets.QFileDialog.Options()
        fileName_suggestion = self.current_gpkg.split('/')[-1]
        fileName_suggestion = fileName_suggestion.split('.')[0]
        fileName_suggestion = (fileName_suggestion
                               +'.'+self.comboBox_class.currentText()
                               +'.'+self.comboBox_subclass.currentText()
                               +'.csv')
        fileName_suggestion = "".join(ch for ch in fileName_suggestion if (ch.isalnum() or ch in ".-_ "))
        fileName_suggestion = os.path.join(self.export_folder, fileName_suggestion)

        save_file_dialog_text = self.tr("Intrasis Analysis Class/SubClass Browser, Save File")
        save_file_type_text = self.tr("Text Files (*.csv);;Excel xlsx (*.xlsx)")
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,save_file_dialog_text,fileName_suggestion
            ,save_file_type_text, options=options)

        if fileName:
            file_dir = os.path.dirname(fileName)
            if os.path.exists(file_dir) is True:
                settings = QgsSettings()
                settings.setValue("IntrasisClassSubClassBrowser/exportFolder", file_dir)
            self.class_subclass_attributes.save_chart(fileName,fileName_suggestion)

class populateTableFromGpkg:
    """Class representing class subclass attribute table"""

    def __init__(self, tableView, class_item, subclass_item
                , selected_gpkg, subclass_items_dict): #, add_parent_id_to_layer):
        '''Holds functions and creates Class Subclass object'''
        self.tableV = tableView
        self.class_item = class_item
        self.subclass_item = subclass_item
        self.selected_gpkg = selected_gpkg
        self.error_dialog = QtWidgets.QErrorMessage()
        self.subclass_items_dict = subclass_items_dict
        self.objects_dataframe = None
        self.attributes_datatypes_dict = []
        self.nRows = None
        self.nCols = None
        self.temp_layername = None
        self.objects_dataframe_relations = None

    def populate_table(self,task:QgsTask) -> None:
        '''Reads and arranges data to be viewed in
          class subclass browser and to create QGIS layers'''
        QgsMessageLog.logMessage(f'Started task {task.description()}'
                                 ,MESSAGE_CATEGORY, Qgis.Info)
        task.setProgress(1)
        self.temp_layername = (self.class_item+
                          '.'+self.subclass_item)
        conn = sqlite3.connect(self.selected_gpkg)

        #########################################################################
        sql_query_string_step1_object_id_class = 'SELECT object_id, class FROM objects WHERE Class IN (\''+ self.class_item + '\') AND SubClass IN (\''+ self.subclass_item + '\')'
        #########################################################################

        sql_query_string_object_ids = '(SELECT object_id FROM objects WHERE Class IN (\''+ self.class_item + '\') AND SubClass IN (\''+ self.subclass_item + '\') )'

        sql_query_string_common_attribute_units = 'select attribute_label, attribute_unit from ( SELECT  objects.Class, SubClass, attribute_label, attribute_unit, count(*) as num_of_occurences FROM objects LEFT JOIN attributes on objects.object_id = attributes.object_id where objects.Class IN (\''+ self.class_item + '\') AND SubClass IN (\''+ self.subclass_item + '\') group by attribute_label, attribute_unit order by objects.Class )temp where attribute_unit != \'\' and temp.num_of_occurences = (Select MAX(num_of_occurences) as max_number_of_occurences FROM( SELECT  objects.Class, SubClass, attribute_label, attribute_unit, count(*) as num_of_occurences FROM objects LEFT JOIN attributes on objects.object_id = attributes.object_id where objects.Class IN (\''+ self.class_item + '\') AND SubClass IN (\''+ self.subclass_item + '\') group by attribute_label, attribute_unit order by objects.Class))'
        if self.subclass_item == self.subclass_items_dict['Every SubClass']:
            sql_query_string_common_attribute_units = 'select attribute_label, attribute_unit from ( SELECT  objects.Class, SubClass, attribute_label, attribute_unit, count(*) as num_of_occurences FROM objects LEFT JOIN attributes on objects.object_id = attributes.object_id where objects.Class IN (\''+ self.class_item + '\') AND SubClass IS NOT NULL group by attribute_label, attribute_unit order by objects.Class )temp where attribute_unit != \'\' and temp.num_of_occurences = (Select MAX(num_of_occurences) as max_number_of_occurences FROM( SELECT  objects.Class, SubClass, attribute_label, attribute_unit, count(*) as num_of_occurences FROM objects LEFT JOIN attributes on objects.object_id = attributes.object_id where objects.Class IN (\''+ self.class_item + '\') AND SubClass IS NOT NULL group by attribute_label, attribute_unit order by objects.Class))'
        if self.subclass_item == self.subclass_items_dict['No SubClass']:
            sql_query_string_common_attribute_units = 'select attribute_label, attribute_unit from ( SELECT  objects.Class, SubClass, attribute_label, attribute_unit, count(*) as num_of_occurences FROM objects LEFT JOIN attributes on objects.object_id = attributes.object_id where objects.Class IN (\''+ self.class_item + '\') AND SubClass IS NULL group by attribute_label, attribute_unit order by objects.Class )temp where attribute_unit != \'\' and temp.num_of_occurences = (Select MAX(num_of_occurences) as max_number_of_occurences FROM( SELECT  objects.Class, SubClass, attribute_label, attribute_unit, count(*) as num_of_occurences FROM objects LEFT JOIN attributes on objects.object_id = attributes.object_id where objects.Class IN (\''+ self.class_item + '\') AND SubClass IS NULL group by attribute_label, attribute_unit order by objects.Class))'
        if self.subclass_item == self.subclass_items_dict['All Objects']:
            sql_query_string_common_attribute_units = 'select attribute_label, attribute_unit from ( SELECT  objects.Class, SubClass, attribute_label, attribute_unit, count(*) as num_of_occurences FROM objects LEFT JOIN attributes on objects.object_id = attributes.object_id where objects.Class IN (\''+ self.class_item + '\')  group by attribute_label, attribute_unit order by objects.Class )temp where attribute_unit != \'\' and temp.num_of_occurences >= (Select count(*) FROM objects where objects.Class IN (\''+ self.class_item + '\'))'

        common_units_dataframe = pd.read_sql_query(sql_query_string_common_attribute_units, conn)

        if common_units_dataframe.empty is not True:
            common_attribute_units_string = '\',\''.join(common_units_dataframe['attribute_unit'].astype(str))

        if self.subclass_item == self.subclass_items_dict['All Objects']:

            ##########################################################
            sql_query_string_step1_object_id_class = 'SELECT object_id, class FROM objects WHERE class IN (\''+ self.class_item + '\')'
            sql_query_string_object_ids = '(SELECT object_id FROM objects WHERE Class IN (\''+ self.class_item + '\') )'

        if self.subclass_item == self.subclass_items_dict['Every SubClass']:

            #######################################################################
            sql_query_string_step1_object_id_class = 'SELECT object_id, class FROM objects WHERE Class IN (\''+ self.class_item + '\') AND SubClass IS NOT NULL'
            sql_query_string_object_ids = '(SELECT object_id FROM objects WHERE Class IN (\''+ self.class_item + '\') AND SubClass IS NOT NULL)'

        if self.subclass_item == self.subclass_items_dict['No SubClass']:

            #######################################################################
            sql_query_string_object_id_and_attribute_data = 'select distinct object_id, attribute_value, attribute_unit,case when attribute_count>1 then attribute_label_numbered else attribute_label end attribute_label, data_type from(select attribute_id, attribute_unit, attribute_value,object_id, attribute_label, data_type, row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_count,attribute_label||\'_\'||row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_label_numbered from attributes where object_id IN (SELECT object_id FROM objects WHERE Class IN (\''+ self.class_item + '\') AND SubClass IS NULL  ))'
            sql_query_string_step1_object_id_class = 'SELECT object_id, class FROM objects WHERE Class IN (\''+ self.class_item + '\') AND SubClass IS NULL'
            #########################################################################
            sql_query_string_object_ids = '(SELECT object_id FROM objects WHERE Class IN (\''+ self.class_item + '\') AND SubClass IS NULL )'

        sql_query_string_num_attributes = 'select count(attribute_id) as antal_attribut_id from attributes where object_id IN' +sql_query_string_object_ids
        number_of_attributes = pd.read_sql_query(sql_query_string_num_attributes, conn)

        if number_of_attributes['antal_attribut_id'].iloc[0] == 0:
            self.objects_dataframe = pd.read_sql_query('select object_id FROM objects where object_id IN' +sql_query_string_object_ids, conn)
            self.attributes_datatypes_dict = []
        if number_of_attributes['antal_attribut_id'].iloc[0] > 0:

            #print(sql_query_string_step1_object_id_class)
            objects_dataframe = pd.read_sql_query(sql_query_string_step1_object_id_class, conn)
            object_id_filter = list(objects_dataframe['object_id'])
            object_id_filter = str(object_id_filter).replace('[', '(').replace(']', ')')
            Query_2 = f"SELECT class as klass, attribute_id, attribute_unit, attribute_value, object_id, attribute_label, data_type, CASE WHEN attribute_count > 1 THEN attribute_label_numbered ELSE attribute_label END AS attribute_label_final FROM (SELECT class, attribute_id, attribute_unit, attribute_value, object_id, attribute_label, data_type,ROW_NUMBER() OVER (PARTITION BY object_id, attribute_label ORDER BY attribute_id) AS attribute_count,attribute_label || '_' || ROW_NUMBER() OVER (PARTITION BY object_id, attribute_label ORDER BY attribute_id) AS attribute_label_numbered FROM attributes WHERE object_id IN {object_id_filter} ) AS A"
            #print(f"Query_2: {Query_2}")
            objects_dataframe2 = pd.read_sql_query(Query_2, conn)
            result = objects_dataframe2.groupby('attribute_label_final')['attribute_label_final'].count()
            #common_class_attributes = objects_dataframe2.query('klass == 1')['attribute_label_final'].copy().drop_duplicates()
            common_class_attributes = objects_dataframe2['attribute_label_final'].copy().drop_duplicates()
            common_attributes = list(set(common_class_attributes))
            #common_class_attributes = objects_dataframe2.query('klass == 1')['attribute_label_final'].copy().drop_duplicates()
            '''a=pd.DataFrame(result)
            a['namn']=list(a.index.values.tolist())
            print(f"a: {a}")
            mostcommon = a['attribute_label_final'].max()
            print(f"mostcommon: {mostcommon}")
            mostcommon = a['attribute_label_final'].value_counts().idxmax()
            print(f"mostcommon: {mostcommon}")
            common_attributes = a.query('attribute_label_final == @mostcommon')['namn']
            #common_attributes = a.query('attribute_label_final > 1')['namn']
            common_attributes = list(common_attributes)
            common_class_attributes = list(common_class_attributes)
            print(f"common_class_attributes: {common_class_attributes}")
            common_attributes = list(set(common_attributes+common_class_attributes))
            print(f"common_attributes: {common_attributes} ")'''
            subclass_attributes = objects_dataframe2.query('klass == 0')['attribute_label_final'].copy().drop_duplicates()
            subclass_attributes = list(set(subclass_attributes))
            #print(subclass_attributes)
            #common_attributes = list(set(common_class_attributes+subclass_attributes))
            #common_attributes = list(set(common_class_attributes))
            b = objects_dataframe.set_index('object_id').join(objects_dataframe2.set_index('object_id'))
            if self.subclass_item == self.subclass_items_dict['All Objects']:
                common_class_attributes = objects_dataframe2.query('klass == 1')['attribute_label_final'].copy().drop_duplicates()
                common_attributes = list(set(common_class_attributes))
                #b = b.query('attribute_label_final in @common_attributes').copy()
            if self.subclass_item == self.subclass_items_dict['Every SubClass']:
                common_class_attributes = objects_dataframe2.query('klass == 1')['attribute_label_final'].copy().drop_duplicates()
                common_attributes = list(set(common_class_attributes))
                #b = b.query('attribute_label_final in @common_attributes').copy()
            if self.subclass_item == self.subclass_items_dict['No SubClass']:
                common_class_attributes = objects_dataframe2.query('klass == 1')['attribute_label_final'].copy().drop_duplicates()
                common_attributes = list(set(common_class_attributes))
                #b = b.query('attribute_label_final in @common_attributes').copy()
            #print(f"subclass_attributes: {subclass_attributes}")
            #print(f"common_attributes: {common_attributes}")
            #print(f"len(b.index): {len(b.index)}")
            #####b = b.query('attribute_label_final in @common_attributes').copy()
            b['object_id']=list(b.index.values.tolist())
            #print(b.columns)
            #print(b)
            self.objects_dataframe = b[['object_id', 'attribute_value', 'attribute_unit', 'attribute_label_final', 'data_type']].copy()
            #print(len(self.objects_dataframe.index))
            self.objects_dataframe = self.objects_dataframe.rename(columns={'attribute_label_final': 'attribute_label'})
            #################################################################
            attrib = list(self.objects_dataframe ['attribute_label'])
            #print(f"attrib: {attrib}")
            attrib_dtype = list(self.objects_dataframe ['data_type'])
            self.attributes_datatypes_dict = dict(zip(attrib,attrib_dtype))
            self.objects_dataframe.loc[self.objects_dataframe['data_type'].isin(['Decimal']),'attribute_value'] = self.objects_dataframe.loc[self.objects_dataframe['data_type'].isin(['Decimal']),'attribute_value'].str.replace(',','.')
            
            


        task.setProgress(20)
        if number_of_attributes['antal_attribut_id'].iloc[0] > 0:
            sql_query_string_attribute_order = 'select group_concat(test||enhetskolumn, \'|\') as attribute_order from( select distinct case when attribute_count>1 then attribute_label_numbered else attribute_label end test, case when attribute_unit !=\'\' AND attribute_count>1  then \'|\'||attribute_label_numbered||\' (enhet)\' when attribute_unit !=\'\' then \'|\'||attribute_label ||\' (enhet)\' else \'\' end enhetskolumn from( select attribute_id, attribute_unit, attribute_value,object_id, attribute_label, row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_count,attribute_label||\'_\'||row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_label_numbered from attributes where object_id IN '+sql_query_string_object_ids+') AS attribute_order order by attribute_id)'
            #print(sql_query_string_attribute_order)
            attribute_label_order = pd.read_sql_query(sql_query_string_attribute_order, conn)
            if attribute_label_order.isnull().values.any() is not True :
                attribute_label_order = attribute_label_order['attribute_order'].values.tolist() #.toString().split('|')
                attribute_label_order = attribute_label_order[0].split('|')
            elif attribute_label_order.isnull().values.any() :
                attribute_label_order = []

            sql_query_string_object_id_and_attribute_data = 'SELECT object_id, attribute_id, attribute_unit FROM attributes WHERE object_id IN (SELECT object_id FROM objects WHERE Class IN (\''+ self.class_item + '\') AND SubClass IN (\''+ self.subclass_item + '\') )'

            if self.subclass_item == self.subclass_items_dict['All Objects']:
                sql_query_string_object_id_and_attribute_data = 'SELECT object_id, attribute_id, attribute_unit FROM attributes WHERE object_id IN (SELECT object_id FROM objects WHERE Class IN (\''+ self.class_item + '\') )'
                sql_query_string_subclass = 'SELECT object_id FROM objects WHERE Class IN (\''+ self.class_item + '\') '
                attribute_subclass_dataframe = pd.read_sql_query(sql_query_string_subclass, conn)
                attribute_subclass_dataframe = attribute_subclass_dataframe.set_index('object_id')
                #print(len(attribute_subclass_dataframe.index))

            if self.subclass_item == self.subclass_items_dict['Every SubClass']:

                sql_query_string_object_id_and_attribute_data = 'SELECT object_id, attribute_id, attribute_unit FROM attributes WHERE object_id IN (SELECT object_id FROM objects WHERE Class IN (\''+ self.class_item + '\') AND SubClass IS NOT NULL )'

                sql_query_string_subclass = 'SELECT object_id FROM objects WHERE Class IN (\''+ self.class_item + '\') AND SubClass IS NOT NULL'

                attribute_subclass_dataframe = pd.read_sql_query(sql_query_string_subclass, conn)
                attribute_subclass_dataframe = attribute_subclass_dataframe.set_index('object_id')

            if self.subclass_item == self.subclass_items_dict['No SubClass']:

                sql_query_string_object_id_and_attribute_data = 'SELECT object_id, attribute_id, attribute_unit FROM attributes WHERE object_id IN (SELECT object_id FROM objects WHERE Class IN (\''+ self.class_item + '\') AND SubClass IS NULL )'
                sql_query_string_subclass = 'SELECT object_id FROM objects WHERE Class IN (\''+ self.class_item + '\')'
                attribute_subclass_dataframe = pd.read_sql_query(sql_query_string_subclass, conn)
                attribute_subclass_dataframe = attribute_subclass_dataframe.set_index('object_id')

            attribute_unit_dataframe = pd.read_sql_query(sql_query_string_object_id_and_attribute_data, conn)
            #print(f"sql_query_string_object_id_and_attribute_data: {sql_query_string_object_id_and_attribute_data}")

            attribute_unit_dataframe = attribute_unit_dataframe.set_index(['object_id'])

            sql_query_string_enhetskolumn = 'select object_id, case when attribute_count>1 then attribute_label_numbered else attribute_label end attribute_label, case when attribute_unit !=\'\' AND attribute_count>1 then attribute_label_numbered||\' (enhet)\' else attribute_label ||\' (enhet)\' end enhetskolumn ,attribute_unit from( select attribute_id, attribute_unit, attribute_value,object_id, attribute_label, row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_count,attribute_label||\'_\'||row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_label_numbered from attributes where object_id IN'+sql_query_string_object_ids+') AS attribute_enhet where attribute_unit !=\'\''

            if not common_units_dataframe.empty:
                sql_query_string_enhetskolumn = 'select object_id, case when attribute_count>1 then attribute_label_numbered else attribute_label end attribute_label, case when attribute_unit !=\'\' AND attribute_count>1 then attribute_label_numbered||\' (enhet)\' else attribute_label ||\' (enhet)\' end enhetskolumn ,attribute_unit from( select attribute_id, attribute_unit, attribute_value,object_id, attribute_label, row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_count,attribute_label||\'_\'||row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_label_numbered from attributes where object_id IN'+sql_query_string_object_ids+') AS attribute_enhet where attribute_unit !=\'\' and attribute_unit IN (\''+common_attribute_units_string+'\')'

            attribute_enhetskolumn_dataframe = pd.read_sql_query(sql_query_string_enhetskolumn, conn)
            conn.close()

            #Pivot attribute data
            if common_units_dataframe.empty is True:
                self.objects_dataframe = self.objects_dataframe.pivot(index=['object_id'], columns='attribute_label', values='attribute_value')

            if not common_units_dataframe.empty:
                try:
                    self.objects_dataframe = self.objects_dataframe.pivot(index=['object_id'], columns='attribute_label', values='attribute_value')
                    attribute_enhetskolumn_dataframe = attribute_enhetskolumn_dataframe.pivot(index=['object_id'], columns='enhetskolumn', values='attribute_unit')

                except Exception as ex:
                    QgsMessageLog.logMessage(f'{ex}'
                                 ,MESSAGE_CATEGORY, Qgis.Info)
                    self.objects_dataframe.reset_index(inplace=True)
                    attribute_unit_dataframe.reset_index(inplace=True)
                    attribute_unit_dataframe = attribute_unit_dataframe.set_index(['object_id','attribute_id'])
                    self.objects_dataframe = self.objects_dataframe.pivot(index=['object_id'], columns='attribute_label', values='attribute_value')

            #print(len(self.objects_dataframe.index))
            self.objects_dataframe = self.objects_dataframe.join(attribute_unit_dataframe, how='left')
            #print(len(self.objects_dataframe.index))

            if self.subclass_item == self.subclass_items_dict['Every SubClass']:
                self.objects_dataframe = self.objects_dataframe.join(attribute_subclass_dataframe, how='left')

            if self.subclass_item == self.subclass_items_dict['All Objects']:
                #print(len(self.objects_dataframe.index))
                self.objects_dataframe = self.objects_dataframe.join(attribute_subclass_dataframe, how='left')
                self.objects_dataframe.drop(columns=subclass_attributes, inplace=True)
                #print(len(self.objects_dataframe.index))

        #Join Class and Subclass
        if number_of_attributes['antal_attribut_id'].iloc[0] > 0:
            self.objects_dataframe['object_id'] = self.objects_dataframe.index
            conn = sqlite3.connect(self.selected_gpkg)
            class_subclass_dataframe = pd.read_sql_query('select object_id, IntrasisId, Name, Class, SubClass from objects', conn)

            class_subclass_dataframe = class_subclass_dataframe.set_index(['object_id'])
            conn.close()

            self.objects_dataframe = self.objects_dataframe.join(class_subclass_dataframe, how='left')
            #if common_units_dataframe.empty != True:
            if not common_units_dataframe.empty:
                self.objects_dataframe = self.objects_dataframe.join(attribute_enhetskolumn_dataframe, how='left')

        if number_of_attributes['antal_attribut_id'].iloc[0] == 0:
            #print('Koppla på class subclass, antal attribut == 0')
            conn = sqlite3.connect(self.selected_gpkg)
            self.objects_dataframe = pd.read_sql_query('select object_id, IntrasisId, Name, Class, SubClass from objects where attributes IS NULL AND object_id IN' +sql_query_string_object_ids, conn)
            conn.close()

        #Test if objects exists without attribute a
        conn = sqlite3.connect(self.selected_gpkg)
        sql_query_count_null_attributes = 'select count(*) as num_of_objects_with_null_attributes from(select distinct attributes from objects where object_id IN' +sql_query_string_object_ids+' group by attributes, SubClass, Class) where attributes is null'

        count_attribute_null_dataframe = pd.read_sql_query(sql_query_count_null_attributes, conn)

        sql_query_count_subclasses = 'select count(*) as num_of_SubClasses from(select distinct SubClass from objects where object_id IN' +sql_query_string_object_ids+' group by Class, SubClass)'

        count_subclasses_dataframe = pd.read_sql_query(sql_query_count_subclasses, conn)

        if count_attribute_null_dataframe['num_of_objects_with_null_attributes'].iloc[0] > 0 and count_subclasses_dataframe['num_of_SubClasses'].iloc[0] > 0:
            objects_with_null_attributes_dataframe = pd.read_sql_query('select object_id, IntrasisId, Name, Class, SubClass from objects where attributes IS NULL AND object_id IN' +sql_query_string_object_ids, conn)
            self.objects_dataframe = pd.concat([self.objects_dataframe, objects_with_null_attributes_dataframe], ignore_index=True, sort=False)
        self.objects_dataframe = self.objects_dataframe.drop_duplicates()
        conn.close()

        #Arrange columns ("attributes") in correct order
        objects_dataframe_colnames = list(self.objects_dataframe.columns.values.tolist())
        #print(f"objects_dataframe_colnames: {objects_dataframe_colnames}")
        if number_of_attributes['antal_attribut_id'].iloc[0] == 0:
            attribute_label_order = []
        attribute_label_order.insert(0,'IntrasisId')
        attribute_label_order.insert(1,'object_id')
        attribute_label_order.insert(2,'Name')
        attribute_label_order.insert(3,'Class')
        attribute_label_order.insert(4,'SubClass')

        attribute_label_order = [x for x in attribute_label_order if x in objects_dataframe_colnames]
        self.objects_dataframe = self.objects_dataframe[attribute_label_order].copy(deep=True)
        self.objects_dataframe = self.objects_dataframe.drop_duplicates().copy(deep=True)
        self.objects_dataframe = self.objects_dataframe.fillna('').copy(deep=True)
        self.nRows = len(self.objects_dataframe.index)
        self.nCols = len(self.objects_dataframe.columns)
        #print(f"attribute_label_order: {attribute_label_order}")

        task.setProgress(100)
        return

    def create_temp_layer(self, fileName_suggestion:str) -> QgsVectorLayer:
        '''Create a temporary layer so that QGIS layer methods can be used
          to save to excel chart (xlsx)'''

        temp_layer_name = fileName_suggestion[0:30]
        temp_layer = QgsVectorLayer("none",temp_layer_name,"memory")
        temp_data = temp_layer.dataProvider()
        temp_layer.startEditing()

        attribute_fields = []
        for head in self.objects_dataframe:

            if self.objects_dataframe[head].dtype == 'int64':
                myField = QgsField( head, QVariant.Int )
            else:
                myField = QgsField( head, QVariant.String )
            attribute_fields.append(myField)
            temp_data.addAttributes(attribute_fields)
            temp_layer.updateFields()

        #Remove numpy nan fill with empty space so that chart files look nice
        self.objects_dataframe = self.objects_dataframe.fillna('')

        headers=[col for col in self.objects_dataframe.columns]
        objects_dataframe_to_excel = self.objects_dataframe[headers].copy()
        objects_dataframe_to_excel['concat_sep'] = objects_dataframe_to_excel.apply(lambda x: x.astype(str).tolist(), axis=1)
        for i in range(len(self.objects_dataframe.index)):
            feature=QgsFeature()
            newrow = objects_dataframe_to_excel['concat_sep'].iloc[i]
            feature.setAttributes(newrow)
            temp_data.addFeature(feature)

        return temp_layer

    def save_chart(self, filepath, fileName_suggestion:str) -> None:
        '''Exports/saves the class subclass browser data as a chart CSV or Excel'''
        #Get filetype
        selected_file_type = filepath.split('.')[-1]
        if selected_file_type=='csv':
            try:
                result = self.objects_dataframe.to_csv(filepath, index=False, encoding='utf-8')
                if result is None:
                    QgsMessageLog.logMessage(f'Wrote file to: {filepath}'
                                             ,MESSAGE_CATEGORY, Qgis.Info)
            except BaseException as err:
                print(f'Something went wrong, could not save file: {err}')
                QgsMessageLog.logMessage(f"Exception from Class Subclass Browser Exception: {err}", MESSAGE_CATEGORY, Qgis.Info)
                return

        if selected_file_type=='xlsx':
            try:
                options = QgsVectorFileWriter.SaveVectorOptions()
                options.driverName = "XLSX"
                options.fileEncoding = "utf-8"
                options.layerOptions = ["GEOMETRY=AS_XYZ"]
                options.layerName = ".".join(fileName_suggestion.split (".", -1) [1:-1])[:31]# fileName_suggestion.split('.')[1]
                options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
                layer_to_export = self.create_temp_layer(fileName_suggestion)
                result, error_string, error_string2, error_string3 = QgsVectorFileWriter.writeAsVectorFormatV3(layer_to_export,filepath,QgsProject.instance().transformContext(),options)
                if result == QgsVectorFileWriter.NoError:
                    QgsMessageLog.logMessage(f'Wrote file to: {filepath}'
                                             ,MESSAGE_CATEGORY, Qgis.Info)
                if result != QgsVectorFileWriter.NoError:
                    QgsMessageLog.logMessage(error_string,MESSAGE_CATEGORY, Qgis.Info)
                    QgsMessageLog.logMessage(error_string2,MESSAGE_CATEGORY, Qgis.Info)
                    QgsMessageLog.logMessage(error_string3,MESSAGE_CATEGORY, Qgis.Info)

            except BaseException as err:
                print(f'Something went wrong, could not save file: {err}')
                QgsMessageLog.logMessage(f"Exception from Class Subclass Browser Exception: {err}", MESSAGE_CATEGORY, Qgis.Info)
                return

    def clear_qtablewidget(self) -> None:
        '''Clears data from class subclass browser'''
        #table_data = pd.DataFrame(data={'': []})
        table_data = pd.DataFrame()
        self.tableV.setModel(TableModel(table_data=table_data))

    def update_qtablewidget(self, task:QgsTask) -> pd.DataFrame:
        '''Update class subclass browser with data'''
        table_data = self.objects_dataframe.copy()
        task.setProgress(int(50))
        kolumnHeader = list(self.objects_dataframe.columns.values)
        table_data = table_data[kolumnHeader].fillna('')
        task.setProgress(int(75))
        table_data.reset_index(drop=True, inplace=True)
        table_data.set_index('object_id')
        self.tableV.setModel(TableModel(table_data=table_data))

        task.setProgress(int(100))
        QgsMessageLog.logMessage(f'Finished: {task.description()} {task.progress()}'.format(),MESSAGE_CATEGORY, Qgis.Info)
        return self.objects_dataframe
    
    def get_loaded_rows_info_data_frame(self):
        '''Update the QTable widget with number of loaded objects in class subclass browser'''
        object_id_list = list(self.objects_dataframe['object_id'])
        object_ids = str(object_id_list).replace('[', '').replace(']', '')
        
        sql = Utils.load_resource('sql/browse_tables_select_number_of_object.sql')
        sql = sql.replace("__OBJECT_ID__", f"{object_ids}")
        conn = sqlite3.connect(self.selected_gpkg)
        table_loaded_data_stats = pd.read_sql_query(sql, conn)
        conn.close()

        return table_loaded_data_stats

    '''def get_parent_id_string(self, gpkg:str, object_id:int) -> (str | None | None):
        parent_object_id_list = BrowseRelationsUtils.get_realated_above(
                    gpkg, object_id)
                #print(parent_object_id_list)
        parent_object_id_string = ''
        if len(parent_object_id_list) > 0:
            parent_intrasis_id_list = [Utils.get_objects_data_for_object_id(MESSAGE_CATEGORY
                                                     , gpkg
                                                     , int(item))["IntrasisId"].tolist()
                                                     for item in parent_object_id_list[:,0]]
                    #print(parent_intrasis_id_list)
            parent_id_string = ','.join([str(item)
                                                       for sublist in
                                                       parent_intrasis_id_list
                                                       for item in sublist])
            parent_object_id_string = list(parent_object_id_list[:,0])
            parent_object_id_string = ','.join(map(str, parent_object_id_string))
            #print(parent_object_id_string)
            
            if len(parent_id_string) > 0:
                return parent_intrasis_id_list, parent_id_string, parent_object_id_list, parent_object_id_string
            if len(parent_id_string) == 0:
                parent_id_string = ''
                parent_object_id_string = ''
                return parent_intrasis_id_list, parent_id_string, parent_object_id_list, parent_object_id_string
        else:
            parent_intrasis_id_list = []
            parent_id_string = ''
            parent_object_id_string = ''
            return parent_intrasis_id_list, parent_id_string, parent_object_id_list, parent_object_id_string'''

    '''def get_parent_id_string_string(self, gpkg:str, object_id:int) -> (str | None | None):
        parent_object_id_list = BrowseRelationsUtils.get_realated_above(
                    gpkg, object_id)
                #print(parent_object_id_list)
        parent_object_id_string = ''
        if len(parent_object_id_list) > 0:
            parent_intrasis_id_list = [Utils.get_objects_data_for_object_id(MESSAGE_CATEGORY
                                                     , gpkg
                                                     , int(item))["IntrasisId"].tolist()
                                                     for item in parent_object_id_list[:,0]]
                    #print(parent_intrasis_id_list)
            parent_id_string = ','.join([str(item)
                                                       for sublist in
                                                       parent_intrasis_id_list
                                                       for item in sublist])
            parent_object_id_string = list(parent_object_id_list[:,0])
            parent_object_id_string = ','.join(map(str, parent_object_id_string))
            #print(parent_object_id_string)
            
            if len(parent_id_string) > 0:
                #return parent_intrasis_id_list, parent_id_string, parent_object_id_list, parent_object_id_string
                return parent_id_string
            if len(parent_id_string) == 0:
                parent_id_string = ''
                parent_object_id_string = ''
                #return parent_intrasis_id_list, parent_id_string, parent_object_id_list, parent_object_id_string
                return parent_id_string
        else:
            parent_intrasis_id_list = []
            parent_id_string = ''
            parent_object_id_string = ''
            #return parent_intrasis_id_list, parent_id_string, parent_object_id_list, parent_object_id_string
            return parent_id_string'''

    '''def get_related_classes_and_subclasses(self, gpkg,  object_id_string):
        ''''''Returns a Pandas dataframe containing related class and subclass combinations''''''
        sql_query = f"select Class, SubClass, REPLACE(Class, ' ', '_') || '.' || REPLACE(Subclass, ' ', '_') AS 'Class.SubClass', count() as count from objects where IntrasisId in ({object_id_string}) group by Class, SubClass"
        print(sql_query)
        conn = sqlite3.connect(gpkg)
        related_classes_subclasses = pd.read_sql_query(sql_query, conn)
        #class_subclass_dataframe = class_subclass_dataframe.set_index(['object_id'])
        conn.close()
        return related_classes_subclasses'''

class TableModel(QAbstractTableModel):
    """Class representing QAbstractTableModel"""

    def __init__(self, table_data, parent=None):
        super().__init__(parent)
        self.table_data = table_data

    def rowCount(self, parent: QModelIndex) -> int:
        """Returns number of rows of data table"""
        return self.table_data.shape[0]

    def columnCount(self, parent: QModelIndex) -> int:
        """Returns number of columns of data table"""
        return self.table_data.shape[1]

    def data(self, index: QModelIndex, role: int = ...) -> typing.Any:
        """Returns table data row as a string"""
        if role == Qt.DisplayRole:
            return str(self.table_data.iloc[index.row()][index.column()])

    def headerData(self, section: int, orientation: Qt.Orientation
                   , role: int = ...) -> typing.Any:
        """Returns table data header"""
        if not self.table_data.empty:
            if orientation == Qt.Horizontal and role == Qt.DisplayRole:
                return str(self.table_data.columns[section])

    def sort(self, column, order):
        # Sortera DataFrame baserat på kolumn och ordning
        column_name = self.table_data.columns[column]
        self.table_data = self.table_data.sort_values(by=column_name, ascending=(order == Qt.AscendingOrder))
        self.layoutChanged.emit()  # Meddela vyn att datamodellen har ändrats

class TableModelParenID(QAbstractTableModel):
    """Class representing QAbstractTableModel"""

    def __init__(self, table_data, parent=None):
        super().__init__(parent)
        self.table_data = table_data

    def rowCount(self, parent: QModelIndex) -> int:
        """Returns number of rows of data table"""
        return self.table_data.shape[0]

    def columnCount(self, parent: QModelIndex) -> int:
        """Returns number of columns of data table"""
        return self.table_data.shape[1]

    def data(self, index: QModelIndex, role: int = ...) -> typing.Any:
        """Returns table data row as a string"""
        if role == Qt.DisplayRole:
            return str(self.table_data.iloc[index.row()][index.column()])

    def headerData(self, section: int, orientation: Qt.Orientation
                   , role: int = ...) -> typing.Any:
        """Returns table data header"""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return str(self.table_data.columns[section])
        
    def sort(self, column, order):
        # Sortera DataFrame baserat på kolumn och ordning
        column_name = self.table_data.columns[column]
        self.table_data = self.table_data.sort_values(by=column_name, ascending=(order == Qt.AscendingOrder))
        self.layoutChanged.emit()  # Meddela vyn att datamodellen har ändrats
