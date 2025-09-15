from sqlalchemy import select, util, sql, exc as sqlalchemy_exc
import sqlalchemy.sql.sqltypes as sqltypes
from sqlalchemy.dialects.postgresql.base import PGDialect
from sqlalchemy.dialects.postgresql import JSON, JSONB, UUID, ARRAY
from sqlalchemy.dialects.mysql.base import MySQLDialect
from sqlalchemy.util import memoized_property

import re
from .base import (
    _ADA_ARRAY,
    _ADA_DATE,
    _ADA_DOUBLE,
    _ADA_FLOAT,
    _ADA_SA_JSON,
    _ADA_JSON,
    _ADA_JSONB,
    _ADA_TIME,
    _ADA_TIMESTAMP,
    _ADA_UUID,
    _ADA_ENUM,
    _ADA_NUMERIC,
)

import aurora_data_api


class AuroraMySQLDataAPIDialect(MySQLDialect):
    # See https://docs.sqlalchemy.org/en/13/core/internals.html#sqlalchemy.engine.interfaces.Dialect
    driver = "aurora_data_api"
    default_schema_name = None
    supports_native_decimal = True
    colspecs = util.update_copy(
        MySQLDialect.colspecs,
        {
            sqltypes.Date: _ADA_DATE,
            sqltypes.Time: _ADA_TIME,
            sqltypes.DateTime: _ADA_TIMESTAMP,
        },
    )
    supports_statement_cache = True

    @classmethod
    def import_dbapi(cls):
        return aurora_data_api

    def _detect_charset(self, connection):
        return connection.execute("SHOW VARIABLES LIKE 'character_set_client'").fetchone()[1]

    def _extract_error_code(self, exception):
        return exception.args[0].value

    def create_connect_args(self, url, _translate_args=None):
        """Create connection arguments from URL."""
        opts = url.translate_connect_args(username="user")
        opts.update(url.query)

        # Map URL parameters to aurora-data-api parameters
        connect_args = {}
        if "aurora_cluster_arn" in opts:
            connect_args["aurora_cluster_arn"] = opts.pop("aurora_cluster_arn")
        if "secret_arn" in opts:
            connect_args["secret_arn"] = opts.pop("secret_arn")
        if "database" in opts:
            connect_args["database"] = opts.pop("database")
        elif "dbname" in opts:
            connect_args["database"] = opts.pop("dbname")
        if "charset" in opts:
            connect_args["charset"] = opts.pop("charset")

        # Remove standard connection parameters that aurora-data-api doesn't use
        opts.pop("host", None)
        opts.pop("port", None)
        opts.pop("user", None)
        opts.pop("password", None)

        return [], connect_args

    @classmethod
    def load_provisioning(cls):
        """Load provisioning hooks for Aurora dialect testing."""
        __import__("sqlalchemy_aurora_data_api.provision")

    @memoized_property
    def dbapi_exception_translation_map(self):
        """Map Aurora Data API exceptions to SQLAlchemy exceptions."""
        import aurora_data_api.exceptions as ada_exc

        return {
            ada_exc.IntegrityError: sqlalchemy_exc.IntegrityError,
            ada_exc.DataError: sqlalchemy_exc.DataError,
            ada_exc.OperationalError: sqlalchemy_exc.OperationalError,
            ada_exc.ProgrammingError: sqlalchemy_exc.ProgrammingError,
            ada_exc.NotSupportedError: sqlalchemy_exc.NotSupportedError,
            ada_exc.InternalError: sqlalchemy_exc.InternalError,
            ada_exc.InterfaceError: sqlalchemy_exc.InterfaceError,
            ada_exc.DatabaseError: sqlalchemy_exc.DatabaseError,
        }

    def _handle_dbapi_exception(self, e):
        """Handle Aurora Data API exception mapping."""
        if hasattr(e, 'args') and e.args:
            error_msg = str(e.args[0])
            # Look for PostgreSQL SQLState codes: "ERROR: ... SQLState: 23505"
            sqlstate_match = re.search(r'SQLState: (\w+)', error_msg)
            if sqlstate_match:
                sqlstate = sqlstate_match.group(1)
                if sqlstate in ('23505', '23503', '23502', '23514', '23000'):
                    # Integrity constraint violations -> IntegrityError
                    import aurora_data_api.exceptions as ada_exc
                    integrity_error = ada_exc.IntegrityError(error_msg)
                    if hasattr(e, 'response'):
                        integrity_error.response = e.response
                    return integrity_error
        return e

    def do_execute(self, cursor, statement, parameters, context=None):
        """Override to handle exception mapping."""
        try:
            cursor.execute(statement, parameters)
        except Exception as e:
            transformed_e = self._handle_dbapi_exception(e)
            raise transformed_e from e




