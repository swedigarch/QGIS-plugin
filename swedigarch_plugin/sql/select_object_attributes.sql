SELECT 
    o."ObjectId" as object_id, 
    a."Label", 
    __ATTRIBUTE_VALUE__,
    ad."Unit", 
    ad."DataType", 
    (o."ClassId" = am."ObjectDefId") as "Class", 
    COALESCE(ft."AttributeId" > 0, false) as "LongText", 
    __FREE_TEXT_VALUE__,
    am."AttributeOrder" 
FROM "Object" o
    JOIN "Attribute" a ON o."ObjectId" = a."ObjectId" AND o."ClassId" = __CLASS__
	JOIN "AttributeDef" ad ON a."MetaId" = ad."MetaId"
	JOIN "AttributeMember" am ON ad."MetaId" = am."AttributeDefId" AND (o."ClassId" = am."ObjectDefId" OR o."SubClassId" = am."ObjectDefId") AND am."IsVisible" = 'true' AND am."ObjectDefId" IN(__CLS_IDS__)
    LEFT OUTER JOIN "AttributeValue" av ON a."AttributeId" = av."AttributeId"
    LEFT OUTER JOIN "FreeText" ft ON a."AttributeId" = ft."AttributeId"
ORDER BY o."ObjectId"__ORDERING__, am."AttributeOrder"