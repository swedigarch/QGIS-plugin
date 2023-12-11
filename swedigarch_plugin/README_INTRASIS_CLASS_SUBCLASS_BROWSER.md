# Intrasis Class/Subclass Browser plugin

"The Intrasis Class/Subclass Browser is a QGIS plugin that can browse the attributes of archaeological classes and subclasses of an Intrasis GeoPackage. The plugin can be used to create QGIS map layers and attribute tables based on the combobox settings of archaeological Class and Subclass. Besides creating QGIS map layers, the attribute table of the browser can be saved as an Excel (.XLSX) and comma-separated file (.CSV) as well.

The main window of Intrasis Class/Subclass Browser is a QDialog where the attributes of archaeological classes and subclasses are displayed. The dialog consists of combo boxes which are used to select archaeological class and subclass, a QTableWidget for displaying the attribute table, and a set of buttons “Load table”, “Create layer”, “Save as …”, “Help and Close”."

### Code Structure

The files related to Class SubClass browser are
- intrasis_analysis_browse_tables.py
- intrasis_analysis_browse_class_subclass.ui
- utils&period;py
- select_geo_package_dalog.py
- help_dialog.py
- help_dialog.ui

The Python files were edited using Visual Studio Code. The UI-files were edited with Qt Designer, which is included as a part of the standard QGIS installation. It is recommended to use Qt Designer to edit the UI-files. The code can be edited with any code editor.

### intrasis_analysis_browse_tables.py Classes
#### Class IntrasisAnalysisBrowseTablesDialog  
Prepares variables  
Sets titles and names  
Contains pushbutton logics of the interface

#### Class populateTableFromGpkg
Initiates a populateTableFromGpkg object with methods 'clear_qtablewidget', 'create_temp_layer', 'populate_table', 'save_chart', 'update_qtablewidget'

#### Class TableModel(QAbstractTableModel)
Used to create a table model to the be displayed as a QTableWidget

### Overall Functional description of the plugin
The plugin loads an Intrasis Geopackage from the QgsProject.instance(). At least one geopackage must be loaded in the QGIS project. If more than one geopackage is present the user must choose only one. When the plugin dialog opens the function update_combobox_class and update_combobox_subclass fills the combo box list with the archeological Classes and Subclasses. When an archeological Class is selected the Subclass combo box is updated and preselected with “All objects” and the Load Table button becomes activated.

When the load table button is pushed, a populateTableFromGpkg object is created. Data to the objects is loaded by Sqlite3 queries executed against the chosen Intrasis Geopackage. Within the code, there are several different Sqlite3 queries, which sqlite3 query is run is determined by the chosen class and subclass. The Sqlite3 queries are dynamically adapted to the settings. Examples of Sqlite3 queries are found in the end of this document under section “Sqlite3 queries in Intrasis Class/Subclass Browser plugin.  

#### Work flow when load table button is pushed 
-  Start: Read the comboboxes of Class and SubClass 
 ---> pick correct SQL queries and adapt them dynamically ---> fetch and store query result as a Pandas Dataframe ---> transpose result from long format to wide format to represent an attribute table ---> 
- End: Display the attribute table in the browser

After the table is finished loading, the buttons "Create Layer" and "Save Table As..." become activated.

#### Work flow when Create Layer button is pushed
-  Start: Get  
 ---> determine which objects has/has no geometry ---> fetch geometries ---> create layer without geometries (if applicable) ---> create geometry layer(s) ---> 
- End: add the created layers to the QGIS table of contents "TOC"

Note: Data is transposed from long format to wide format, to improve readability and to work as a QGIS attribute table. To transform data from Long format to Wide format, the row id must be unique or the transform will fail. The transform is based on the object_id, attribute_label and attribute_value. This requires that attribute_label is unique. However, an Intrasis attributes table allows non-unique attribute_labels. Therefore, an object can have several rows with identical attribute_labels. This is handled by giving a suffix to the attribute label. The method is illustrated below by using Class “Ruta” as an example. The first attribute label becomes “rutstorlek” and subsequent “rutstorlek”-labels are assigned a suffix based on a numerical sequence starting at 2: rutstorlek, rutstorlek_2, rutstorlek_3, rutstorlek_4.

#### Attribute values are stored in "attributes" in an Intrasis Geopackage as "Long format"
|attribute_id|object_id|attribute_label|attribute_value|attribute_unit|class|data_type|
|---|:---:|:---:|:---:|:---:|:---:|---:|
|62|13547|Rutstorlek|1|m|1|Decimal|
|63|13547|Rutstorlek|1|m|1|Decimal|
|64|13547|Rutstorlek|1|m|0|Decimal|
|65|13547|Rutstorlek|1|m|0|Decimal|

