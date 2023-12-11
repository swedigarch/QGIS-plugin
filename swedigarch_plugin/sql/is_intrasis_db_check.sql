SELECT CASE WHEN (SELECT count(*) FROM pg_tables where schemaname = 'public') > 31
		AND EXISTS(select  * from pg_tables where schemaname = 'public' AND tablename = 'GeoObject')
		AND EXISTS(select  * from pg_tables where schemaname = 'public' AND tablename = 'Object')
		AND EXISTS(select  * from pg_tables where schemaname = 'public' AND tablename = 'Attribute')
		AND EXISTS(select  * from pg_tables where schemaname = 'public' AND tablename = 'Definition')
		AND EXISTS(select  * from pg_tables where schemaname = 'public' AND tablename = 'SysDefs')
	THEN 'Intrasis DB' ELSE 'Not Intrasis' END