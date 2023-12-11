# Introduction

This plugin can export from Intrasis databases to GeoPackage and optionally allow to CSV.
Export is done from the "Intrasis DB Manger" dialog.
This dialog have a top part for selecting/connecting to the PostgreSQL server to export databases from.
Then we have the part to select the databases to export, with one top list and one bottom list.
The top list holds the available databases found on the connected server.
The bottom list holds the databases selected for export. Databases are moved between the lists by double clicking on a database,
or by using the buttons between the lists.

On the bottom of the export dialog we have the folder to export selected databases to.
And two checkboxes that that control if we overwrite existing GeoPackages and if CSV exports is wanted.

If a valid selection and export catalog has been selected the "_Run export_" button will be enabled.
Clicking this will open the Export Confirmation dialog to verify that this export is what the user wanted to do.
Clicking _Start_ will start the export in bulk export mode if number of databases was above the bulk export number.

# Code structure

The files related to the Export are (some are also used in other parts)

- swedigarch_export_dialog_base.ui
- swedigarch_export_dialog.py
- select_connection_dialog_base.ui
- select_connection_dialog.py
- connect_to_db_dialog_base.ui
- connect_to_db_dialog.py
- export_confirmation_dialog.ui
- export_confirmation_dialog.py
- geo_package_bulk_export_task.py
- geo_package_export_task.py
- geopackage_export.py
- export_geopackage_to_csv.py
- help_dialog.ui
- help_dialog.py
- utils&period;py
- export_utils.py
- symbol_builder.py
- utils_classes.py
- constant&period;py

### swedigarch_export_dialog_base.ui

The UI file containing the main Export dialog. Can be edited in Qt Designer, included in the QGIS installation.

### swedigarch_export_dialog.py

The Python file connected to the _swedigarch_export_dialog_base.ui_ file. Responsible for all the export dialog backend code
that handles the interaction with the user.

This file is uses _select_connection_dialog.py_ to select a registered connection to the PostgreSQL server and it uses
_connect_to_db_dialog.py_ to connect to a PostgreSQL server even if it is not registered in the QGIS DB Manager.

When the user clicks "Run export" the confirmation dialog from _export_confirmation_dialog.py_ is opened to display
a list of databases that is about to be exported to confirm that this is what the user wants to do.
This dialog also uses the _utils&period;py_ for some common utility functions.

### select_connection_dialog_base.ui

The UI file containing the select connections dialog. Can be edited in Qt Designer, included in the QGIS installation.

### select_connection_dialog.py

The Python file connected to the _select_connection_dialog_base.ui_ file.
Responsible for all the dialog backend code that reads registered PostgreSQL connections and allows the user to select one. When one is selected the dialog tries to connect to that server in a backend process and the result is shown in a status text at the bottom of the dialog.
This dialog also uses the _utils&period;py_ for some common utility functions.

### connect_to_db_dialog_base.ui

The UI file containing the connect to DB dialog. Can be edited in Qt Designer, included in the QGIS installation.

### connect_to_db_dialog.py

The Python file connected to the _connect_to_db_dialog_base.ui_ file. Responsible for connect to DB dialog backend code that
handles the interaction with the user and testing of the connection.

### export_confirmation_dialog.ui

The UI file containing the export confirmation dialog. Can be edited in Qt Designer, included in the QGIS installation.

### export_confirmation_dialog.py

The Python file connected to the _export_confirmation_dialog.ui_ file. Responsible for export confirmation dialog backend code that handles the interaction with the user.

### geo_package_bulk_export_task.py

The Python class implementing a QgsTask that handles bulk export, if the number of databases is equal or greater that the threshold set in bulk*export_threshold in \_swedigarch_export_dialog.py* (currently 8).
This task runs parallel exports of databases, the number of parallel tasks is determined by: cpu*count() - 2
Where cpu_count() returns the number of parallel threads that can be executed by the CPU.
This uses \_geopackage_export.py*, _export_geopackage_to_csv.py_ and _constant&period;py_

### geo_package_export_task.py