#### Attributes are displayed in Wide format in class browser (with some more attributes that is added by the browser)
|IntrasisId|object_id|Name|Class|SubClass|X|Y|Typ|Rutstorlek|Rutstorlek (enhet)|Rutstorlek_2|Rutstorlek_2 (enhet)|Rutstorlek_3|Rutstorlek_3 (enhet)|Rutstorlek_4|Rutstorlek_4 (enhet)|Beskrivning|spatial_type|
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---:|
|8652|13547|X= 6704032.5 Y= 1588767.5|Ruta|Ruta 0,5x0,5|6704032.5|1588767.5|1|nan|m|nan|m|nan|m|nan|m|1|Polygon|

#### Preventing QGIS user interface becoming unresponsive
A computantional intensive process can make QGIS user interface becoming unresponsive until the process is finished. To prevent this 

```python
QgsTask from function 
```

is used when loading a class subclass table to the browser and when creating map layers.  

```python
QgsTask.fromFunction('Create_spatial_layer_task')
```
is added to 
```python
QgsApplication.taskManager().addTask()
```
It is important to note, that the QgsTask should not interact with any objects of the QGIS main thread. Interaction will result in unexpected behavior and crashes. After the task is finished, the result of the task is added to the main thread of QGIS.

#### Workflow of a QgsTask, QgsTask.fromFunction
-  Start: create a QgsTask
  ---> do the processing, (i.e. Load Table) -> when finished ---> Handle the result (i.e. display attributes) 
- End: Display the attribute table in the browser


## SQL-queries that are generated
Depending on chosen class subclass different SQL-queries are generated. The queries are partly hard coded and partly dynamically generated.

#### Example of typical class subclass browser SQL-queries
There is mainly three selections that can be chosen in the class subclass browser
Archeologial Class paired with either, "All Objects", "All SubClasses", "No SubClass", and SubClass.
For instance if the Archeological Class is "Fynd" the possible selections become:
Class ComboBox: "Fynd", SubClass ComboBox: "All Objects"
Class ComboBox: "Fynd", SubClass ComboBox: "All SubClasses"
Class ComboBox: "Fynd", SubClass ComboBox: "No SubClass"
Class ComboBox: "Fynd", SubClass ComboBox: "Kakel" (which is an archeological subclass)

## Below are documented the resulting SQL-queries that result from the four different selections above:

An example of the basic structure of a SQL query (for all other SQL queries see the source code).

```python
sql_query_string_step1_object_id_class = 'SELECT object_id, class FROM objects WHERE Class IN (\''+ self.class_item + '\') AND SubClass IN (\''+ self.subclass_item + '\')'
```

