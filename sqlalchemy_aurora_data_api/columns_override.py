def _columns_query_override(self, schema, has_filter_names, scope, kind):
    """Override to cast CHAR/name type columns to TEXT for Aurora Data API compatibility.

    This is a copy of PGDialect._columns_query with CHAR type columns cast to TEXT.
    Aurora Data API doesn't support CHAR data type in result sets.
    """
    from sqlalchemy import select, sql
    import sqlalchemy.sql.sqltypes as sqltypes
    from sqlalchemy.dialects.postgresql import pg_catalog
    from sqlalchemy.sql.sqltypes import TEXT
    from sqlalchemy.sql import bindparam


    # NOTE: the query with the default and identity options scalar
    # subquery is faster than trying to use outer joins for them
    # AURORA CHANGE: Cast attgenerated ("char" type) to TEXT for Aurora Data API compatibility
    generated = (
        pg_catalog.pg_attribute.c.attgenerated.cast(TEXT).label("generated")
        if self.server_version_info >= (12,)
        else sql.null().label("generated")
    )
    if self.server_version_info >= (10,):
        # join lateral performs worse (~2x slower) than a scalar_subquery
        identity = (
            select(
                sql.func.json_build_object(
                    "always",
                    # AURORA CHANGE: Cast attidentity ("char" type) to TEXT for Aurora Data API compatibility
                    pg_catalog.pg_attribute.c.attidentity.cast(TEXT) == "a",
                    "start",
                    pg_catalog.pg_sequence.c.seqstart,
                    "increment",
                    pg_catalog.pg_sequence.c.seqincrement,
                    "minvalue",
                    pg_catalog.pg_sequence.c.seqmin,
                    "maxvalue",
                    pg_catalog.pg_sequence.c.seqmax,
                    "cache",
                    pg_catalog.pg_sequence.c.seqcache,
                    "cycle",
                    pg_catalog.pg_sequence.c.seqcycle,
                    type_=sqltypes.JSON(),
                )
            )
            .select_from(pg_catalog.pg_sequence)
            .where(
                # attidentity != '' is required or it will reflect also
                # serial columns as identity.
                # AURORA CHANGE: Cast attidentity ("char" type) to TEXT for Aurora Data API compatibility
                pg_catalog.pg_attribute.c.attidentity.cast(TEXT) != "",
                pg_catalog.pg_sequence.c.seqrelid
                == sql.cast(
                    sql.cast(
                        pg_catalog.pg_get_serial_sequence(
                            sql.cast(
                                sql.cast(
                                    pg_catalog.pg_attribute.c.attrelid,
                                    sqltypes.BIGINT,  # REGCLASS equivalent
                                ),
                                TEXT,
                            ),
                            # AURORA CHANGE: Cast attname to TEXT for Aurora Data API compatibility
                            pg_catalog.pg_attribute.c.attname.cast(TEXT),
                        ),
                        sqltypes.BIGINT,  # REGCLASS equivalent
                    ),
                    sqltypes.BIGINT,  # OID equivalent
                ),
            )
            .correlate(pg_catalog.pg_attribute)
            .scalar_subquery()
            .label("identity_options")
        )
    else:
        identity = sql.null().label("identity_options")

    # join lateral performs the same as scalar_subquery here
    default = (
        select(
            pg_catalog.pg_get_expr(
                pg_catalog.pg_attrdef.c.adbin,
                pg_catalog.pg_attrdef.c.adrelid,
            )
        )
        .select_from(pg_catalog.pg_attrdef)
        .where(
            pg_catalog.pg_attrdef.c.adrelid
            == pg_catalog.pg_attribute.c.attrelid,
            pg_catalog.pg_attrdef.c.adnum
            == pg_catalog.pg_attribute.c.attnum,
            pg_catalog.pg_attribute.c.atthasdef,
        )
        .correlate(pg_catalog.pg_attribute)
        .scalar_subquery()
        .label("default")
    )
    relkinds = self._kind_to_relkinds(kind)
    query = (
        select(
            # AURORA CHANGE: Cast attname to TEXT for Aurora Data API compatibility
            pg_catalog.pg_attribute.c.attname.cast(TEXT).label("name"),
            pg_catalog.format_type(
                pg_catalog.pg_attribute.c.atttypid,
                pg_catalog.pg_attribute.c.atttypmod,
            ).label("format_type"),
            default,
            pg_catalog.pg_attribute.c.attnotnull.label("not_null"),
            # AURORA CHANGE: Cast relname to TEXT for Aurora Data API compatibility
            pg_catalog.pg_class.c.relname.cast(TEXT).label("table_name"),
            pg_catalog.pg_description.c.description.label("comment"),
            generated,
            identity,
        )
        .select_from(pg_catalog.pg_class)
        # NOTE: postgresql support table with no user column, meaning
        # there is no row with pg_attribute.attnum > 0. use a left outer
        # join to avoid filtering these tables.
        .outerjoin(
            pg_catalog.pg_attribute,
            sql.and_(
                pg_catalog.pg_class.c.oid
                == pg_catalog.pg_attribute.c.attrelid,
                pg_catalog.pg_attribute.c.attnum > 0,
                ~pg_catalog.pg_attribute.c.attisdropped,
            ),
        )
        .outerjoin(
            pg_catalog.pg_description,
            sql.and_(
                pg_catalog.pg_description.c.objoid
                == pg_catalog.pg_attribute.c.attrelid,
                pg_catalog.pg_description.c.objsubid
                == pg_catalog.pg_attribute.c.attnum,
            ),
        )
        .where(self._pg_class_relkind_condition(relkinds))
        .order_by(
            # AURORA CHANGE: Cast relname to TEXT for sorting compatibility
            pg_catalog.pg_class.c.relname.cast(TEXT),
            pg_catalog.pg_attribute.c.attnum
        )
    )
    query = self._pg_class_filter_scope_schema(query, schema, scope=scope)
    if has_filter_names:
        query = query.where(
            # AURORA CHANGE: Cast relname to TEXT for comparison compatibility
            pg_catalog.pg_class.c.relname.cast(TEXT).in_(bindparam("filter_names"))
        )

    return query