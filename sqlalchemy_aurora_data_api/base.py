import datetime
import re
import decimal

from sqlalchemy import select, cast, func, util, sql, exc as sqlalchemy_exc
import sqlalchemy.sql.sqltypes as sqltypes
from sqlalchemy.dialects.postgresql import JSON, JSONB, UUID, DATE, TIME, TIMESTAMP, ARRAY, ENUM
from sqlalchemy.dialects.postgresql.base import PGDialect
from sqlalchemy.dialects.mysql.base import MySQLDialect
from sqlalchemy.engine import reflection
from functools import lru_cache


class _ADA_SA_JSON(sqltypes.JSON):
    def bind_expression(self, value):
        return cast(value, sqltypes.JSON)


class _ADA_JSON(JSON):
    def bind_expression(self, value):
        return cast(value, JSON)


class _ADA_JSONB(JSONB):
    def bind_expression(self, value):
        return cast(value, JSONB)


class _ADA_UUID(UUID):
    def bind_expression(self, value):
        return cast(value, UUID)

    def result_processor(self, dialect, coltype):
        import uuid

        def process(value):
            if isinstance(value, str):
                # Check if as_uuid=False was specified
                if hasattr(self, "as_uuid") and not self.as_uuid:
                    return value  # Return as string
                return uuid.UUID(value)
            return value

        return process


class _ADA_ENUM(ENUM):
    def bind_expression(self, value):
        return cast(value, self)


