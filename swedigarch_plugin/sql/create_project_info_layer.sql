SELECT (row_number() OVER())::INTEGER AS "fid", ST_GeometricMedian(ST_Multi(ST_Collect(ST_Centroid(ST_Force2D(ST_SetSRID(the_geom, 0)))))) as geom, __ATTR__ FROM "GeoObject" WHERE ST_isValid(the_geom) = TRUE