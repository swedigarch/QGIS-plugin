SELECT o."PublicId", o."ClassId", go."ObjectId" as "GeoObjectId", ST_SRID(the_raster) as srid, length(ST_AsGDALRaster(the_raster, 'GTiff')) FROM "GeoObject" go
	JOIN "GeoRel" gr ON go."ObjectId" = gr."GeoObjectId"
	JOIN "Object" o ON gr."ObjectId" = o."ObjectId" AND o."ClassId" NOT IN(__EXCLUDE_META_IDS__)
	WHERE the_raster is not null;