The Python class implementing a QgsTask that handles export of databases bellow the bulk*export_threshold in \_swedigarch_export_dialog.py*. This task runs the exports on one database at a time.
This uses _geopackage_export.py_, _export_geopackage_to_csv.py_ and _constant&period;py_

### geopackage_export.py

The main Python export script that contains the export function export_to_geopackage()

### export_geopackage_to_csv.py

The Python script that does the CSV export.

### help_dialog.ui

The UI file containing the help dialog. Can be edited in Qt Designer, included in the QGIS installation.

### help_dialog.py

The Python file connected to the _help_dialog.ui_ file. Responsible for the help dialog.
This reads the configuration fil _help/help_sections.json_ where help sections and where the help is located.
This dialog is started with the name of the section we want to se help for.

### utils&period;py

Collection of general utility functions for the entire Intrasis plugin project.

### export_utils.py

Collection of export specific utility functions.

### symbol_builder.py

Help class (SymbolBuilder) that read symbology definitions from Intrasis database and convert it to
QGIS qml symbol definition file, this is then stored in table layer_styles to define visual style for the exported layers.

### utils_classes.py

Contains help classes:

- Site: Class to hold and handle site information from Intrasis
- IconType: The type of icon (CIRCLE or SQUARE) used in relations dialog
- SymbolException: Symbol specific Exception from _symbol_builder.py_

### constant&period;py

Contains constant definitions in three classes:

- Intrasis: Intrasis specific values
- RetCode: Return codes returned by the export function export*to_geopackage in file \_geopackage_export.py*
- WriterError: Write error codes

## Intrasis database Export

The export have to parts

1. GeoPackge export
2. CSV-Export (from GeoPackage) to .zip file

### The GeoPackage export process

Tables Created during export in the GeoPackage

| Table name          | Description                                            |
| ------------------- | ------------------------------------------------------ |
| objects             | Object base table                                      |
| attributes          | Attributes table, one attribute per row                |
| attribute_relations | Define the relations between objects and attributes    |
| object_relation     | Define the relations between objects                   |
| features            | Geometries for objects, linked on object_id to objects |
| layer_styles        | Holds the default symbology style for the layers       |
| project_information | Project information and a mid point of all geometries  |

The default table described in the GeoPackage definition are not described.

#### Layers

The geometry layers are defined as views against the feature table joined with the objects table filtered by geometry.
These are the possible geometries views that may be created (depends on what the Intrasis database contained)

- Point
- Multipoint
- Polyline
- Polygon

The geometry type Square in Intrasis is exported as Polygon

#### GeoPackge export walkthrough

Intrasis database export's can be done one by one or in bulk mode where multiple threads run many exports in parallel.
There is a variable in swedigarch_export_dialog.py named bulk_export_threshold that control witch mode an export will use.

The same export script function is used in both modes but in bulk it is called to only export one database.
This is function export_to_geopackage in geopackage_export.py, this function can take a list of databases to export.

1. It starts by verifying the connection to the database and then checking if the database really is an Intrasis database before continuing.
2. Internally it then uses the function export_database to export one database at a time.
3. In export_database it checks if the output file already exist and if so try to delete it (export override).
4. It then loads srid and Site (class object in Intrasis) information.
5. Find the geometry types in the database to export.
6. Export every geometry type into the features table, one by one and create the geometry view.
7. Export project information to the project_information table.
8. Export all objects from Intrasis database, except Staff and GeoObject class objects.
9. Build Symbology layer definition and save to layer_styles.
10. Export any raster geometries as separate layers with format: raster\_{geo_object_id}.
11. Export attributes for all exported objects to the attributes table, this is made by Class and SubClass because they can have different attributes defined.
12. Export relations from Intrasis into object_relation table.
13. Populate attributes_relations with data from attributes table.

Then the export_database function call is done and only some logfile writing is done.

### CSV-Export

Creates a .zip file with .csv files of the table content.

This export uses the GeoPackge as its source of data.

Geometries will be converted to WKT and included in the features.csv file.

An additional documentations text file will be added to the .zip file, (csv_documentation.txt).