Below are the dynamically adpated SQL queries as they are run. 
#### Class ComboBox: "Fynd", SubClass ComboBox: "All Objects" -------------------------------------------------------------
sql_query_string_step1_object_id_class: 
```sql
 SELECT object_id, class FROM objects WHERE Class IN ('Fynd') AND SubClass IN ('All Objects')
```
sql_query_string_object_ids: 
```sql
 (SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IN ('All Objects') )
```
sql_query_string_common_attribute_units: 
```sql
 select attribute_label, attribute_unit from ( SELECT  objects.Class, SubClass, attribute_label, attribute_unit, count(*) as num_of_occurences FROM objects LEFT JOIN attributes on objects.object_id = attributes.object_id where objects.Class IN ('Fynd') AND SubClass IN ('All Objects') group by attribute_label, attribute_unit order by objects.Class )temp where attribute_unit != '' and temp.num_of_occurences = (Select MAX(num_of_occurences) as max_number_of_occurences FROM( SELECT  objects.Class, SubClass, attribute_label, attribute_unit, count(*) as num_of_occurences FROM objects LEFT JOIN attributes on objects.object_id = attributes.object_id where objects.Class IN ('Fynd') AND SubClass IN ('All Objects') group by attribute_label, attribute_unit order by objects.Class))
```
sql_query_string_common_attribute_units:
```sql
 select attribute_label, attribute_unit from ( SELECT  objects.Class, SubClass, attribute_label, attribute_unit, count(*) as num_of_occurences FROM objects LEFT JOIN attributes on objects.object_id = attributes.object_id where objects.Class IN ('Fynd')  group by attribute_label, attribute_unit order by objects.Class )temp where attribute_unit != '' and temp.num_of_occurences >= (Select count(*) FROM objects where objects.Class IN ('Fynd'))
```
sql_query_string_step1_object_id_class: 
```sql
SELECT object_id, class FROM objects WHERE class IN ('Fynd')
```
sql_query_string_object_ids: 
```sql
(SELECT object_id FROM objects WHERE Class IN ('Fynd') )
```
sql_query_string_num_attributes: 
```sql
select count(attribute_id) as antal_attribut_id from attributes where object_id IN(SELECT object_id FROM objects WHERE Class IN ('Fynd') )
```
sql_query_string_attribute_order: 
```sql
select group_concat(test||enhetskolumn, '|') as attribute_order from( select distinct case when attribute_count>1 then attribute_label_numbered else attribute_label end test, case when attribute_unit !='' AND attribute_count>1  then '|'||attribute_label_numbered||' (enhet)' when attribute_unit !='' then '|'||attribute_label ||' (enhet)' else '' end enhetskolumn from( select attribute_id, attribute_unit, attribute_value,object_id, attribute_label, row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_count,attribute_label||'_'||row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_label_numbered from attributes where object_id IN (SELECT object_id FROM objects WHERE Class IN ('Fynd') )) AS attribute_order order by attribute_id)
```
sql_query_string_object_id_and_attribute_data: 
```sql
SELECT object_id, attribute_id, attribute_unit FROM attributes WHERE object_id IN (SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IN ('All Objects') )
```
sql_query_string_object_id_and_attribute_data: 
```sql
SELECT object_id, attribute_id, attribute_unit FROM attributes WHERE object_id IN (SELECT object_id FROM objects WHERE Class IN ('Fynd') )
```
sql_query_string_subclass: 
```sql
SELECT object_id FROM objects WHERE Class IN ('Fynd') 
```
sql_query_string_enhetskolumn: 
```sql
select object_id, case when attribute_count>1 then attribute_label_numbered else attribute_label end attribute_label, case when attribute_unit !='' AND attribute_count>1 then attribute_label_numbered||' (enhet)' else attribute_label ||' (enhet)' end enhetskolumn ,attribute_unit from( select attribute_id, attribute_unit, attribute_value,object_id, attribute_label, row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_count,attribute_label||'_'||row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_label_numbered from attributes where object_id IN(SELECT object_id FROM objects WHERE Class IN ('Fynd') )) AS attribute_enhet where attribute_unit !=''
```
sql_query_string_enhetskolumn: 
```sql
select object_id, case when attribute_count>1 then attribute_label_numbered else attribute_label end attribute_label, case when attribute_unit !='' AND attribute_count>1 then attribute_label_numbered||' (enhet)' else attribute_label ||' (enhet)' end enhetskolumn ,attribute_unit from( select attribute_id, attribute_unit, attribute_value,object_id, attribute_label, row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_count,attribute_label||'_'||row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_label_numbered from attributes where object_id IN(SELECT object_id FROM objects WHERE Class IN ('Fynd') )) AS attribute_enhet where attribute_unit !='' and attribute_unit IN ('mm','mm','mm','mm','gram')
```
sql_query_count_null_attributes: 
```sql
select count(*) as num_of_objects_with_null_attributes from(select distinct attributes from objects where object_id IN(SELECT object_id FROM objects WHERE Class IN ('Fynd') ) group by attributes, SubClass, Class) where attributes is null
```
sql_query_count_subclasses: 
```sql
select count(*) as num_of_SubClasses from(select distinct SubClass from objects where object_id IN(SELECT object_id FROM objects WHERE Class IN ('Fynd') ) group by Class, SubClass)
```
 
