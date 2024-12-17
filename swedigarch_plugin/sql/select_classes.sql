SELECT d."MetaId", d."Name" from "Definition" d JOIN "ClassDef" cd ON d."MetaId" = cd."MetaId" AND d."MetaId" IN(SELECT "ClassId" FROM "Object")
WHERE d."MetaId" NOT IN (SELECT "MetaId" FROM "SysDefs" WHERE "SystemId" IN (3, 4, 23, 9990)) 
ORDER BY d."Name"