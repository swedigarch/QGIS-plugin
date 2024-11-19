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
"""Utils functions for Class SubClass Browser"""
from qgis.core import QgsMessageLog, Qgis
import sqlite3
import pandas as pd
import numpy as np
from . import utils as Utils
from . import browse_relations_utils as BrowseRelationsUtils

MESSAGE_CATEGORY = 'Class_Subclass_Browser'

def get_relation_dataframe(gpkg, child_object_id):
    sql_query = f'''WITH Parent AS (
    SELECT base_id, related_id
    FROM object_relations
	WHERE related_id IN ({child_object_id})
   ),
GrandParent AS (
    SELECT base_id, related_id
    FROM object_relations 
    WHERE related_id IN (SELECT base_id FROM Parent)
),GreatGrandParent AS (
    SELECT base_id, related_id
    FROM object_relations 
    WHERE related_id IN (SELECT base_id FROM GrandParent)
),RelationTable AS(
SELECT p.related_id as child_id,
p.base_id as parent_id,
po.IntrasisId as ParentId,
po.Class as parent_class,
gp.base_id as grand_parent_id,
gpo.IntrasisId as GrandParentId,
gpo.Class as grand_parent_class,
ggp.base_id as great_grand_parent_id,
ggpo.IntrasisId as GreatGrandParentId,
ggpo.Class as great_grand_parent_class,
COALESCE(po.class,'NULL')||'_'||COALESCE(gpo.class,'NULL')||'_'||COALESCE(ggpo.class,'NULL') AS parenthierarchy
FROM Parent p
left join GrandParent gp on p.base_id = gp.related_id
left join GreatGrandParent ggp on gp.base_id = ggp.related_id
left join objects po on p.base_id = po.object_id
left join objects gpo on gp.base_id = gpo.object_id
left join objects ggpo on ggp.base_id = ggpo.object_id
),ParentHierarchyCount AS(
select parenthierarchy, count(parenthierarchy) as parenthierarchy_count
from RelationTable
group by parenthierarchy
),ParentCount AS (
    SELECT distinct
        child_id,parent_class,
		COUNT(parent_class) OVER (PARTITION BY child_id, parent_class) AS parent_count
    FROM RelationTable rt
    GROUP BY child_id, parent_id
),GrandParentCount AS (
    SELECT distinct
        child_id,grand_parent_class,
		COUNT(grand_parent_class) OVER (PARTITION BY child_id, grand_parent_class) AS grand_parent_count
    FROM RelationTable rt
    GROUP BY child_id, grand_parent_id
),GreatGrandParentCount AS (
    SELECT distinct
        child_id,great_grand_parent_class,
		COUNT(great_grand_parent_class) OVER (PARTITION BY child_id, great_grand_parent_class) AS great_grand_parent_count
    FROM RelationTable rt
    GROUP BY child_id, great_grand_parent_id
),ParentIdString AS (
    SELECT
	child_id, parent_class,
	GROUP_CONCAT(ParentId, ',') OVER (PARTITION BY child_id, parent_class) AS ParentIdString 
    FROM (select distinct child_id, parent_class, ParentId from RelationTable)
),GrandParentIdString AS (
    SELECT
	child_id, grand_parent_class,
	GROUP_CONCAT(GrandParentId, ',') OVER (PARTITION BY child_id, grand_parent_class) AS GrandParentIdString 
    FROM (select distinct child_id, grand_parent_class, GrandParentId from RelationTable)
),GreatGrandParentIdString AS (
    SELECT
	child_id, great_grand_parent_class,
	GROUP_CONCAT(GreatGrandParentId, ',') OVER (PARTITION BY child_id, great_grand_parent_class) AS GreatGrandParentIdString 
    FROM (select distinct child_id, great_grand_parent_class, GreatGrandParentId from RelationTable)
)

Select DISTINCT rt.*, phc.parenthierarchy_count, pc.parent_count, gpc.grand_parent_count, ggpc.great_grand_parent_count
,pis.ParentIdString, gpis.GrandParentIdString, ggpis.GreatGrandParentIdString
from RelationTable rt
LEFT join ParentHierarchyCount phc ON rt.parenthierarchy = phc.parenthierarchy
LEFT JOIN ParentCount pc ON rt.child_id = pc.child_id and rt.parent_class = pc.parent_class
LEFT JOIN GrandParentCount gpc ON rt.child_id = gpc.child_id and rt.grand_parent_class = gpc.grand_parent_class
LEFT JOIN GreatGrandParentCount ggpc ON rt.child_id = ggpc.child_id and rt.great_grand_parent_class = ggpc.great_grand_parent_class
LEFT JOIN ParentIdString pis ON rt.child_id = pis.child_id and rt.parent_class = pis.parent_class
LEFT JOIN GrandParentIdString gpis ON rt.child_id = gpis.child_id and rt.grand_parent_class = gpis.grand_parent_class
LEFT JOIN GreatGrandParentIdString ggpis ON rt.child_id = ggpis.child_id and rt.great_grand_parent_class = ggpis.great_grand_parent_class'''
    conn = sqlite3.connect(gpkg)
    relation_dataframe = pd.read_sql_query(sql_query, conn)
    conn.close()
    #print(sql_query)
    return relation_dataframe

def get_child_class(gpkg, child_object_id):
    sql_query = f'''select distinct class from objects WHERE object_id IN ({child_object_id})'''
    conn = sqlite3.connect(gpkg)
    child_class_dataframe = pd.read_sql_query(sql_query, conn)
    conn.close()
    #print(sql_query)
    child_class_string = ', '.join(child_class_dataframe['Class'].astype(str))
    return child_class_string
