SELECT av."Value"::integer FROM "Object" o LEFT OUTER JOIN "SysDefs" sd ON sd."SystemId" = 489
	JOIN "Attribute" a ON o."ObjectId" = a."ObjectId" AND a."MetaId" = COALESCE(sd."MetaId", 489)
	JOIN "AttributeValue" av ON a."AttributeId" = av."AttributeId" WHERE o."ClassId" = 4