class AuroraPostgresDataAPIDialect(PGDialect):
    # See https://docs.sqlalchemy.org/en/13/core/internals.html#sqlalchemy.engine.interfaces.Dialect
    driver = "aurora_data_api"
    default_schema_name = None
    colspecs = util.update_copy(
        PGDialect.colspecs,
        {
            sqltypes.JSON: _ADA_SA_JSON,
            JSON: _ADA_JSON,
            JSONB: _ADA_JSONB,
            UUID: _ADA_UUID,
            sqltypes.Uuid: _ADA_UUID,
            sqltypes.Date: _ADA_DATE,
            sqltypes.Time: _ADA_TIME,
            sqltypes.DateTime: _ADA_TIMESTAMP,
            sqltypes.Enum: _ADA_ENUM,
            sqltypes.Numeric: _ADA_NUMERIC,
            sqltypes.Float: _ADA_FLOAT,
            sqltypes.Double: _ADA_DOUBLE,
            ARRAY: _ADA_ARRAY,
        },
    )
    supports_sane_multi_rowcount = False
    supports_statement_cache = True
    supports_distinct_on = True

    # Aurora Data API PostgreSQL limitations
    # The generatedFields feature is not supported, but RETURNING clause is supported
    # Reference: "To get the values of generated fields, use the RETURNING clause"
    insert_returning = True  # RETURNING clause is supported
    supports_lastrowid = False  # generatedFields is not supported
    supports_returning = True  # RETURNING clause is supported


    @classmethod
    def import_dbapi(cls):
        return aurora_data_api



    def _extract_error_code(self, exception):
        return exception.args[0].value

    def create_connect_args(self, url, _translate_args=None):
        """Create connection arguments from URL."""
        opts = url.translate_connect_args(username="user")
        opts.update(url.query)

        # Map URL parameters to aurora-data-api parameters
        connect_args = {}
        if "aurora_cluster_arn" in opts:
            connect_args["aurora_cluster_arn"] = opts.pop("aurora_cluster_arn")
        if "secret_arn" in opts:
            connect_args["secret_arn"] = opts.pop("secret_arn")
        if "database" in opts:
            connect_args["database"] = opts.pop("database")
        elif "dbname" in opts:
            connect_args["database"] = opts.pop("dbname")

        # Remove standard connection parameters that aurora-data-api doesn't use
        # FIXME: this entire section can be deleted once DB API is updated.
        opts.pop("host", None)
        opts.pop("port", None)
        opts.pop("user", None)
        opts.pop("password", None)

        # Initialize with normal transaction mode
        connect_args["skip_begin_transaction"] = False

        return [], connect_args


    @classmethod
    def load_provisioning(cls):
        """Load provisioning hooks for Aurora dialect testing."""
        __import__("sqlalchemy_aurora_data_api.provision")

    @memoized_property
    def dbapi_exception_translation_map(self):
        """Map Aurora Data API exceptions to SQLAlchemy exceptions."""
        import aurora_data_api.exceptions as ada_exc

        return {
            ada_exc.IntegrityError: sqlalchemy_exc.IntegrityError,
            ada_exc.DataError: sqlalchemy_exc.DataError,
            ada_exc.OperationalError: sqlalchemy_exc.OperationalError,
            ada_exc.ProgrammingError: sqlalchemy_exc.ProgrammingError,
            ada_exc.NotSupportedError: sqlalchemy_exc.NotSupportedError,
            ada_exc.InternalError: sqlalchemy_exc.InternalError,
            ada_exc.InterfaceError: sqlalchemy_exc.InterfaceError,
            ada_exc.DatabaseError: sqlalchemy_exc.DatabaseError,
        }

    def _handle_dbapi_exception(self, e):
        """Handle Aurora Data API exception mapping."""
        if hasattr(e, 'args') and e.args:
            error_msg = str(e.args[0])
            # Look for PostgreSQL SQLState codes: "ERROR: ... SQLState: 23505"
            sqlstate_match = re.search(r'SQLState: (\w+)', error_msg)
            if sqlstate_match:
                sqlstate = sqlstate_match.group(1)
                if sqlstate in ('23505', '23503', '23502', '23514', '23000'):
                    # Integrity constraint violations -> IntegrityError
                    import aurora_data_api.exceptions as ada_exc
                    integrity_error = ada_exc.IntegrityError(error_msg)
                    if hasattr(e, 'response'):
                        integrity_error.response = e.response
                    return integrity_error
        return e

    def do_execute(self, cursor, statement, parameters, context=None):
        """Override to handle exception mapping."""
        try:
            cursor.execute(statement, parameters)
        except Exception as e:
            transformed_e = self._handle_dbapi_exception(e)
            raise transformed_e from e


    def _columns_query(self, schema, has_filter_names, scope, kind):
        """Override to cast CHAR/name type columns to TEXT for Aurora Data API compatibility.

        This is a copy of PGDialect._columns_query with CHAR type columns cast to TEXT.
        Aurora Data API doesn't support CHAR data type in result sets.
        """
        from sqlalchemy.dialects.postgresql import pg_catalog
        from sqlalchemy.sql.sqltypes import TEXT
        from sqlalchemy.sql import bindparam
        import sqlalchemy.sql.sqltypes as sqltypes

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
            # there is not row with pg_attribute.attnum > 0. use a left outer
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

    @util.memoized_property
    def _constraint_query(self):
        """Override to replace generate_subscripts with row_number() for Aurora Data API compatibility."""
        from sqlalchemy.dialects.postgresql import pg_catalog
        from sqlalchemy.dialects.postgresql.ext import aggregate_order_by
        from sqlalchemy.sql.sqltypes import TEXT
        from sqlalchemy.sql import bindparam

        if self.server_version_info >= (11, 0):
            indnkeyatts = pg_catalog.pg_index.c.indnkeyatts
        else:
            indnkeyatts = pg_catalog.pg_index.c.indnatts.label("indnkeyatts")

        if self.server_version_info >= (15,):
            indnullsnotdistinct = pg_catalog.pg_index.c.indnullsnotdistinct
        else:
            indnullsnotdistinct = sql.false().label("indnullsnotdistinct")

        # AURORA CHANGE: Replaced generate_subscripts with row_number() window function
        # because generate_subscripts is not supported by Aurora Data API
        # Original: sql.func.generate_subscripts(pg_catalog.pg_index.c.indkey, 1).label("ord")
        # New approach: Use row_number() to generate ordinal positions for constraint columns
        con_sq = (
            select(
                pg_catalog.pg_constraint.c.conrelid,
                pg_catalog.pg_constraint.c.conname,
                sql.func.unnest(pg_catalog.pg_index.c.indkey).label("attnum"),
                # AURORA CHANGE: Use row_number() window function instead of generate_subscripts
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
            .where(con_sq.c.conrelid.in_(bindparam("oids")))
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
        """Override to replace generate_subscripts with row_number() for Aurora Data API compatibility."""
        from sqlalchemy.dialects.postgresql import pg_catalog
        from sqlalchemy.dialects.postgresql import arraylib as _array
        from sqlalchemy.dialects.postgresql.ext import aggregate_order_by
        from sqlalchemy.sql.sqltypes import TEXT
        from sqlalchemy.sql import bindparam
        import sqlalchemy.sql.sqltypes as sqltypes
        from sqlalchemy.dialects.postgresql.base import OID

        # AURORA CHANGE: Replaced generate_subscripts with row_number() window function
        # because generate_subscripts is not supported by Aurora Data API
        # Original: sql.func.generate_subscripts(pg_catalog.pg_index.c.indkey, 1).label("ord")
        # New approach: Use row_number() over the unnested arrays to generate ordinal positions
        idx_sq = (
            select(
                pg_catalog.pg_index.c.indexrelid,
                pg_catalog.pg_index.c.indrelid,
                sql.func.unnest(pg_catalog.pg_index.c.indkey).label("attnum"),
                # AURORA CHANGE: Cast unnested indclass to proper OID type for comparison
                sql.cast(sql.func.unnest(pg_catalog.pg_index.c.indclass), sqltypes.BIGINT).label(
                    "att_opclass"
                ),
                # AURORA CHANGE: Use row_number() window function instead of generate_subscripts
                # This generates ordinal positions (1, 2, 3, ...) for each index's columns
                sql.func.row_number().over(
                    partition_by=[pg_catalog.pg_index.c.indexrelid],
                    order_by=[pg_catalog.pg_index.c.indexrelid]
                ).label("ord"),
            )
            .where(
                ~pg_catalog.pg_index.c.indisprimary,
                # AURORA CHANGE: Cast OID to TEXT for Aurora Data API compatibility with parameter binding
                sql.cast(pg_catalog.pg_index.c.indrelid, sqltypes.TEXT).in_(bindparam("oids")),
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
                            # AURORA CHANGE: Cast to OID for pg_get_indexdef function compatibility
                            sql.cast(idx_sq.c.indexrelid, OID),
                            # AURORA CHANGE: Cast to INTEGER for pg_get_indexdef function compatibility
                            sql.cast(idx_sq.c.ord + 1, sqltypes.Integer),
                            True
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
                    # AURORA CHANGE: Cast OIDs to BIGINT for Aurora Data API compatibility
                    sql.cast(pg_catalog.pg_attribute.c.attrelid, sqltypes.BIGINT) == sql.cast(idx_sq.c.indrelid, sqltypes.BIGINT),
                ),
            )
            .outerjoin(
                pg_catalog.pg_opclass,
                # AURORA CHANGE: Cast OID to BIGINT for Aurora Data API compatibility
                sql.cast(pg_catalog.pg_opclass.c.oid, sqltypes.BIGINT) == idx_sq.c.att_opclass,
            )
            # AURORA CHANGE: Cast OID to TEXT for Aurora Data API compatibility with parameter binding
            .where(sql.cast(idx_sq.c.indrelid, sqltypes.TEXT).in_(bindparam("oids")))
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
                # AURORA CHANGE: Cast OID to TEXT for Aurora Data API compatibility with parameter binding
                sql.cast(pg_catalog.pg_index.c.indrelid, sqltypes.TEXT).in_(bindparam("oids")),
                ~pg_catalog.pg_index.c.indisprimary,
            )
            .join(
                pg_catalog.pg_class,
                # AURORA CHANGE: Cast both OIDs to BIGINT for Aurora Data API compatibility
                sql.cast(pg_catalog.pg_index.c.indexrelid, sqltypes.BIGINT) == sql.cast(pg_catalog.pg_class.c.oid, sqltypes.BIGINT),
            )
            .join(
                pg_catalog.pg_am,
                # AURORA CHANGE: Cast both OIDs to BIGINT for Aurora Data API compatibility
                sql.cast(pg_catalog.pg_class.c.relam, sqltypes.BIGINT) == sql.cast(pg_catalog.pg_am.c.oid, sqltypes.BIGINT),
            )
            .outerjoin(
                cols_sq,
                # AURORA CHANGE: Cast OID to BIGINT for Aurora Data API compatibility
                sql.cast(pg_catalog.pg_index.c.indexrelid, sqltypes.BIGINT) == cols_sq.c.indexrelid,
            )
            .outerjoin(
                pg_catalog.pg_constraint,
                sql.and_(
                    # AURORA CHANGE: Cast OIDs to BIGINT for Aurora Data API compatibility
                    sql.cast(pg_catalog.pg_index.c.indrelid, sqltypes.BIGINT)
                    == sql.cast(pg_catalog.pg_constraint.c.conrelid, sqltypes.BIGINT),
                    sql.cast(pg_catalog.pg_index.c.indexrelid, sqltypes.BIGINT)
                    == sql.cast(pg_catalog.pg_constraint.c.conindid, sqltypes.BIGINT),
                    pg_catalog.pg_constraint.c.contype
                    == sql.any_(_array.array(("p", "u", "x"))),
                ),
            )
            .order_by(
                pg_catalog.pg_index.c.indrelid, pg_catalog.pg_class.c.relname
            )
        )
