from sqlalchemy import select, util, sql
from sqlalchemy.sql.sqltypes import TEXT
from sqlalchemy.dialects.postgresql.base import PGInspector
from sqlalchemy.dialects.postgresql import pg_catalog
from sqlalchemy.dialects.postgresql import arraylib as _array
from sqlalchemy.dialects.postgresql.ext import aggregate_order_by
from sqlalchemy.sql import bindparam



class AuroraPostgresDataAPIInspector(PGInspector):
    @util.memoized_property
    def _constraint_query(self):
        if self.server_version_info >= (11, 0):
            indnkeyatts = pg_catalog.pg_index.c.indnkeyatts
        else:
            indnkeyatts = pg_catalog.pg_index.c.indnatts.label("indnkeyatts")

        if self.server_version_info >= (15,):
            indnullsnotdistinct = pg_catalog.pg_index.c.indnullsnotdistinct
        else:
            indnullsnotdistinct = sql.false().label("indnullsnotdistinct")

        # CHANGED: Replaced generate_subscripts with row_number() window function
        # because generate_subscripts is not supported by Aurora Data API
        # Original: sql.func.generate_subscripts(pg_catalog.pg_index.c.indkey, 1).label("ord")
        # New approach: Use row_number() to generate ordinal positions for constraint columns
        con_sq = (
            select(
                pg_catalog.pg_constraint.c.conrelid,
                pg_catalog.pg_constraint.c.conname,
                sql.func.unnest(pg_catalog.pg_index.c.indkey).label("attnum"),
                # CHANGED: Use row_number() window function instead of generate_subscripts
                # This generates ordinal positions (1, 2, 3, ...) for each constraint's columns
                sql.func.row_number().over(
                    partition_by=[pg_catalog.pg_constraint.c.conname],
                    order_by=[pg_catalog.pg_constraint.c.conname]
                ).label("ord"),
                indnkeyatts,
                indnullsnotdistinct,
                pg_catalog.pg_description.c.description,
            )
            .join(
                pg_catalog.pg_index,
                pg_catalog.pg_constraint.c.conindid
                == pg_catalog.pg_index.c.indexrelid,
            )
            .outerjoin(
                pg_catalog.pg_description,
                pg_catalog.pg_description.c.objoid
                == pg_catalog.pg_constraint.c.oid,
            )
            .where(
                pg_catalog.pg_constraint.c.contype == bindparam("contype"),
                pg_catalog.pg_constraint.c.conrelid.in_(bindparam("oids")),
                # NOTE: filtering also on pg_index.indrelid for oids does
                # not seem to have a performance effect, but it may be an
                # option if perf problems are reported
            )
            .subquery("con")
        )

        attr_sq = (
            select(
                con_sq.c.conrelid,
                con_sq.c.conname,
                con_sq.c.description,
                con_sq.c.ord,
                con_sq.c.indnkeyatts,
                con_sq.c.indnullsnotdistinct,
                pg_catalog.pg_attribute.c.attname,
            )
            .select_from(pg_catalog.pg_attribute)
            .join(
                con_sq,
                sql.and_(
                    pg_catalog.pg_attribute.c.attnum == con_sq.c.attnum,
                    pg_catalog.pg_attribute.c.attrelid == con_sq.c.conrelid,
                ),
            )
            .where(
                # NOTE: restate the condition here, since pg15 otherwise
                # seems to get confused on pscopg2 sometimes, doing
                # a sequential scan of pg_attribute.
                # The condition in the con_sq subquery is not actually needed
                # in pg15, but it may be needed in older versions. Keeping it
                # does not seems to have any inpact in any case.
                con_sq.c.conrelid.in_(bindparam("oids"))
            )
            .subquery("attr")
        )

        return (
            select(
                attr_sq.c.conrelid,
                sql.func.array_agg(
                    # NOTE: cast since some postgresql derivatives may
                    # not support array_agg on the name type
                    aggregate_order_by(
                        attr_sq.c.attname.cast(TEXT), attr_sq.c.ord
                    )
                ).label("cols"),
                attr_sq.c.conname,
                sql.func.min(attr_sq.c.description).label("description"),
                sql.func.min(attr_sq.c.indnkeyatts).label("indnkeyatts"),
                sql.func.bool_and(attr_sq.c.indnullsnotdistinct).label(
                    "indnullsnotdistinct"
                ),
            )
            .group_by(attr_sq.c.conrelid, attr_sq.c.conname)
            .order_by(attr_sq.c.conrelid, attr_sq.c.conname)
        )


    @util.memoized_property
    def _index_query(self):
        """
        sql.func.generate_subscripts is not supported by Aurora Data API
        so we need to rewrite the index query to avoid using it.
        """
        # NOTE: pg_index is used as from two times to improve performance,
        # since extraing all the index information from `idx_sq` to avoid
        # the second pg_index use leads to a worse performing query in
        # particular when querying for a single table (as of pg 17)
        # NOTE: repeating oids clause improve query performance

        # subquery to get the columns
        
        # CHANGED: Replaced generate_subscripts with row_number() window function
        # because generate_subscripts is not supported by Aurora Data API
        # Original: sql.func.generate_subscripts(pg_catalog.pg_index.c.indkey, 1).label("ord")
        # New approach: Use row_number() over the unnested arrays to generate ordinal positions
        idx_sq = (
            select(
                pg_catalog.pg_index.c.indexrelid,
                pg_catalog.pg_index.c.indrelid,
                sql.func.unnest(pg_catalog.pg_index.c.indkey).label("attnum"),
                sql.func.unnest(pg_catalog.pg_index.c.indclass).label(
                    "att_opclass"
                ),
                # CHANGED: Use row_number() window function instead of generate_subscripts
                # This generates ordinal positions (1, 2, 3, ...) for each index's columns
                sql.func.row_number().over(
                    partition_by=[pg_catalog.pg_index.c.indexrelid],
                    order_by=[pg_catalog.pg_index.c.indexrelid]
                ).label("ord"),
            )
            .where(
                ~pg_catalog.pg_index.c.indisprimary,
                pg_catalog.pg_index.c.indrelid.in_(bindparam("oids")),
            )
            .subquery("idx")
        )

        attr_sq = (
            select(
                idx_sq.c.indexrelid,
                idx_sq.c.indrelid,
                idx_sq.c.ord,
                # NOTE: always using pg_get_indexdef is too slow so just
                # invoke when the element is an expression
                sql.case(
                    (
                        idx_sq.c.attnum == 0,
                        pg_catalog.pg_get_indexdef(
                            idx_sq.c.indexrelid, idx_sq.c.ord + 1, True
                        ),
                    ),
                    # NOTE: need to cast this since attname is of type "name"
                    # that's limited to 63 bytes, while pg_get_indexdef
                    # returns "text" so its output may get cut
                    else_=pg_catalog.pg_attribute.c.attname.cast(TEXT),
                ).label("element"),
                (idx_sq.c.attnum == 0).label("is_expr"),
                pg_catalog.pg_opclass.c.opcname,
                pg_catalog.pg_opclass.c.opcdefault,
            )
            .select_from(idx_sq)
            .outerjoin(
                # do not remove rows where idx_sq.c.attnum is 0
                pg_catalog.pg_attribute,
                sql.and_(
                    pg_catalog.pg_attribute.c.attnum == idx_sq.c.attnum,
                    pg_catalog.pg_attribute.c.attrelid == idx_sq.c.indrelid,
                ),
            )
            .outerjoin(
                pg_catalog.pg_opclass,
                pg_catalog.pg_opclass.c.oid == idx_sq.c.att_opclass,
            )
            .where(idx_sq.c.indrelid.in_(bindparam("oids")))
            .subquery("idx_attr")
        )

        cols_sq = (
            select(
                attr_sq.c.indexrelid,
                sql.func.min(attr_sq.c.indrelid),
                sql.func.array_agg(
                    aggregate_order_by(attr_sq.c.element, attr_sq.c.ord)
                ).label("elements"),
                sql.func.array_agg(
                    aggregate_order_by(attr_sq.c.is_expr, attr_sq.c.ord)
                ).label("elements_is_expr"),
                sql.func.array_agg(
                    aggregate_order_by(attr_sq.c.opcname, attr_sq.c.ord)
                ).label("elements_opclass"),
                sql.func.array_agg(
                    aggregate_order_by(attr_sq.c.opcdefault, attr_sq.c.ord)
                ).label("elements_opdefault"),
            )
            .group_by(attr_sq.c.indexrelid)
            .subquery("idx_cols")
        )

        if self.server_version_info >= (11, 0):
            indnkeyatts = pg_catalog.pg_index.c.indnkeyatts
        else:
            indnkeyatts = pg_catalog.pg_index.c.indnatts.label("indnkeyatts")

        if self.server_version_info >= (15,):
            nulls_not_distinct = pg_catalog.pg_index.c.indnullsnotdistinct
        else:
            nulls_not_distinct = sql.false().label("indnullsnotdistinct")

        return (
            select(
                pg_catalog.pg_index.c.indrelid,
                pg_catalog.pg_class.c.relname,
                pg_catalog.pg_index.c.indisunique,
                pg_catalog.pg_constraint.c.conrelid.is_not(None).label(
                    "has_constraint"
                ),
                pg_catalog.pg_index.c.indoption,
                pg_catalog.pg_class.c.reloptions,
                pg_catalog.pg_am.c.amname,
                # NOTE: pg_get_expr is very fast so this case has almost no
                # performance impact
                sql.case(
                    (
                        pg_catalog.pg_index.c.indpred.is_not(None),
                        pg_catalog.pg_get_expr(
                            pg_catalog.pg_index.c.indpred,
                            pg_catalog.pg_index.c.indrelid,
                        ),
                    ),
                    else_=None,
                ).label("filter_definition"),
                indnkeyatts,
                nulls_not_distinct,
                cols_sq.c.elements,
                cols_sq.c.elements_is_expr,
                cols_sq.c.elements_opclass,
                cols_sq.c.elements_opdefault,
            )
            .select_from(pg_catalog.pg_index)
            .where(
                pg_catalog.pg_index.c.indrelid.in_(bindparam("oids")),
                ~pg_catalog.pg_index.c.indisprimary,
            )
            .join(
                pg_catalog.pg_class,
                pg_catalog.pg_index.c.indexrelid == pg_catalog.pg_class.c.oid,
            )
            .join(
                pg_catalog.pg_am,
                pg_catalog.pg_class.c.relam == pg_catalog.pg_am.c.oid,
            )
            .outerjoin(
                cols_sq,
                pg_catalog.pg_index.c.indexrelid == cols_sq.c.indexrelid,
            )
            .outerjoin(
                pg_catalog.pg_constraint,
                sql.and_(
                    pg_catalog.pg_index.c.indrelid
                    == pg_catalog.pg_constraint.c.conrelid,
                    pg_catalog.pg_index.c.indexrelid
                    == pg_catalog.pg_constraint.c.conindid,
                    pg_catalog.pg_constraint.c.contype
                    == sql.any_(_array.array(("p", "u", "x"))),
                ),
            )
            .order_by(
                pg_catalog.pg_index.c.indrelid, pg_catalog.pg_class.c.relname
            )
        )

    def _columns_query(self, schema, has_filter_names, scope, kind):
        """Override to cast CHAR/name type columns to TEXT for Aurora Data API compatibility.

        Aurora Data API doesn't support CHAR data type in result sets.
        PostgreSQL system catalog columns like pg_attribute.attname, pg_class.relname
        are of type 'name' (essentially CHAR(63)), so we need to cast them to TEXT.
        """
        # NOTE: the query with the default and identity options scalar
        # subquery is faster than trying to use outer joins for them
        generated = (
            pg_catalog.pg_attribute.c.attgenerated.label("generated")
            if self.server_version_info >= (12,)
            else sql.null().label("generated")
        )
        if self.server_version_info >= (10,):
            # join lateral performs worse (~2x slower) than a scalar_subquery
            identity = (
                select(
                    sql.func.json_build_object(
                        "always",
                        pg_catalog.pg_attribute.c.attidentity == "a",
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
                        type_=sql.sqltypes.JSON(),
                    )
                )
                .select_from(pg_catalog.pg_sequence)
                .where(
                    # attidentity != '' is required or it will reflect also
                    # serial columns as identity.
                    pg_catalog.pg_attribute.c.attidentity != "",
                    pg_catalog.pg_sequence.c.seqrelid
                    == sql.cast(
                        sql.cast(
                            pg_catalog.pg_get_serial_sequence(
                                sql.cast(
                                    sql.cast(
                                        pg_catalog.pg_attribute.c.attrelid,
                                        sql.sqltypes.BIGINT,  # REGCLASS equivalent
                                    ),
                                    TEXT,
                                ),
                                # CHANGED: Cast attname (name type) to TEXT for Aurora Data API compatibility
                                pg_catalog.pg_attribute.c.attname.cast(TEXT),
                            ),
                            sql.sqltypes.BIGINT,  # REGCLASS equivalent
                        ),
                        sql.sqltypes.BIGINT,  # OID equivalent
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
                # CHANGED: Cast attname (name type) to TEXT for Aurora Data API compatibility
                pg_catalog.pg_attribute.c.attname.cast(TEXT).label("name"),
                pg_catalog.format_type(
                    pg_catalog.pg_attribute.c.atttypid,
                    pg_catalog.pg_attribute.c.atttypmod,
                ).label("format_type"),
                default,
                pg_catalog.pg_attribute.c.attnotnull.label("not_null"),
                # CHANGED: Cast relname (name type) to TEXT for Aurora Data API compatibility
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
                # CHANGED: Cast relname to TEXT for sorting compatibility
                pg_catalog.pg_class.c.relname.cast(TEXT),
                pg_catalog.pg_attribute.c.attnum
            )
        )
        query = self._pg_class_filter_scope_schema(query, schema, scope=scope)
        if has_filter_names:
            query = query.where(
                # CHANGED: Cast relname to TEXT for comparison compatibility
                pg_catalog.pg_class.c.relname.cast(TEXT).in_(bindparam("filter_names"))
            )
        return query

