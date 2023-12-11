# Introduction

The Intrasis Relationship Browser consists of a main QDialog where all data and relationships for the selected object is displayed. This dialog contains QTreeWidgets for displaying the selected object's relationships, QTableWidgets for displaying the selected object's attributes and a QComboBox for collecting all QGIS selected features allowing the user to select which object/feature to view.

# Code structure

The files related to the Relationship Browser are

- intrasis_analysis_browse_relations.py
- intrasis_analysis_browse_relations_dialog.ui
- select_tree_nodes_dialog.py
- select_tree_nodes_dialog.ui
- select_geo_package_dalog.py
- create_layers_from_all_child_nodes_task.py
- browse_relations_utils.py
- browse_relations_utils_classes.py
- create_layers_utils.py
- utils.py

### intrasis_analysis_browse_relations_dialog.ui

The UI file containing the Relationship Browser dialog and all its widgets. The file can be opened and modified in the Qt Designer that is included in the QGIS installation.

### intrasis_analysis_browse_relations.py

The Python file that connects to the _intrasis_analysis_browse_relations_dialog.ui_ file is responsible for managing the user interface data and handling user interactions.

The file uses the _select_tree_nodes_dialog.py_ file to select which of the nodes that should be exported when the user clicks the "Create Layer from children" button, and the utils files _browse_relations_utils.py_, _browse_relations_utils_classes.py_, _create_layers_utils.py_, _utils.py_ for retrieving and handling data from the active GeoPackage, and for accessing some shared gui functions, and for creating QGIS layers from the selected relations.

### select_tree_nodes_dialog.ui

The UI file containing the Select Tree Nodes dialog and all its widgets, which can be opened and modified in the Qt Designer that is included in the QGIS installation.

### select_tree_nodes_dialog.py

The Python file connected to the select*tree_nodes_dialog.ui* file. Responsible for holding the gui data and handling interaction with the user.

This dialog is opened from the _intrasis_analysis_browse_relations.py_ file when the user clicks the "Create Layers from children button", and allows the user to remove nodes from the tree structure in the "Related below" QtreeWidget before QGIS layers are created.

This file uses the utils files _browse_relations_utils.py_ and _browse_relations_utils_classes.py_ for accessing some shared GUI-functions.

### create_layers_from_all_child_nodes_task.py

Python file containing the class CreateLayersFromAllChildNodesTask, which inherits QgsTask. CreateLayersFromAllChildNodesTask is used for creating QGIS layers from child nodes or closes parents nodes in a QGIS background process.

CreateLayersFromAllChildNodesTask uses the utils files _browse_relations_utils.py_, _browse_relations_utils_classes.py_, _create_layers_utils.py_ and _utils.py_ for accessing shared functions and classes connected to creating layers.

### browse_relations_utils.py

Collection of utils functions related to the Relationship Browser. Mainly functions for data handling, retrieving data from geopackage and handling the relationship tree structure that is necessary for the Relationship Browser dialog to function properly.

### browse_relations_utils_classes.py

Collection of classes that is needed for the Relationship Browser.

#### IntrasisTreeWidgetItem

Extends the QTreeWidgetItem class, to be able to use a custom class, holding necessary data and convenience functions, in the QTreeWidgets in the Relationship Browser dialog.

Has a class member _self.intrasis_item_ that is an _IntrasisItem_ object.

#### IntrasisItem

A class containing an object's Intrasis information, such as IntrasisId, Name, Class, SubClass, and related functions.

#### LayerGroupTreeNode

Extends the QTreeWidgetItem class and is used as a custom tree data structure when creating layers in the _CreateLayersFromAllChildNodesTask_ class to create the hierarchical tree structure that the resulting QGIS layer groups should have. Since it is not allowed to create QGIS layer groups in a background thread, the layer group name and a list of layers that the group should contain is stored for each tree node using this data structure.

The QGIS layer groups are created, and their layers added, in the function _on_task_create_layers_finished_ in _intrasis_analysis_browse_relations.py_ which is called when the background thread emits its _result_done_signal_ signal.

### create_layers_utils.py

Collection of utility functions related to creating QGIS layers. Used when creating layers from selected object/tree structure in the Relationship Browser.

### utils.py

Collection of general utility functions for the entire Intrasis plugin project.

# SQL queries used in the code

All SQL queries related to the Relationship Browser can be found in _browse_relations_utils.py_. All SQL queries used for creating layers (currently only used by the Relationship Browser) can be found in _create_layers_utils.py_. The SQL queries are listed below:

### SQL queries in browse_relations_utils.py

In function _get_realated_below_: Get related_id and related_text from the object_relations table where base_id=object_id, i.e. all relations directly below object_id.

,```sql
SELECT related_id, related_text FROM object_relations WHERE base_id = {object_id}
```

In function _get_realated_above_: Get base_id and related_text from the object_relations table where related_id=object_id, i.e. all relations directly above object_id.

```sql
SELECT base_id, base_text FROM object_relations WHERE related_id = {object_id}
```

### SQL queries in create_layers_utils.py

In function _get_attribute_list_for_class_subclass_combination_: Get a list of all attributes for a combination of class/subclass.

```sql
SELECT attribute_label, attribute_unit, class, data_type
FROM attributes WHERE object_id
    IN (
        SELECT object_id FROM
        (
            SELECT object_id, COUNT(*) AS num_attributes
            FROM attributes
            WHERE object_id IN
            (
                SELECT object_id
                FROM objects
                WHERE Class = '{class_name}' AND SubClass {subclass_where_clause}
            )
            GROUP BY object_id ORDER BY num_attributes DESC LIMIT 1
        )t)
```

where _subclass_where_clause_ is decided by

```python
subclass_where_clause = f"= '{subclass_name}'"
if Utils.is_empty_string_or_none(subclass_name):
    subclass_where_clause = "IS NULL"
```

so if the current object has a subclass the _subclass_where_clause_ will be "= subclass_name" otherwise it will be "IS NULL"
