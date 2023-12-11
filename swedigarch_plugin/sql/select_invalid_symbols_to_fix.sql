SELECT sd."SymbolId", sd."ClassId", sd.*, d1."Name" as "Class", d2."Name", 'MULTIPOINT' as "GeometryType", god."Type" as "GeoObjectType" FROM "SymbolDef" sd
	JOIN (SELECT DISTINCT "SymbolId" FROM "GeoObject" WHERE geometrytype(the_geom) IN('MULTIPOINT')) s ON sd."SymbolId" = s."SymbolId"
	JOIN "Definition" d1 ON sd."ClassId" = d1."MetaId" JOIN "Definition" d2 ON sd."MetaId" = d2."MetaId"
	JOIN "GeoObjectDef" god ON sd."GeoDefId" = god."MetaId" AND upper(god."Type") <> 'MULTIPOINT'
UNION
SELECT sd."SymbolId", sd."ClassId", sd.*, d1."Name" as "Class", d2."Name", 'POINT' as "GeometryType", god."Type" as "GeoObjectType" FROM "SymbolDef" sd
	JOIN (SELECT DISTINCT "SymbolId" FROM "GeoObject" WHERE geometrytype(the_geom) IN('POINT')) s ON sd."SymbolId" = s."SymbolId"
	JOIN "Definition" d1 ON sd."ClassId" = d1."MetaId" JOIN "Definition" d2 ON sd."MetaId" = d2."MetaId"
	JOIN "GeoObjectDef" god ON sd."GeoDefId" = god."MetaId" AND upper(god."Type") <> 'POINT'
UNION
SELECT sd."SymbolId", sd."ClassId", sd.*, d1."Name" as "Class", d2."Name", 'POLYGON' as "GeometryType", god."Type" as "GeoObjectType" FROM "SymbolDef" sd
	JOIN (SELECT DISTINCT "SymbolId" FROM "GeoObject" WHERE geometrytype(ST_Multi(the_geom)) IN('MULTIPOLYGON')) s ON sd."SymbolId" = s."SymbolId"
	JOIN "Definition" d1 ON sd."ClassId" = d1."MetaId" JOIN "Definition" d2 ON sd."MetaId" = d2."MetaId"
	JOIN "GeoObjectDef" god ON sd."GeoDefId" = god."MetaId" AND upper(god."Type") <> 'POLYGON'
UNION
SELECT sd."SymbolId", sd."ClassId", sd.*, d1."Name" as "Class", d2."Name", 'POLYLINE' as "GeometryType", god."Type" as "GeoObjectType" FROM "SymbolDef" sd
	JOIN (SELECT DISTINCT "SymbolId" FROM "GeoObject" WHERE geometrytype(ST_Multi(the_geom)) IN('MULTILINESTRING')) s ON sd."SymbolId" = s."SymbolId"
	JOIN "Definition" d1 ON sd."ClassId" = d1."MetaId" JOIN "Definition" d2 ON sd."MetaId" = d2."MetaId"
	JOIN "GeoObjectDef" god ON sd."GeoDefId" = god."MetaId" AND upper(god."Type") <> 'POLYLINE'
ORDER BY 1