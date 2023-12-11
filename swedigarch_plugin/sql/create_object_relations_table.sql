CREATE TABLE object_relations (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "base_id" MEDIUMINT,
    "related_id" MEDIUMINT,
    "base_text" TEXT(30),
    "related_text" TEXT(30)
);