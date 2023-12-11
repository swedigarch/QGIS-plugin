CREATE TABLE "objects" (
  "IntrasisId" INTEGER,
  "object_id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "Name" TEXT,
  "Class" TEXT,
  "SubClass" TEXT,
  "Color" INTEGER,
  geometry_count INTEGER,
  "attributes" TEXT
)