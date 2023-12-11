SELECT sd.*, d1."Name" as "Class", d2."Name", god."Type" as "GeoObjectType" FROM "SymbolDef" sd
	JOIN (SELECT DISTINCT "SymbolId" FROM "GeoObject" WHERE GEOM_FILTER_STRING) s ON sd."SymbolId" = s."SymbolId"
	JOIN "Definition" d1 ON sd."ClassId" = d1."MetaId" JOIN "Definition" d2 ON sd."MetaId" = d2."MetaId"
	JOIN "GeoObjectDef" god ON sd."GeoDefId" = god."MetaId"
	ORDER BY sd."SymbolId"