#### Class ComboBox: "Fynd", SubClass ComboBox: "All SubClasses"-------------------------------------------------------------
sql_query_string_step1_object_id_class: 
```sql
SELECT object_id, class FROM objects WHERE Class IN ('Fynd') AND SubClass IN ('All SubClasses')
```
sql_query_string_object_ids: 
```sql
(SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IN ('All SubClasses') )
```
sql_query_string_common_attribute_units: 
```sql
select attribute_label, attribute_unit from ( SELECT  objects.Class, SubClass, attribute_label, attribute_unit, count(*) as num_of_occurences FROM objects LEFT JOIN attributes on objects.object_id = attributes.object_id where objects.Class IN ('Fynd') AND SubClass IN ('All SubClasses') group by attribute_label, attribute_unit order by objects.Class )temp where attribute_unit != '' and temp.num_of_occurences = (Select MAX(num_of_occurences) as max_number_of_occurences FROM( SELECT  objects.Class, SubClass, attribute_label, attribute_unit, count(*) as num_of_occurences FROM objects LEFT JOIN attributes on objects.object_id = attributes.object_id where objects.Class IN ('Fynd') AND SubClass IN ('All SubClasses') group by attribute_label, attribute_unit order by objects.Class))
```
sql_query_string_common_attribute_units: 
```sql
select attribute_label, attribute_unit from ( SELECT  objects.Class, SubClass, attribute_label, attribute_unit, count(*) as num_of_occurences FROM objects LEFT JOIN attributes on objects.object_id = attributes.object_id where objects.Class IN ('Fynd') AND SubClass IS NOT NULL group by attribute_label, attribute_unit order by objects.Class )temp where attribute_unit != '' and temp.num_of_occurences = (Select MAX(num_of_occurences) as max_number_of_occurences FROM( SELECT  objects.Class, SubClass, attribute_label, attribute_unit, count(*) as num_of_occurences FROM objects LEFT JOIN attributes on objects.object_id = attributes.object_id where objects.Class IN ('Fynd') AND SubClass IS NOT NULL group by attribute_label, attribute_unit order by objects.Class))
```
sql_query_string_step1_object_id_class: 
```sql
SELECT object_id, class FROM objects WHERE Class IN ('Fynd') AND SubClass IS NOT NULL
```
sql_query_string_object_ids: 
```sql
(SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IS NOT NULL)
```
sql_query_string_num_attributes: 
```sql
select count(attribute_id) as antal_attribut_id from attributes where object_id IN(SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IS NOT NULL)
```
sql_query_string_attribute_order: 
```sql
select group_concat(test||enhetskolumn, '|') as attribute_order from( select distinct case when attribute_count>1 then attribute_label_numbered else attribute_label end test, case when attribute_unit !='' AND attribute_count>1  then '|'||attribute_label_numbered||' (enhet)' when attribute_unit !='' then '|'||attribute_label ||' (enhet)' else '' end enhetskolumn from( select attribute_id, attribute_unit, attribute_value,object_id, attribute_label, row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_count,attribute_label||'_'||row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_label_numbered from attributes where object_id IN (SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IS NOT NULL)) AS attribute_order order by attribute_id)
```
sql_query_string_object_id_and_attribute_data: 
```sql
SELECT object_id, attribute_id, attribute_unit FROM attributes WHERE object_id IN (SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IN ('All SubClasses') )
```
sql_query_string_object_id_and_attribute_data: 
```sql
SELECT object_id, attribute_id, attribute_unit FROM attributes WHERE object_id IN (SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IS NOT NULL )
```
sql_query_string_subclass: 
```sql
SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IS NOT NULL
```
sql_query_string_enhetskolumn: 
```sql
select object_id, case when attribute_count>1 then attribute_label_numbered else attribute_label end attribute_label, case when attribute_unit !='' AND attribute_count>1 then attribute_label_numbered||' (enhet)' else attribute_label ||' (enhet)' end enhetskolumn ,attribute_unit from( select attribute_id, attribute_unit, attribute_value,object_id, attribute_label, row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_count,attribute_label||'_'||row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_label_numbered from attributes where object_id IN(SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IS NOT NULL)) AS attribute_enhet where attribute_unit !=''
```
sql_query_count_null_attributes: 
```sql
select count(*) as num_of_objects_with_null_attributes from(select distinct attributes from objects where object_id IN(SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IS NOT NULL) group by attributes, SubClass, Class) where attributes is null
```
sql_query_count_subclasses: 
```sql
select count(*) as num_of_SubClasses from(select distinct SubClass from objects where object_id IN(SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IS NOT NULL) group by Class, SubClass)
```