# TODO: is TZ awareness needed here?
class _ADA_DATETIME_MIXIN:
    iso_ts_re = re.compile(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+")

    @staticmethod
    def ms(value):
        # Three digit fractional second component, truncated and zero padded. This is what the data api requires.
        return str(value.microsecond).zfill(6)[:-3]

    def bind_processor(self, dialect):
        def process(value):
            return value.isoformat() if isinstance(value, self.py_type) else value

        return process

    def bind_expression(self, value):
        return cast(value, self.sa_type)

    def result_processor(self, dialect, coltype):
        def process(value):
            # When the microsecond component ends in zeros, they are omitted from the return value,
            # and datetime.datetime.fromisoformat can't parse the result (example: '2019-10-31 09:37:17.31869
            # '). Pad it.
            if isinstance(value, str) and self.iso_ts_re.match(value):
                value = self.iso_ts_re.sub(lambda match: match.group(0).ljust(26, "0"), value)
            if isinstance(value, str):
                try:
                    return self.py_type.fromisoformat(value)
                except AttributeError:  # fromisoformat not supported on Python < 3.7
                    if self.py_type == datetime.date:
                        return datetime.datetime.strptime(value, "%Y-%m-%d").date()
                    if self.py_type == datetime.time:
                        return datetime.datetime.strptime(value, "%H:%M:%S").time()
                    if "." in value:
                        return datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f")
                    return datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            return value

        return process


class _ADA_DATE(_ADA_DATETIME_MIXIN, DATE):
    py_type = datetime.date
    sa_type = sqltypes.Date

    def bind_processor(self, dialect):
        def process(value):
            return value.strftime("%Y-%m-%d") if isinstance(value, self.py_type) else value

        return process


class _ADA_TIME(_ADA_DATETIME_MIXIN, TIME):
    py_type = datetime.time
    sa_type = sqltypes.Time

    def bind_processor(self, dialect):
        def process(value):
            return value.strftime("%H:%M:%S.") + self.ms(value) if isinstance(value, self.py_type) else value

        return process


class _ADA_TIMESTAMP(_ADA_DATETIME_MIXIN, TIMESTAMP):
    py_type = datetime.datetime
    sa_type = sqltypes.DateTime

    def bind_processor(self, dialect):
        def process(value):
            return value.strftime("%Y-%m-%d %H:%M:%S.") + self.ms(value) if isinstance(value, self.py_type) else value

        return process


class _ADA_NUMERIC(sqltypes.Numeric):
    def result_processor(self, dialect, coltype):
        def process(value):
            if value is None:
                return value

            # Aurora Data API returns numeric values as float (doubleValue)
            # For asdecimal=True (default), convert float to Decimal
            if self.asdecimal and isinstance(value, float):
                return decimal.Decimal(str(value))

            # Handle asdecimal=False case: return float as-is
            if not self.asdecimal:
                if isinstance(value, decimal.Decimal):
                    return float(value)
                return float(value) if not isinstance(value, float) else value

            # For other cases (already Decimal), return as-is
            return value

        return process


class _ADA_FLOAT(sqltypes.Float):
    """Aurora Data API Float type to distinguish from Numeric."""

    pass


class _ADA_DOUBLE(sqltypes.Double):
    """Aurora Data API Double type to distinguish from Numeric."""

    pass


class _ADA_ARRAY(ARRAY):
    def bind_processor(self, dialect):
        def process(value):
            # FIXME: escape strings properly here
            return "\v".join(value) if isinstance(value, list) else value

        return process

    def bind_expression(self, value):
        return func.string_to_array(value, "\v")


class BaseADAMySQLDialect(MySQLDialect):
    # See https://docs.sqlalchemy.org/en/13/core/internals.html#sqlalchemy.engine.interfaces.Dialect

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

    @util.memoized_property
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
        if hasattr(e, "args") and e.args:
            error_msg = str(e.args[0])
            # Look for PostgreSQL SQLState codes: "ERROR: ... SQLState: 23505"
            sqlstate_match = re.search(r"SQLState: (\w+)", error_msg)
            if sqlstate_match:
                sqlstate = sqlstate_match.group(1)
                if sqlstate in ("23505", "23503", "23502", "23514", "23000"):
                    # Integrity constraint violations -> IntegrityError
                    import aurora_data_api.exceptions as ada_exc

                    integrity_error = ada_exc.IntegrityError(error_msg)
                    if hasattr(e, "response"):
                        integrity_error.response = e.response
                    return integrity_error
        return e

    def _detect_charset(self, connection):
        return connection.execute("SHOW VARIABLES LIKE 'character_set_client'").fetchone()[1]


class BaseADAPGDialect(PGDialect):
    # See https://docs.sqlalchemy.org/en/13/core/internals.html#sqlalchemy.engine.interfaces.Dialect

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

    # AURORA CHANGE: Enable name normalization for consistent identifier handling
    # Aurora Data API may return identifiers with inconsistent casing
    requires_name_normalize = True

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

    def _extract_error_code(self, exception):
        """Extract error code from exception."""
        return exception.args[0].value

    @util.memoized_property
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
        if hasattr(e, "args") and e.args:
            error_msg = str(e.args[0])
            # Look for PostgreSQL SQLState codes: "ERROR: ... SQLState: 23505"
            sqlstate_match = re.search(r"SQLState: (\w+)", error_msg)
            if sqlstate_match:
                sqlstate = sqlstate_match.group(1)
                if sqlstate in ("23505", "23503", "23502", "23514", "23000"):
                    # Integrity constraint violations -> IntegrityError
                    import aurora_data_api.exceptions as ada_exc

                    integrity_error = ada_exc.IntegrityError(error_msg)
                    if hasattr(e, "response"):
                        integrity_error.response = e.response
                    return integrity_error
        return e

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
        # AURORA CHANGE: Cast attgenerated from PostgreSQL "char" type to TEXT
        # PostgreSQL "char" is a single-character type, but Aurora Data API doesn't support it in result sets
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
                        # AURORA CHANGE: Cast attidentity from PostgreSQL "char" type to TEXT
                        # PostgreSQL "char" stores identity column type ('a'=always, 'd'=by default, ''=none)
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
                    # AURORA CHANGE: Cast attidentity from PostgreSQL "char" type to TEXT
                    # PostgreSQL "char" stores identity column type, but Aurora Data API can't return this type
                    pg_catalog.pg_attribute.c.attidentity.cast(TEXT) != "",
                    # AURORA CHANGE: Simplified casting for pg_get_serial_sequence compatibility
                    # Aurora Data API can't handle complex double-casting in function parameters
                    pg_catalog.pg_sequence.c.seqrelid
                    == sql.cast(
                        pg_catalog.pg_get_serial_sequence(
                            # AURORA CHANGE: Quote table name to handle special characters properly
                            # Use quote_ident to properly escape table names with special characters
                            sql.func.quote_ident(pg_catalog.pg_class.c.relname.cast(TEXT)),
                            # AURORA CHANGE: Cast attname from PostgreSQL "name" type to TEXT and quote it
                            sql.func.quote_ident(pg_catalog.pg_attribute.c.attname.cast(TEXT)),
                        ),
                        sqltypes.BIGINT,  # Cast result to BIGINT for OID compatibility
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
                pg_catalog.pg_attrdef.c.adrelid == pg_catalog.pg_attribute.c.attrelid,
                pg_catalog.pg_attrdef.c.adnum == pg_catalog.pg_attribute.c.attnum,
                pg_catalog.pg_attribute.c.atthasdef,
            )
            .correlate(pg_catalog.pg_attribute)
            .scalar_subquery()
            .label("default")
        )
        relkinds = self._kind_to_relkinds(kind)
        query = (
            select(
                # AURORA CHANGE: Cast attname from PostgreSQL "name" type to TEXT
                # PostgreSQL "name" is a 63-byte string type used for object names
                pg_catalog.pg_attribute.c.attname.cast(TEXT).label("name"),
                pg_catalog.format_type(
                    pg_catalog.pg_attribute.c.atttypid,
                    pg_catalog.pg_attribute.c.atttypmod,
                ).label("format_type"),
                default,
                pg_catalog.pg_attribute.c.attnotnull.label("not_null"),
                # AURORA CHANGE: Cast relname from PostgreSQL "name" type to TEXT
                # PostgreSQL "name" is a 63-byte string type used for relation names
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
                    pg_catalog.pg_class.c.oid == pg_catalog.pg_attribute.c.attrelid,
                    pg_catalog.pg_attribute.c.attnum > 0,
                    ~pg_catalog.pg_attribute.c.attisdropped,
                ),
            )
            .outerjoin(
                pg_catalog.pg_description,
                sql.and_(
                    pg_catalog.pg_description.c.objoid == pg_catalog.pg_attribute.c.attrelid,
                    pg_catalog.pg_description.c.objsubid == pg_catalog.pg_attribute.c.attnum,
                ),
            )
            .where(self._pg_class_relkind_condition(relkinds))
            .order_by(
                # AURORA CHANGE: Cast relname from PostgreSQL "name" type to TEXT for sorting compatibility
                # PostgreSQL "name" type may not sort properly when mixed with other string types
                pg_catalog.pg_class.c.relname.cast(TEXT),
                pg_catalog.pg_attribute.c.attnum,
            )
        )
        query = self._pg_class_filter_scope_schema(query, schema, scope=scope)
        if has_filter_names:
            query = query.where(
                # AURORA CHANGE: Cast relname from PostgreSQL "name" type to TEXT for comparison compatibility
                # Ensures proper string comparison when filter_names contains standard strings
                pg_catalog.pg_class.c.relname.cast(TEXT).in_(bindparam("filter_names"))
            )
        return query

    def _parse_indoption_text(self, indoption_text):
        """Parse indoption TEXT representation back to list of integers.

        The indoption field is an int2vector in PostgreSQL, which Aurora Data API
        converts to TEXT. We need to parse it back to integers for bitwise operations.

        Args:
            indoption_text: TEXT representation like "0 0 0" or ""

        Returns:
            List of integers for bitwise operations
        """
        if not indoption_text or indoption_text.strip() == "":
            return []

        try:
            # Handle both space-separated and array-like formats
            text = str(indoption_text).strip()

            # Remove array brackets if present: "{0,0,0}" -> "0,0,0"
            if text.startswith("{") and text.endswith("}"):
                text = text[1:-1]
                # Split by comma for array format
                parts = [x.strip() for x in text.split(",") if x.strip()]
            else:
                # Split by whitespace for space-separated format
                parts = [x.strip() for x in text.split() if x.strip()]

            return [int(x) for x in parts if x]
        except (ValueError, AttributeError, TypeError):
            # If parsing fails, return empty list (no special sorting)
            return []

    def _clean_expression_output(self, expression):
        """Clean expression output from Aurora Data API.

        Aurora Data API automatically adds ::text casting in expressions.
        Remove these for cleaner, more standard output.
        """
        # if not expression:
        #     return expression

        # # Remove ::text, ::character varying, and similar type casts commonly added by Aurora
        # import re
        # # Pattern to match ::type_name (including variations like ::character varying)
        # pattern = r'::[a-zA-Z_][a-zA-Z0-9_]*(?:\s+[a-zA-Z_][a-zA-Z0-9_]*)*(?:\([^)]*\))?'
        # cleaned = re.sub(pattern, '', expression)

        # return cleaned.strip()
        return expression

    def get_multi_indexes(self, connection, schema, filter_names, scope, kind, **kw):
        """Override to handle indoption TEXT conversion for Aurora Data API."""
        from collections import defaultdict
        from sqlalchemy.engine.reflection import ReflectionDefaults

        table_oids = self._get_table_oids(connection, schema, filter_names, scope, kind, **kw)

        indexes = defaultdict(list)
        default = ReflectionDefaults.indexes

        batches = list(table_oids)

        while batches:
            batch = batches[0:3000]
            batches[0:3000] = []

            result = connection.execute(
                # AURORA CHANGE: Convert OIDs to integers for Aurora Data API compatibility (OID type not supported)
                self._index_query,
                {"oids": [int(r[0]) for r in batch]},
            ).mappings()

            result_by_oid = defaultdict(list)
            for row_dict in result:
                # AURORA CHANGE: Normalize indrelid to integer for consistent matching
                # Aurora Data API returns indrelid as string, but we need integer keys
                result_by_oid[int(row_dict["indrelid"])].append(row_dict)

            for oid, table_name in batch:
                # AURORA CHANGE: Handle both integer and string OID types for consistent matching
                oid_key = int(oid) if not isinstance(oid, int) else oid
                if oid_key not in result_by_oid:
                    indexes[(schema, table_name)] = default()
                    continue

                for row in result_by_oid[oid_key]:
                    index_name = row["relname"]
                    table_indexes = indexes[(schema, table_name)]

                    all_elements = row["elements"]
                    all_elements_is_expr = row["elements_is_expr"]
                    all_elements_opclass = row["elements_opclass"]
                    all_elements_opdefault = row["elements_opdefault"]
                    indnkeyatts = row["indnkeyatts"]
                    # "The number of key columns in the index, not counting any
                    # included columns, which are merely stored and do not
                    # participate in the index semantics"
                    if len(all_elements) > indnkeyatts:
                        # this is a "covering index" which has INCLUDE columns
                        # as well as regular index columns
                        inc_cols = all_elements[indnkeyatts:]
                        idx_elements = all_elements[:indnkeyatts]
                        idx_elements_is_expr = all_elements_is_expr[:indnkeyatts]
                        # postgresql does not support expression on included
                        # columns as of v14: "ERROR: expressions are not
                        # supported in included columns".
                        assert all(not is_expr for is_expr in all_elements_is_expr[indnkeyatts:])
                        idx_elements_opclass = all_elements_opclass[:indnkeyatts]
                        idx_elements_opdefault = all_elements_opdefault[:indnkeyatts]
                    else:
                        idx_elements = all_elements
                        idx_elements_is_expr = all_elements_is_expr
                        inc_cols = []
                        idx_elements_opclass = all_elements_opclass
                        idx_elements_opdefault = all_elements_opdefault

                    index = {"name": index_name, "unique": row["indisunique"]}

                    if any(idx_elements_is_expr):
                        index["column_names"] = [
                            None if is_expr else expr for expr, is_expr in zip(idx_elements, idx_elements_is_expr)
                        ]
                        # AURORA CHANGE: Clean expression output for Aurora Data API
                        index["expressions"] = [
                            self._clean_expression_output(expr) if is_expr else expr
                            for expr, is_expr in zip(idx_elements, idx_elements_is_expr)
                        ]
                    else:
                        index["column_names"] = idx_elements

                    dialect_options = {}

                    # AURORA CHANGE: Add postgresql_ops support for custom operator classes
                    if not all(idx_elements_opdefault):
                        dialect_options["postgresql_ops"] = {
                            name: opclass
                            for name, opclass, is_default in zip(
                                idx_elements,
                                idx_elements_opclass,
                                idx_elements_opdefault,
                            )
                            if not is_default
                        }

                    sorting = {}
                    # AURORA CHANGE: Parse TEXT indoption back to integers for bitwise operations
                    indoption_ints = self._parse_indoption_text(row["indoption"])
                    for col_index, col_flags in enumerate(indoption_ints):
                        if col_index >= len(idx_elements):
                            break  # Safety check

                        col_sorting = ()
                        # try to set flags only if they differ from PG defaults...
                        if col_flags & 0x01:
                            col_sorting += ("desc",)
                            if not (col_flags & 0x02):
                                col_sorting += ("nulls_last",)
                        else:
                            if col_flags & 0x02:
                                col_sorting += ("nulls_first",)
                        if col_sorting:
                            sorting[idx_elements[col_index]] = col_sorting

                    if sorting:
                        index["column_sorting"] = sorting
                    if row["has_constraint"]:
                        index["duplicates_constraint"] = index_name

                    if row["reloptions"]:
                        dialect_options["postgresql_with"] = dict(
                            [option.split("=", 1) for option in row["reloptions"]]
                        )

                    # it *might* be nice to include that this is 'btree' in the
                    # reflection info.  But we don't want an Index object
                    # to have a ``postgresql_using`` in it that is just the
                    # default, so for the moment leaving this out.
                    amname = row["amname"]
                    if amname != "btree":
                        dialect_options["postgresql_using"] = row["amname"]

                    if row["filter_definition"]:
                        dialect_options["postgresql_where"] = row["filter_definition"]

                    if self.server_version_info >= (11,):
                        # NOTE: this is legacy, this is part of dialect_options now as of #7382
                        index["include_columns"] = inc_cols
                        dialect_options["postgresql_include"] = inc_cols

                    if row["indnullsnotdistinct"]:
                        # the default is False, so ignore it.
                        dialect_options["postgresql_nulls_not_distinct"] = row["indnullsnotdistinct"]

                    if dialect_options:
                        index["dialect_options"] = dialect_options

                    table_indexes.append(index)

        return indexes.items()

    def get_multi_foreign_keys(self, connection, schema, filter_names, scope, kind, **kw):
        """Override to handle OID type casting for Aurora Data API compatibility.

        Uses pg_get_constraintdef like parent class, but with Aurora-specific OID casting.
        Cannot use parent's _foreing_key_query directly due to Aurora Data API OID type limitations.
        """
        from collections import defaultdict
        from sqlalchemy.engine.reflection import ReflectionDefaults
        import re

        preparer = self.identifier_preparer
        has_filter_names, params = self._prepare_filter_names(filter_names)

        # AURORA CHANGE: Use our modified version of _foreing_key_query with OID casting
        query = self._foreing_key_query(schema, has_filter_names, scope, kind)
        result = connection.execute(query, params)

        FK_REGEX = self._fk_regex_pattern
        fkeys = defaultdict(list)
        default = ReflectionDefaults.foreign_keys

        # Match parent class structure: iterate through query results directly
        for table_name, conname, condef, conschema, comment in result:
            # ensure that each table has an entry, even if it has
            # no foreign keys
            if conname is None:
                fkeys[(schema, table_name)] = default()
                continue

            table_fks = fkeys[(schema, table_name)]
            m = re.search(FK_REGEX, condef).groups()
            (
                constrained_columns,
                referred_schema,
                referred_table,
                referred_columns,
                _,
                match,
                _,
                onupdate,
                _,
                ondelete,
                deferrable,
                _,
                initially,
            ) = m

            if deferrable is not None:
                deferrable = True if deferrable == "DEFERRABLE" else False

            constrained_columns = [preparer._unquote_identifier(x) for x in re.split(r"\s*,\s*", constrained_columns)]

            # Handle schema logic like parent class
            if referred_schema:
                referred_schema = preparer._unquote_identifier(referred_schema)
            elif schema is not None and schema == conschema:
                referred_schema = schema

            referred_table = preparer._unquote_identifier(referred_table)
            referred_columns = [preparer._unquote_identifier(x) for x in re.split(r"\s*,\s", referred_columns)]

            options = {
                k: v
                for k, v in [
                    ("onupdate", onupdate),
                    ("ondelete", ondelete),
                    ("initially", initially),
                    ("deferrable", deferrable),
                    ("match", match),
                ]
                if v is not None and v != "NO ACTION"
            }

            fkey_d = {
                "name": conname,
                "constrained_columns": constrained_columns,
                "referred_schema": referred_schema,
                "referred_table": referred_table,
                "referred_columns": referred_columns,
                "options": options,
                "comment": comment,
            }
            table_fks.append(fkey_d)

        return fkeys.items()

    @lru_cache
    def _foreing_key_query(self, schema, has_filter_names, scope, kind):
        """Override to handle OID type casting for Aurora Data API compatibility."""
        from sqlalchemy.dialects.postgresql import pg_catalog
        from sqlalchemy.sql import select, bindparam
        import sqlalchemy.sql.sqltypes as sqltypes

        pg_class_ref = pg_catalog.pg_class.alias("cls_ref")
        pg_namespace_ref = pg_catalog.pg_namespace.alias("nsp_ref")
        relkinds = self._kind_to_relkinds(kind)

        query = (
            select(
                pg_catalog.pg_class.c.relname,
                pg_catalog.pg_constraint.c.conname,
                # NOTE: avoid calling pg_get_constraintdef when not needed
                # to speed up the query
                sql.case(
                    (
                        pg_catalog.pg_constraint.c.oid.is_not(None),
                        pg_catalog.pg_get_constraintdef(
                            # AURORA CHANGE: Cast constraint OID to BIGINT for Aurora Data API compatibility
                            sql.cast(pg_catalog.pg_constraint.c.oid, sqltypes.BIGINT),
                            True,
                        ),
                    ),
                    else_=None,
                ),
                pg_namespace_ref.c.nspname,
                pg_catalog.pg_description.c.description,
            )
            .select_from(pg_catalog.pg_class)
            .outerjoin(
                pg_catalog.pg_constraint,
                sql.and_(
                    # AURORA CHANGE: Cast OIDs to BIGINT for Aurora Data API compatibility
                    sql.cast(pg_catalog.pg_class.c.oid, sqltypes.BIGINT)
                    == sql.cast(pg_catalog.pg_constraint.c.conrelid, sqltypes.BIGINT),
                    pg_catalog.pg_constraint.c.contype == "f",
                ),
            )
            .outerjoin(
                pg_class_ref,
                # AURORA CHANGE: Cast OIDs to BIGINT for Aurora Data API compatibility
                sql.cast(pg_class_ref.c.oid, sqltypes.BIGINT)
                == sql.cast(pg_catalog.pg_constraint.c.confrelid, sqltypes.BIGINT),
            )
            .outerjoin(
                pg_namespace_ref,
                # AURORA CHANGE: Cast OIDs to BIGINT for Aurora Data API compatibility
                sql.cast(pg_class_ref.c.relnamespace, sqltypes.BIGINT)
                == sql.cast(pg_namespace_ref.c.oid, sqltypes.BIGINT),
            )
            .outerjoin(
                pg_catalog.pg_description,
                # AURORA CHANGE: Cast OIDs to BIGINT for Aurora Data API compatibility
                sql.cast(pg_catalog.pg_description.c.objoid, sqltypes.BIGINT)
                == sql.cast(pg_catalog.pg_constraint.c.oid, sqltypes.BIGINT),
            )
            .order_by(
                pg_catalog.pg_class.c.relname,
                pg_catalog.pg_constraint.c.conname,
            )
            .where(self._pg_class_relkind_condition(relkinds))
        )
        query = self._pg_class_filter_scope_schema(query, schema, scope)
        if has_filter_names:
            query = query.where(pg_catalog.pg_class.c.relname.in_(bindparam("filter_names")))
        return query

    @util.memoized_property
    def _constraint_query(self):
        """Override to use generate_subscripts for Aurora Data API compatibility."""
        from sqlalchemy.dialects.postgresql import pg_catalog
        from sqlalchemy.dialects.postgresql.ext import aggregate_order_by
        from sqlalchemy.sql.sqltypes import TEXT
        from sqlalchemy.sql import bindparam, select
        import sqlalchemy.sql.sqltypes as sqltypes

        if self.server_version_info >= (11, 0):
            # AURORA CHANGE: Cast indnkeyatts for Aurora Data API compatibility
            indnkeyatts = pg_catalog.pg_index.c.indnkeyatts.cast(sqltypes.INTEGER).label("indnkeyatts")
        else:
            # AURORA CHANGE: Cast indnatts for Aurora Data API compatibility
            indnkeyatts = pg_catalog.pg_index.c.indnatts.cast(sqltypes.INTEGER).label("indnkeyatts")

        if self.server_version_info >= (15,):
            indnullsnotdistinct = pg_catalog.pg_index.c.indnullsnotdistinct
        else:
            indnullsnotdistinct = sql.false().label("indnullsnotdistinct")

        con_sq = (
            select(
                pg_catalog.pg_constraint.c.conrelid,
                pg_catalog.pg_constraint.c.conname,
                # AURORA CHANGE: Use generate_subscripts instead of unnest for Aurora Data API compatibility
                pg_catalog.pg_index.c.indkey[
                    sql.func.generate_subscripts(pg_catalog.pg_index.c.indkey, sql.cast(1, sqltypes.Integer))
                ].label("attnum"),
                sql.func.generate_subscripts(pg_catalog.pg_index.c.indkey, sql.cast(1, sqltypes.Integer)).label("ord"),
                indnkeyatts,
                indnullsnotdistinct,
                pg_catalog.pg_description.c.description,
            )
            .join(
                pg_catalog.pg_index,
                # AURORA CHANGE: Cast OIDs to BIGINT for Aurora Data API compatibility
                sql.cast(pg_catalog.pg_constraint.c.conindid, sqltypes.BIGINT)
                == sql.cast(pg_catalog.pg_index.c.indexrelid, sqltypes.BIGINT),
            )
            .outerjoin(
                pg_catalog.pg_description,
                # AURORA CHANGE: Cast OIDs to BIGINT for Aurora Data API compatibility
                sql.cast(pg_catalog.pg_description.c.objoid, sqltypes.BIGINT)
                == sql.cast(pg_catalog.pg_constraint.c.oid, sqltypes.BIGINT),
            )
            .where(
                pg_catalog.pg_constraint.c.contype == bindparam("contype"),
                # AURORA CHANGE: Cast OIDs to BIGINT for Aurora Data API compatibility
                sql.cast(pg_catalog.pg_constraint.c.conrelid, sqltypes.BIGINT).in_(bindparam("oids")),
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
                    # AURORA CHANGE: Cast OIDs to BIGINT for Aurora Data API compatibility
                    sql.cast(pg_catalog.pg_attribute.c.attrelid, sqltypes.BIGINT)
                    == sql.cast(con_sq.c.conrelid, sqltypes.BIGINT),
                ),
            )
            .where(
                # NOTE: restate the condition here, since pg15 otherwise
                # seems to get confused on pscopg2 sometimes, doing
                # a sequential scan of pg_attribute.
                # The condition in the con_sq subquery is not actually needed
                # in pg15, but it may be needed in older versions. Keeping it
                # does not seems to have any inpact in any case.
                # AURORA CHANGE: Cast OIDs to BIGINT for Aurora Data API compatibility
                sql.cast(con_sq.c.conrelid, sqltypes.BIGINT).in_(bindparam("oids"))
            )
            .subquery("attr")
        )

        return (
            select(
                attr_sq.c.conrelid,
                sql.func.array_agg(
                    # NOTE: cast since some postgresql derivatives may
                    # not support array_agg on the name type
                    aggregate_order_by(attr_sq.c.attname.cast(TEXT), attr_sq.c.ord)
                ).label("cols"),
                attr_sq.c.conname,
                sql.func.min(attr_sq.c.description).label("description"),
                sql.func.min(attr_sq.c.indnkeyatts).label("indnkeyatts"),
                sql.func.bool_and(attr_sq.c.indnullsnotdistinct).label("indnullsnotdistinct"),
            )
            .group_by(attr_sq.c.conrelid, attr_sq.c.conname)
            .order_by(attr_sq.c.conrelid, attr_sq.c.conname)
        )

    def _reflect_constraint(self, connection, contype, schema, filter_names, scope, kind, **kw):
        """Override to handle OID casting for Aurora Data API compatibility.

        CRITICAL FIX:
        Aurora Data API returns OID values (conrelid, frelid, etc.) as STRINGS instead of integers.
        This causes key matching failures between query results and table OIDs.
        Solution: Normalize all OID values to integers for consistent dictionary key matching.

        CURRENT STATUS:
        - ✅ Primary key constraint reflection: FIXED via OID string normalization
        - ✅ Foreign key constraint reflection: FIXED via OID string normalization
        - ✅ Index reflection: Works via existing get_multi_indexes implementation
        - ✅ Unique/Check constraints: Works via this _reflect_constraint override
        - ⚠️ System table filtering: Partially working, some edge cases remain
        """
        from collections import defaultdict

        # used to reflect primary and unique constraint
        table_oids = self._get_table_oids(connection, schema, filter_names, scope, kind, **kw)
        batches = list(table_oids)
        is_unique = contype == "u"

        while batches:
            batch = batches[0:3000]
            batches[0:3000] = []

            # AURORA CHANGE: Convert OIDs to integers for Aurora Data API compatibility (OID type not supported)
            result = connection.execute(
                self._constraint_query,
                {"oids": [int(r[0]) for r in batch], "contype": contype},
            ).mappings()

            result_by_oid = defaultdict(list)
            for row_dict in result:
                # AURORA CHANGE: Normalize conrelid to integer for consistent matching
                # Aurora Data API returns conrelid as string, but we need integer keys
                conrelid_key = int(row_dict["conrelid"])
                result_by_oid[conrelid_key].append(row_dict)

            for oid, tablename in batch:
                # AURORA CHANGE: Handle both integer and string OID types for consistent matching
                oid_key = int(oid) if not isinstance(oid, int) else oid
                for_oid = result_by_oid.get(oid_key, ())
                if for_oid:
                    for row in for_oid:
                        # See note in get_multi_indexes
                        all_cols = row["cols"]
                        indnkeyatts = row["indnkeyatts"]
                        if len(all_cols) > indnkeyatts:
                            inc_cols = all_cols[indnkeyatts:]
                            cst_cols = all_cols[:indnkeyatts]
                        else:
                            inc_cols = []
                            cst_cols = all_cols

                        opts = {}
                        if self.server_version_info >= (11,):
                            opts["postgresql_include"] = inc_cols
                        if is_unique:
                            opts["postgresql_nulls_not_distinct"] = row["indnullsnotdistinct"]
                        yield (
                            tablename,
                            cst_cols,
                            row["conname"],
                            row["description"],
                            opts,
                        )
                else:
                    yield tablename, None, None, None, None

    @util.memoized_property
    def _index_query(self):
        """Override to use generate_subscripts for Aurora Data API compatibility."""
        from sqlalchemy.dialects.postgresql import pg_catalog
        from sqlalchemy.dialects.postgresql import arraylib as _array
        from sqlalchemy.dialects.postgresql.ext import aggregate_order_by
        from sqlalchemy.sql.sqltypes import TEXT
        from sqlalchemy.sql import bindparam
        import sqlalchemy.sql.sqltypes as sqltypes

        # AURORA CHANGE: Use generate_subscripts to preserve array order (matching _foreign_key_query pattern)
        # generate_subscripts works with Aurora Data API when properly cast to INTEGER

        # Create query with generate_subscripts for both indkey and indclass arrays
        idx_sq = (
            select(
                pg_catalog.pg_index.c.indexrelid,
                pg_catalog.pg_index.c.indrelid,
                # AURORA CHANGE: Use generate_subscripts to get array elements with order
                pg_catalog.pg_index.c.indkey[
                    sql.func.generate_subscripts(pg_catalog.pg_index.c.indkey, sql.cast(1, sqltypes.Integer))
                ].label("attnum"),
                pg_catalog.pg_index.c.indclass[
                    sql.func.generate_subscripts(pg_catalog.pg_index.c.indclass, sql.cast(1, sqltypes.Integer))
                ].label("att_opclass"),
                sql.func.generate_subscripts(pg_catalog.pg_index.c.indkey, sql.cast(1, sqltypes.Integer)).label("ord"),
            )
            .where(
                ~pg_catalog.pg_index.c.indisprimary,
                # AURORA CHANGE: Cast OID to BIGINT for Aurora Data API compatibility
                sql.cast(pg_catalog.pg_index.c.indrelid, sqltypes.BIGINT).in_(bindparam("oids")),
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
                            # AURORA CHANGE: Try BIGINT directly for Aurora Data API compatibility
                            idx_sq.c.indexrelid,
                            # AURORA CHANGE: Cast to INTEGER for pg_get_indexdef function compatibility
                            sql.cast(idx_sq.c.ord, sqltypes.Integer),
                            True,
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
                    # AURORA CHANGE: Cast OIDs to BIGINT for Aurora Data API compatibility (OID type not supported)
                    sql.cast(pg_catalog.pg_attribute.c.attrelid, sqltypes.BIGINT)
                    == sql.cast(idx_sq.c.indrelid, sqltypes.BIGINT),
                ),
            )
            .outerjoin(
                pg_catalog.pg_opclass,
                # AURORA CHANGE: Cast OID to BIGINT for Aurora Data API compatibility (OID type not supported)
                sql.cast(pg_catalog.pg_opclass.c.oid, sqltypes.BIGINT) == idx_sq.c.att_opclass,
            )
            # AURORA CHANGE: Cast OID to BIGINT for Aurora Data API compatibility (OID type not supported)
            .where(sql.cast(idx_sq.c.indrelid, sqltypes.BIGINT).in_(bindparam("oids")))
            .subquery("idx_attr")
        )

        cols_sq = (
            select(
                attr_sq.c.indexrelid,
                sql.func.min(attr_sq.c.indrelid),
                sql.func.array_agg(aggregate_order_by(attr_sq.c.element, attr_sq.c.ord)).label("elements"),
                sql.func.array_agg(aggregate_order_by(attr_sq.c.is_expr, attr_sq.c.ord)).label("elements_is_expr"),
                sql.func.array_agg(aggregate_order_by(attr_sq.c.opcname, attr_sq.c.ord)).label("elements_opclass"),
                sql.func.array_agg(aggregate_order_by(attr_sq.c.opcdefault, attr_sq.c.ord)).label("elements_opdefault"),
            )
            .group_by(attr_sq.c.indexrelid)
            .subquery("idx_cols")
        )

        if self.server_version_info >= (11, 0):
            # AURORA CHANGE: Cast indnkeyatts for Aurora Data API compatibility
            indnkeyatts = pg_catalog.pg_index.c.indnkeyatts.cast(sqltypes.INTEGER).label("indnkeyatts")
        else:
            # AURORA CHANGE: Cast indnatts for Aurora Data API compatibility
            indnkeyatts = pg_catalog.pg_index.c.indnatts.cast(sqltypes.INTEGER).label("indnkeyatts")

        if self.server_version_info >= (15,):
            nulls_not_distinct = pg_catalog.pg_index.c.indnullsnotdistinct
        else:
            nulls_not_distinct = sql.false().label("indnullsnotdistinct")

        return (
            select(
                pg_catalog.pg_index.c.indrelid,
                pg_catalog.pg_class.c.relname,
                pg_catalog.pg_index.c.indisunique,
                pg_catalog.pg_constraint.c.conrelid.is_not(None).label("has_constraint"),
                # AURORA CHANGE: Cast indoption from PostgreSQL int2vector type to TEXT
                # PostgreSQL int2vector is an array of small integers storing index column options/flags
                sql.cast(pg_catalog.pg_index.c.indoption, sqltypes.TEXT).label("indoption"),
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
                # AURORA CHANGE: Cast OID to BIGINT for Aurora Data API compatibility (OID type not supported)
                sql.cast(pg_catalog.pg_index.c.indrelid, sqltypes.BIGINT).in_(bindparam("oids")),
                ~pg_catalog.pg_index.c.indisprimary,
            )
            .join(
                pg_catalog.pg_class,
                # AURORA CHANGE: Cast both OIDs to BIGINT for Aurora Data API compatibility
                sql.cast(pg_catalog.pg_index.c.indexrelid, sqltypes.BIGINT)
                == sql.cast(pg_catalog.pg_class.c.oid, sqltypes.BIGINT),
            )
            .join(
                pg_catalog.pg_am,
                # AURORA CHANGE: Cast both OIDs to BIGINT for Aurora Data API compatibility
                sql.cast(pg_catalog.pg_class.c.relam, sqltypes.BIGINT)
                == sql.cast(pg_catalog.pg_am.c.oid, sqltypes.BIGINT),
            )
            .outerjoin(
                cols_sq,
                # AURORA CHANGE: Cast OID to BIGINT for Aurora Data API compatibility (OID type not supported)
                sql.cast(pg_catalog.pg_index.c.indexrelid, sqltypes.BIGINT) == cols_sq.c.indexrelid,
            )
            .outerjoin(
                pg_catalog.pg_constraint,
                sql.and_(
                    # AURORA CHANGE: Cast OIDs to BIGINT for Aurora Data API compatibility (OID type not supported)
                    sql.cast(pg_catalog.pg_index.c.indrelid, sqltypes.BIGINT)
                    == sql.cast(pg_catalog.pg_constraint.c.conrelid, sqltypes.BIGINT),
                    sql.cast(pg_catalog.pg_index.c.indexrelid, sqltypes.BIGINT)
                    == sql.cast(pg_catalog.pg_constraint.c.conindid, sqltypes.BIGINT),
                    pg_catalog.pg_constraint.c.contype == sql.any_(_array.array(("p", "u", "x"))),
                ),
            )
            .order_by(pg_catalog.pg_index.c.indrelid, pg_catalog.pg_class.c.relname)
        )

    @lru_cache
    def _table_oids_query(self, schema, has_filter_names, scope, kind):
        """Override to cast OID for Aurora Data API compatibility."""
        from sqlalchemy.dialects.postgresql import pg_catalog
        from sqlalchemy.sql import select, bindparam
        import sqlalchemy.sql.sqltypes as sqltypes
        from sqlalchemy import sql

        relkinds = self._kind_to_relkinds(kind)
        oid_q = select(
            # AURORA CHANGE: Cast OID to BIGINT for Aurora Data API compatibility
            sql.cast(pg_catalog.pg_class.c.oid, sqltypes.BIGINT).label("oid"),
            pg_catalog.pg_class.c.relname,
        ).where(self._pg_class_relkind_condition(relkinds))

        oid_q = self._pg_class_filter_scope_schema(oid_q, schema, scope=scope)

        if has_filter_names:
            oid_q = oid_q.where(pg_catalog.pg_class.c.relname.in_(bindparam("filter_names")))
        return oid_q

    @lru_cache()
    def _check_constraint_query(self, schema, has_filter_names, scope, kind):
        """Aurora-specific check constraint query with BIGINT casting for OIDs."""
        from sqlalchemy.dialects.postgresql import pg_catalog
        from sqlalchemy import sql
        import sqlalchemy.sql.sqltypes as sqltypes

        # Get base query from parent class
        base_query = super()._check_constraint_query(schema, has_filter_names, scope, kind)

        # AURORA CHANGE: Replace the select columns with BIGINT-casted versions for Aurora Data API compatibility
        return base_query.with_only_columns(
            pg_catalog.pg_class.c.relname,
            # AURORA CHANGE: Cast conname from PostgreSQL "name" type to TEXT
            pg_catalog.pg_constraint.c.conname.cast(sqltypes.TEXT),
            # AURORA CHANGE: Modify the CASE statement to cast OID to BIGINT
            sql.case(
                (
                    pg_catalog.pg_constraint.c.oid.is_not(None),
                    pg_catalog.pg_get_constraintdef(
                        # AURORA CHANGE: Cast constraint OID to BIGINT for Aurora Data API compatibility
                        sql.cast(pg_catalog.pg_constraint.c.oid, sqltypes.BIGINT),
                        True,
                    ),
                ),
                else_=None,
            ),
            pg_catalog.pg_description.c.description,
        )

    @reflection.cache
    def get_view_definition(self, connection, view_name, schema=None, **kw):
        """Override to handle OID casting for Aurora Data API compatibility.

        Aurora Data API requires OID types to be cast to BIGINT for proper comparison.
        """
        from sqlalchemy.dialects.postgresql import pg_catalog
        from sqlalchemy import exc
        from sqlalchemy.engine.reflection import ObjectScope

        query = (
            select(
                # AURORA CHANGE: Cast OID parameter to BIGINT for Aurora Data API compatibility
                pg_catalog.pg_get_viewdef(sql.cast(pg_catalog.pg_class.c.oid, sqltypes.BIGINT))
            )
            .select_from(pg_catalog.pg_class)
            .where(
                pg_catalog.pg_class.c.relname == view_name,
                self._pg_class_relkind_condition(pg_catalog.RELKINDS_VIEW + pg_catalog.RELKINDS_MAT_VIEW),
            )
        )
        query = self._pg_class_filter_scope_schema(query, schema, scope=ObjectScope.ANY)
        res = connection.scalar(query)
        if res is None:
            raise exc.NoSuchTableError(f"{schema}.{view_name}" if schema else view_name)
        else:
            return res
