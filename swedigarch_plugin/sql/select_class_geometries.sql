SELECT DISTINCT o."ClassId", 
	CASE
		WHEN Substring(ST_GeometryType(go.the_geom), 4) = 'MultiPoint' THEN 'Multipoint'
		WHEN Substring(ST_GeometryType(go.the_geom), 4) = 'LineString' THEN 'Polyline'
		WHEN Substring(ST_GeometryType(go.the_geom), 4) = 'MultiLineString' THEN 'Polyline'
		WHEN Substring(ST_GeometryType(go.the_geom), 4) = 'MultiPolygon' THEN 'Polygon'
		ELSE Substring(ST_GeometryType(go.the_geom), 4)
	END	as "Type" 
	FROM "Object" o JOIN "GeoRel" gr ON o."ObjectId" = gr."ObjectId" JOIN "GeoObject" go ON gr."GeoObjectId" = go."ObjectId" and go.the_geom is not null
Order By 1