#### Class ComboBox: "Fynd", SubClass ComboBox: "No SubClass"------------------------------------------------------------- 
sql_query_string_step1_object_id_class: 
```sql
SELECT object_id, class FROM objects WHERE Class IN ('Fynd') AND SubClass IN ('No SubClass')
```
sql_query_string_object_ids: 
```sql
(SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IN ('No SubClass') )
```
sql_query_string_common_attribute_units: 
```sql
select attribute_label, attribute_unit from ( SELECT  objects.Class, SubClass, attribute_label, attribute_unit, count(*) as num_of_occurences FROM objects LEFT JOIN attributes on objects.object_id = attributes.object_id where objects.Class IN ('Fynd') AND SubClass IN ('No SubClass') group by attribute_label, attribute_unit order by objects.Class )temp where attribute_unit != '' and temp.num_of_occurences = (Select MAX(num_of_occurences) as max_number_of_occurences FROM( SELECT  objects.Class, SubClass, attribute_label, attribute_unit, count(*) as num_of_occurences FROM objects LEFT JOIN attributes on objects.object_id = attributes.object_id where objects.Class IN ('Fynd') AND SubClass IN ('No SubClass') group by attribute_label, attribute_unit order by objects.Class))
```
sql_query_string_common_attribute_units: 
```sql
select attribute_label, attribute_unit from ( SELECT  objects.Class, SubClass, attribute_label, attribute_unit, count(*) as num_of_occurences FROM objects LEFT JOIN attributes on objects.object_id = attributes.object_id where objects.Class IN ('Fynd') AND SubClass IS NULL group by attribute_label, attribute_unit order by objects.Class )temp where attribute_unit != '' and temp.num_of_occurences = (Select MAX(num_of_occurences) as max_number_of_occurences FROM( SELECT  objects.Class, SubClass, attribute_label, attribute_unit, count(*) as num_of_occurences FROM objects LEFT JOIN attributes on objects.object_id = attributes.object_id where objects.Class IN ('Fynd') AND SubClass IS NULL group by attribute_label, attribute_unit order by objects.Class))
```
sql_query_string_object_id_and_attribute_data: 
```sql
select distinct object_id, attribute_value, attribute_unit,case when attribute_count>1 then attribute_label_numbered else attribute_label end attribute_label, data_type from(select attribute_id, attribute_unit, attribute_value,object_id, attribute_label, data_type, row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_count,attribute_label||'_'||row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_label_numbered from attributes where object_id IN (SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IS NULL  ))
```
sql_query_string_step1_object_id_class: 
```sql
SELECT object_id, class FROM objects WHERE Class IN ('Fynd') AND SubClass IS NULL
```
sql_query_string_object_ids: 
```sql(SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IS NULL )
```
sql_query_string_num_attributes: 
```sql
select count(attribute_id) as antal_attribut_id from attributes where object_id IN(SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IS NULL )
```
sql_query_string_attribute_order: 
```sql
select group_concat(test||enhetskolumn, '|') as attribute_order from( select distinct case when attribute_count>1 then attribute_label_numbered else attribute_label end test, case when attribute_unit !='' AND attribute_count>1  then '|'||attribute_label_numbered||' (enhet)' when attribute_unit !='' then '|'||attribute_label ||' (enhet)' else '' end enhetskolumn from( select attribute_id, attribute_unit, attribute_value,object_id, attribute_label, row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_count,attribute_label||'_'||row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_label_numbered from attributes where object_id IN (SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IS NULL )) AS attribute_order order by attribute_id)
```
sql_query_string_object_id_and_attribute_data: 
```sql
SELECT object_id, attribute_id, attribute_unit FROM attributes WHERE object_id IN (SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IN ('No SubClass') )
```
sql_query_string_object_id_and_attribute_data: 
```sql
SELECT object_id, attribute_id, attribute_unit FROM attributes WHERE object_id IN (SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IS NULL )
```
sql_query_string_subclass: 
```sql
SELECT object_id FROM objects WHERE Class IN ('Fynd')
```
sql_query_string_enhetskolumn: 
```sql
select object_id, case when attribute_count>1 then attribute_label_numbered else attribute_label end attribute_label, case when attribute_unit !='' AND attribute_count>1 then attribute_label_numbered||' (enhet)' else attribute_label ||' (enhet)' end enhetskolumn ,attribute_unit from( select attribute_id, attribute_unit, attribute_value,object_id, attribute_label, row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_count,attribute_label||'_'||row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_label_numbered from attributes where object_id IN(SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IS NULL )) AS attribute_enhet where attribute_unit !=''
```
sql_query_string_enhetskolumn: 
```sql
select object_id, case when attribute_count>1 then attribute_label_numbered else attribute_label end attribute_label, case when attribute_unit !='' AND attribute_count>1 then attribute_label_numbered||' (enhet)' else attribute_label ||' (enhet)' end enhetskolumn ,attribute_unit from( select attribute_id, attribute_unit, attribute_value,object_id, attribute_label, row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_count,attribute_label||'_'||row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_label_numbered from attributes where object_id IN(SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IS NULL )) AS attribute_enhet where attribute_unit !='' and attribute_unit IN ('mm','mm','mm','mm','gram')
```
sql_query_count_null_attributes: 
```sql
select count(*) as num_of_objects_with_null_attributes from(select distinct attributes from objects where object_id IN(SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IS NULL ) group by attributes, SubClass, Class) where attributes is null
```
sql_query_count_subclasses: 
```sql
select count(*) as num_of_SubClasses from(select distinct SubClass from objects where object_id IN(SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IS NULL ) group by Class, SubClass)
```
#### Class ComboBox: "Fynd", SubClass ComboBox: "Kakel" -------------------------------------------------------------
sql_query_string_step1_object_id_class: 
```sql
SELECT object_id, class FROM objects WHERE Class IN ('Fynd') AND SubClass IN ('Kakel')
```
sql_query_string_object_ids: 
```sql
(SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IN ('Kakel') )
```
sql_query_string_common_attribute_units: 
```sql
select attribute_label, attribute_unit from ( SELECT  objects.Class, SubClass, attribute_label, attribute_unit, count(*) as num_of_occurences FROM objects LEFT JOIN attributes on objects.object_id = attributes.object_id where objects.Class IN ('Fynd') AND SubClass IN ('Kakel') group by attribute_label, attribute_unit order by objects.Class )temp where attribute_unit != '' and temp.num_of_occurences = (Select MAX(num_of_occurences) as max_number_of_occurences FROM( SELECT  objects.Class, SubClass, attribute_label, attribute_unit, count(*) as num_of_occurences FROM objects LEFT JOIN attributes on objects.object_id = attributes.object_id where objects.Class IN ('Fynd') AND SubClass IN ('Kakel') group by attribute_label, attribute_unit order by objects.Class))
```
sql_query_string_num_attributes: 
```sqlselect count(attribute_id) as antal_attribut_id from attributes where object_id IN(SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IN ('Kakel') )
```
sql_query_string_attribute_order: 
```sql
select group_concat(test||enhetskolumn, '|') as attribute_order from( select distinct case when attribute_count>1 then attribute_label_numbered else attribute_label end test, case when attribute_unit !='' AND attribute_count>1  then '|'||attribute_label_numbered||' (enhet)' when attribute_unit !='' then '|'||attribute_label ||' (enhet)' else '' end enhetskolumn from( select attribute_id, attribute_unit, attribute_value,object_id, attribute_label, row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_count,attribute_label||'_'||row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_label_numbered from attributes where object_id IN (SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IN ('Kakel') )) AS attribute_order order by attribute_id)
```
sql_query_string_object_id_and_attribute_data: 
```sql
SELECT object_id, attribute_id, attribute_unit FROM attributes WHERE object_id IN (SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IN ('Kakel') )
```
sql_query_string_enhetskolumn: 
```sql
select object_id, case when attribute_count>1 then attribute_label_numbered else attribute_label end attribute_label, case when attribute_unit !='' AND attribute_count>1 then attribute_label_numbered||' (enhet)' else attribute_label ||' (enhet)' end enhetskolumn ,attribute_unit from( select attribute_id, attribute_unit, attribute_value,object_id, attribute_label, row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_count,attribute_label||'_'||row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_label_numbered from attributes where object_id IN(SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IN ('Kakel') )) AS attribute_enhet where attribute_unit !=''
```
sql_query_string_enhetskolumn: 
```sql
select object_id, case when attribute_count>1 then attribute_label_numbered else attribute_label end attribute_label, case when attribute_unit !='' AND attribute_count>1 then attribute_label_numbered||' (enhet)' else attribute_label ||' (enhet)' end enhetskolumn ,attribute_unit from( select attribute_id, attribute_unit, attribute_value,object_id, attribute_label, row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_count,attribute_label||'_'||row_number() OVER(partition BY object_id,attribute_label order by attribute_id) as attribute_label_numbered from attributes where object_id IN(SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IN ('Kakel') )) AS attribute_enhet where attribute_unit !='' and attribute_unit IN ('mm','mm','mm','mm','gram')
```
sql_query_count_null_attributes: 
```sql
select count(*) as num_of_objects_with_null_attributes from(select distinct attributes from objects where object_id IN(SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IN ('Kakel') ) group by attributes, SubClass, Class) where attributes is null
```
sql_query_count_subclasses: 
```sql
select count(*) as num_of_SubClasses from(select distinct SubClass from objects where object_id IN(SELECT object_id FROM objects WHERE Class IN ('Fynd') AND SubClass IN ('Kakel') ) group by Class, SubClass)
```