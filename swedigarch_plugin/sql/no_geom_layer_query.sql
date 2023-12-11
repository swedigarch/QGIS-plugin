SELECT DISTINCT (row_number() OVER() -1)::INTEGER AS "fid", o."PublicId" as intrasis_id, ST_GeomFromText('POINT EMPTY', __SRID__) as "geom", o."Name", d1."Name" as "Class", d2."Name" as "SubClass", o."ObjectId" as object_id,
	NULL as "SymbolId", NULL as "GeoObjectId", '' as spatial_type, NULL  as attributes
FROM "Object" o
	join "Definition" d1 on o."ClassId" = d1."MetaId" AND o."ClassId" NOT IN(__EXCLUDE_META_IDS__) AND o."ObjectId" NOT IN(SELECT "ObjectId" FROM "GeoRel")
	left outer join "Definition" d2 on o."SubClassId" = d2."MetaId"
ORDER BY 1 asc, o."PublicId"