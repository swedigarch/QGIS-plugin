SELECT DISTINCT 
	o."ObjectId" as object_id, 
	o."PublicId" as "IntrasisId", 
	o."Name", 
	d1."Name" as "Class", 
	__SUBCLASS_NAME_SELECT__, 
	od."Color", 
	Count(geo."ObjectId") as geometry_count, 
	NULL  as attributes
FROM "Object" o JOIN "ObjectDef" od on o."ClassId" = od."MetaId"
	JOIN "Definition" d1 on o."ClassId" = d1."MetaId" AND o."ClassId" NOT IN(__EXCLUDE_META_IDS__)
	LEFT OUTER JOIN "Definition" d2 on o."SubClassId" = d2."MetaId"
	LEFT OUTER JOIN "GeoRel" gr ON o."ObjectId" = gr."ObjectId"
	LEFT OUTER JOIN "GeoObject" geo ON gr."GeoObjectId" = geo."ObjectId"
	GROUP BY o."ObjectId", o."PublicId", o."Name", d1."Name", d2."Name", od."Color"
ORDER BY 1 asc, o."PublicId"