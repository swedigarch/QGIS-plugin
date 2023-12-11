SELECT o."ObjectId", a."Label", ad."MetaId", av."Value", ad."Unit", COALESCE(ft."AttributeId" > 0, false) as "LongText", ft."Text", am."AttributeOrder" FROM "Object" o
    JOIN "Attribute" a ON o."ObjectId" = a."ObjectId" AND o."ClassId" = __META_ID__
	JOIN "AttributeDef" ad ON a."MetaId" = ad."MetaId"
	JOIN "AttributeMember" am ON ad."MetaId" = am."AttributeDefId" AND am."IsVisible" = 'true' AND am."ObjectDefId" IN(__META_ID__)
    LEFT OUTER JOIN "AttributeValue" av ON a."AttributeId" = av."AttributeId"
    LEFT OUTER JOIN "FreeText" ft ON a."AttributeId" = ft."AttributeId"
	ORDER BY o."ObjectId", am."AttributeOrder"