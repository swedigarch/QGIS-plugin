CREATE TABLE gpkgext_relations (
  id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
  base_table_name TEXT NOT NULL,
  base_primary_column TEXT NOT NULL DEFAULT 'id',
  related_table_name TEXT NOT NULL,
  related_primary_column TEXT NOT NULL DEFAULT 'id',
  relation_name TEXT NOT NULL,
  mapping_table_name TEXT NOT NULL UNIQUE
 );