SELECT 
    count(*) AS 'Total loaded objects', 
    sum(hasgeometry) AS 'Objects with Geometry', 
    sum(hasnogeometry) AS 'Objects without Geometry' 
FROM (
    SELECT 
        o.object_id, 
        MAX(CASE WHEN f.object_id IS NOT NULL THEN 1 ELSE 0 END) AS hasgeometry, 
        MAX(CASE WHEN f.object_id IS NULL THEN 1 ELSE 0 END) AS hasnogeometry 
    FROM objects o 
    LEFT JOIN features f ON o.object_id = f.object_id 
    WHERE o.object_id IN (__OBJECT_ID__)
    GROUP BY o.object_id
)