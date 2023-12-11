SELECT DISTINCT o."ClassId"::integer, o."SubClassId"::integer, d1."Name" as "Class", d2."Name" as "SubClass"
FROM "Object" o
	join "Definition" d1 on o."ClassId" = d1."MetaId" AND o."ClassId" NOT IN(__EXCLUDE_META_IDS__)
	left outer join "Definition" d2 on o."SubClassId" = d2."MetaId"
ORDER BY 1, 2