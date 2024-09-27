SELECT DISTINCT scd."ClassId", scd."MetaId", d."Name" FROM "Definition" d JOIN "SubClassDef" scd ON d."MetaId" = scd."MetaId"
JOIN "Object" o ON scd."ClassId" = o."ClassId" AND scd."MetaId" = o."SubClassId" AND o."ClassId" NOT IN (SELECT "MetaId" FROM "SysDefs" WHERE "SystemId" IN (3, 4, 23, 9990)) 
ORDER BY 1,2