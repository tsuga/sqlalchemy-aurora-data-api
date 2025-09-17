from sqlalchemy import select, util, sql, exc as sqlalchemy_exc
import sqlalchemy.sql.sqltypes as sqltypes
from sqlalchemy.dialects.postgresql.base import PGDialect
from sqlalchemy.dialects.postgresql import JSON, JSONB, UUID, ARRAY
from sqlalchemy.dialects.mysql.base import MySQLDialect
from sqlalchemy.util import memoized_property
from sqlalchemy.engine import reflection

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

    # AURORA CHANGE: Enable name normalization for consistent identifier handling
    # Aurora Data API may return identifiers with inconsistent casing
    requires_name_normalize = True


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
                # AURORA CHANGE: Cast relname from PostgreSQL "name" type to TEXT for sorting compatibility
                # PostgreSQL "name" type may not sort properly when mixed with other string types
                pg_catalog.pg_class.c.relname.cast(TEXT),
                pg_catalog.pg_attribute.c.attnum
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
            if text.startswith('{') and text.endswith('}'):
                text = text[1:-1]
                # Split by comma for array format
                parts = [x.strip() for x in text.split(',') if x.strip()]
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
        if not expression:
            return expression

        # Remove ::text, ::character varying, and similar type casts commonly added by Aurora
        import re
        # Pattern to match ::type_name (including variations like ::character varying)
        pattern = r'::[a-zA-Z_][a-zA-Z0-9_]*(?:\s+[a-zA-Z_][a-zA-Z0-9_]*)*(?:\([^)]*\))?'
        cleaned = re.sub(pattern, '', expression)

        return cleaned.strip()

    def get_multi_indexes(self, connection, schema, filter_names, scope, kind, **kw):
        """Override to handle indoption TEXT conversion for Aurora Data API."""
        from collections import defaultdict
        from sqlalchemy.engine.reflection import ReflectionDefaults

        table_oids = self._get_table_oids(
            connection, schema, filter_names, scope, kind, **kw
        )

        indexes = defaultdict(list)
        default = ReflectionDefaults.indexes

        batches = list(table_oids)

        while batches:
            batch = batches[0:3000]
            batches[0:3000] = []

            # AURORA CHANGE: Convert OIDs to integers for Aurora Data API compatibility (OID type not supported)
            oids_param = [int(r[0]) for r in batch]

            result = connection.execute(
                self._index_query, {"oids": oids_param}
            ).mappings()


            result_by_oid = defaultdict(list)
            for row_dict in result:
                # AURORA CHANGE: Normalize indrelid to integer for consistent matching
                # Aurora Data API returns indrelid as string, but we need integer keys
                indrelid_key = int(row_dict["indrelid"])
                result_by_oid[indrelid_key].append(row_dict)

            for oid, table_name in batch:
                # AURORA CHANGE: Handle both integer and string OID types for consistent matching
                oid_key = int(oid) if not isinstance(oid, int) else oid
                if oid_key not in result_by_oid:
                    indexes[(schema, table_name)] = default()
                    continue

                for row in result_by_oid[oid_key]:
                    index_name = row["relname"]
                    table_indexes = indexes[(schema, table_name)]

                    # Process the index data (copying from parent implementation)
                    all_elements = row["elements"]
                    all_elements_is_expr = row["elements_is_expr"]
                    # Note: opclass and opdefault processing removed for Aurora Data API simplicity
                    # all_elements_opclass = row["elements_opclass"] - not used in this implementation
                    # all_elements_opdefault = row["elements_opdefault"] - not used in this implementation
                    indnkeyatts = row["indnkeyatts"]

                    if len(all_elements) > indnkeyatts:
                        inc_cols = all_elements[indnkeyatts:]
                        idx_elements = all_elements[:indnkeyatts]
                        idx_elements_is_expr = all_elements_is_expr[:indnkeyatts]
                    else:
                        inc_cols = None
                        idx_elements = all_elements
                        idx_elements_is_expr = all_elements_is_expr

                    index = {
                        "name": index_name,
                        "column_names": [
                            None if is_expr else name
                            for name, is_expr in zip(idx_elements, idx_elements_is_expr)
                        ],
                        "unique": row["indisunique"],
                    }

                    # Only include 'expressions' field if there are actual expressions (not just regular columns)
                    if any(idx_elements_is_expr):
                        expressions_list = [
                            # AURORA CHANGE: For expression indexes, clean the expression output
                            # For regular columns, use the column name directly
                            self._clean_expression_output(name) if is_expr else name
                            for name, is_expr in zip(idx_elements, idx_elements_is_expr)
                        ]
                        index["expressions"] = expressions_list

                    dialect_options = {}

                    # Always include include_columns and postgresql_include for PostgreSQL compatibility
                    if inc_cols:
                        index["include_columns"] = inc_cols
                        dialect_options["postgresql_include"] = inc_cols
                    else:
                        # Even when no include columns, add empty arrays for test compatibility
                        index["include_columns"] = []
                        dialect_options["postgresql_include"] = []

                    if row["filter_definition"]:
                        dialect_options["postgresql_where"] = row["filter_definition"]

                    if self.server_version_info >= (15,) and row["indnullsnotdistinct"]:
                        dialect_options["postgresql_nulls_not_distinct"] = True

                    # Note: opclass processing removed for simplicity in Aurora Data API implementation

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
                            [
                                option.split("=", 1) if "=" in option else (option, True)
                                for option in row["reloptions"]
                            ]
                        )

                    if dialect_options:
                        index["dialect_options"] = dialect_options

                    table_indexes.append(index)

        return indexes


    def get_foreign_keys(self, connection, table_name, schema=None, **kw):
        """Override to handle OID type casting for Aurora Data API compatibility."""
        from sqlalchemy.engine.reflection import ObjectScope, ObjectKind
        return self.get_multi_foreign_keys(
            connection, schema, [table_name], scope=ObjectScope.DEFAULT,
            kind=ObjectKind.TABLE, **kw
        )[(schema, table_name)]

    def get_multi_foreign_keys(self, connection, schema, filter_names, scope, kind, **kw):
        """Override to handle OID type casting for Aurora Data API compatibility."""
        from collections import defaultdict
        from sqlalchemy.engine.reflection import ReflectionDefaults

        table_oids = self._get_table_oids(
            connection, schema, filter_names, scope, kind, **kw
        )

        fkeys = defaultdict(list)
        default = ReflectionDefaults.foreign_keys

        batches = list(table_oids)

        while batches:
            batch = batches[0:3000]
            batches[0:3000] = []

            # AURORA CHANGE: Convert OIDs to integers for Aurora Data API compatibility (OID type not supported)
            result = connection.execute(
                self._foreign_key_query, {"oids": [int(r[0]) for r in batch]}
            ).mappings()

            fkey_d = defaultdict(lambda: defaultdict(list))
            for row in result:
                # AURORA CHANGE: Normalize frelid to integer for consistent matching
                # Aurora Data API returns frelid as string, but we need integer keys
                frelid_key = int(row["frelid"]) if isinstance(row["frelid"], str) else row["frelid"]
                fkey_d[frelid_key][row["conname"]].append(row)

            for oid, table_name in batch:
                # AURORA CHANGE: Normalize oid to integer for consistent matching
                oid_key = int(oid) if not isinstance(oid, int) else oid
                if oid_key not in fkey_d:
                    fkeys[(schema, table_name)] = default()
                    continue

                table_fkeys = fkeys[(schema, table_name)]

                for conname, rows in fkey_d[oid_key].items():
                    # AURORA CHANGE: Add defensive check for empty rows to prevent IndexError
                    if not rows:
                        continue
                    referred_schema = rows[0]["referred_schema"]
                    referred_table = rows[0]["referred_table"]
                    constrained_columns = [r["constrained_column"] for r in rows]
                    referred_columns = [r["referred_column"] for r in rows]

                    constraint = {
                        "name": conname,
                        "constrained_columns": constrained_columns,
                        "referred_schema": referred_schema,
                        "referred_table": referred_table,
                        "referred_columns": referred_columns,
                    }

                    # AURORA CHANGE: Always include options for test compatibility
                    # Convert PostgreSQL char codes to readable action names
                    # 'a'=no action, 'r'=restrict, 'c'=cascade, 'n'=set null, 'd'=set default
                    action_map = {
                        'a': 'NO ACTION',
                        'r': 'RESTRICT',
                        'c': 'CASCADE',
                        'n': 'SET NULL',
                        'd': 'SET DEFAULT'
                    }

                    options = {}
                    if rows[0]["confupdtype"]:
                        upd_action = action_map.get(rows[0]["confupdtype"], rows[0]["confupdtype"])
                        del_action = action_map.get(rows[0]["confdeltype"], rows[0]["confdeltype"])

                        # Only include non-default actions in options
                        if upd_action != 'NO ACTION':
                            options["onupdate"] = upd_action
                        if del_action != 'NO ACTION':
                            options["ondelete"] = del_action

                    # Always include options key, even if empty
                    constraint["options"] = options

                    table_fkeys.append(constraint)

        return fkeys

    @util.memoized_property
    def _foreign_key_query(self):
        """Override to handle OID type casting and unnest() for Aurora Data API compatibility."""
        from sqlalchemy.dialects.postgresql import pg_catalog
        from sqlalchemy.sql.sqltypes import TEXT
        from sqlalchemy.sql import bindparam
        import sqlalchemy.sql.sqltypes as sqltypes

        # Create aliases for joined tables
        pg_class_2 = pg_catalog.pg_class.alias("pg_class_2")
        pg_attribute_2 = pg_catalog.pg_attribute.alias("pg_attribute_2")
        pg_namespace_2 = pg_catalog.pg_namespace.alias("pg_namespace_2")

        # AURORA CHANGE: Use subqueries with unnest in SELECT instead of JOIN conditions
        # This avoids "set-returning functions are not allowed in JOIN conditions" error

        # First subquery: unnest conkey and confkey to get column pairs
        conkey_sq = (
            select(
                pg_catalog.pg_constraint.c.oid.label("con_oid"),
                pg_catalog.pg_constraint.c.conrelid,
                pg_catalog.pg_constraint.c.conname,
                pg_catalog.pg_constraint.c.confrelid,
                # AURORA CHANGE: Cast confupdtype from PostgreSQL "char" type to TEXT
                # PostgreSQL "char" stores foreign key update action ('a'=no action, 'r'=restrict, 'c'=cascade, 'n'=set null, 'd'=set default)
                sql.cast(pg_catalog.pg_constraint.c.confupdtype, sqltypes.TEXT).label("confupdtype"),
                # AURORA CHANGE: Cast confdeltype from PostgreSQL "char" type to TEXT
                # PostgreSQL "char" stores foreign key delete action ('a'=no action, 'r'=restrict, 'c'=cascade, 'n'=set null, 'd'=set default)
                sql.cast(pg_catalog.pg_constraint.c.confdeltype, sqltypes.TEXT).label("confdeltype"),
                sql.func.unnest(pg_catalog.pg_constraint.c.conkey).label("conkey_elem"),
                sql.func.unnest(pg_catalog.pg_constraint.c.confkey).label("confkey_elem"),
                # AURORA CHANGE: Use row_number to maintain unnest() order for foreign key columns
                sql.func.row_number().over(
                    partition_by=[pg_catalog.pg_constraint.c.oid]
                    # Note: No ORDER BY to preserve unnest() natural order
                ).label("ord"),
            )
            .where(
                pg_catalog.pg_constraint.c.contype == "f",
                # AURORA CHANGE: Cast OID to BIGINT for Aurora Data API compatibility (OID type not supported)
                sql.cast(pg_catalog.pg_constraint.c.conrelid, sqltypes.BIGINT).in_(bindparam("oids")),
            )
            .subquery("conkey_sq")
        )

        # Second subquery: join with pg_attribute to get constrained column names
        constrained_cols = (
            select(
                conkey_sq.c.con_oid,
                conkey_sq.c.conrelid,
                conkey_sq.c.conname,
                conkey_sq.c.confrelid,
                conkey_sq.c.confupdtype,
                conkey_sq.c.confdeltype,
                conkey_sq.c.confkey_elem,
                conkey_sq.c.ord,
                # AURORA CHANGE: Cast name type to TEXT
                pg_catalog.pg_attribute.c.attname.cast(TEXT).label("constrained_column"),
            )
            .select_from(conkey_sq)
            .join(
                pg_catalog.pg_attribute,
                sql.and_(
                    # AURORA CHANGE: Cast OIDs for comparison
                    sql.cast(pg_catalog.pg_attribute.c.attrelid, sqltypes.BIGINT) == sql.cast(conkey_sq.c.conrelid, sqltypes.BIGINT),
                    pg_catalog.pg_attribute.c.attnum == conkey_sq.c.conkey_elem,
                ),
            )
            .subquery("constrained_cols")
        )

        # Final query: join with referred table and columns
        return (
            select(
                # AURORA CHANGE: Cast OID to TEXT for result
                sql.cast(constrained_cols.c.conrelid, sqltypes.TEXT).label("frelid"),
                constrained_cols.c.conname,
                constrained_cols.c.constrained_column,
                # AURORA CHANGE: Cast name type to TEXT
                pg_class_2.c.relname.cast(TEXT).label("referred_table"),
                # AURORA CHANGE: Cast name type to TEXT
                pg_attribute_2.c.attname.cast(TEXT).label("referred_column"),
                constrained_cols.c.confupdtype,
                constrained_cols.c.confdeltype,
                sql.case(
                    (pg_namespace_2.c.nspname != "public", pg_namespace_2.c.nspname),
                    else_=None,
                ).label("referred_schema"),
            )
            .select_from(constrained_cols)
            .join(
                pg_class_2,
                # AURORA CHANGE: Cast OIDs for comparison
                sql.cast(constrained_cols.c.confrelid, sqltypes.BIGINT) == sql.cast(pg_class_2.c.oid, sqltypes.BIGINT),
            )
            .join(
                pg_attribute_2,
                sql.and_(
                    # AURORA CHANGE: Cast OIDs for comparison
                    sql.cast(pg_attribute_2.c.attrelid, sqltypes.BIGINT) == sql.cast(constrained_cols.c.confrelid, sqltypes.BIGINT),
                    pg_attribute_2.c.attnum == constrained_cols.c.confkey_elem,
                ),
            )
            .join(
                pg_namespace_2,
                # AURORA CHANGE: Cast OIDs for comparison
                sql.cast(pg_class_2.c.relnamespace, sqltypes.BIGINT) == sql.cast(pg_namespace_2.c.oid, sqltypes.BIGINT),
            )
            .order_by(
                constrained_cols.c.conrelid,
                constrained_cols.c.conname,
                constrained_cols.c.ord,
            )
        )

    @util.memoized_property
    def _constraint_query(self):
        """Override to replace generate_subscripts with row_number() for Aurora Data API compatibility."""
        from sqlalchemy.dialects.postgresql import pg_catalog
        from sqlalchemy.dialects.postgresql.ext import aggregate_order_by
        from sqlalchemy.sql.sqltypes import TEXT
        from sqlalchemy.sql import bindparam

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

        # AURORA CHANGE: Replaced generate_subscripts with row_number() window function
        # because generate_subscripts is not supported by Aurora Data API
        # Original: sql.func.generate_subscripts(pg_catalog.pg_index.c.indkey, 1).label("ord")

        # AURORA CHANGE: Use LATERAL JOIN with unnest WITH ORDINALITY to preserve array order
        # This replaces generate_subscripts functionality
        con_sq = (
            select(
                pg_catalog.pg_constraint.c.conrelid,
                pg_catalog.pg_constraint.c.conname,
                sql.literal_column("indkey_unnest.attnum").label("attnum"),
                sql.literal_column("indkey_unnest.ord").label("ord"),
                indnkeyatts,
                indnullsnotdistinct,
                pg_catalog.pg_description.c.description,
            )
            .select_from(
                pg_catalog.pg_constraint
                .join(pg_catalog.pg_index,
                    # AURORA CHANGE: Cast OIDs from PostgreSQL oid type to BIGINT for Aurora Data API compatibility
                    sql.cast(pg_catalog.pg_constraint.c.conindid, sqltypes.BIGINT)
                    == sql.cast(pg_catalog.pg_index.c.indexrelid, sqltypes.BIGINT)
                )
                .join(
                    sql.text("LATERAL unnest(pg_catalog.pg_index.indkey) WITH ORDINALITY AS indkey_unnest(attnum, ord)"),
                    sql.text("true")
                )
                .outerjoin(
                    pg_catalog.pg_description,
                    # AURORA CHANGE: Cast OIDs from PostgreSQL oid type to BIGINT for Aurora Data API compatibility
                    sql.cast(pg_catalog.pg_description.c.objoid, sqltypes.BIGINT)
                    == sql.cast(pg_catalog.pg_constraint.c.oid, sqltypes.BIGINT)
                )
            )
            .where(
                # AURORA CHANGE: Cast contype from PostgreSQL "char" type to TEXT
                pg_catalog.pg_constraint.c.contype.cast(sqltypes.TEXT) == bindparam("contype"),
                # AURORA CHANGE: Cast conrelid from PostgreSQL oid type to BIGINT for parameter binding compatibility
                sql.cast(pg_catalog.pg_constraint.c.conrelid, sqltypes.BIGINT).in_(bindparam("oids")),
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
                    sql.cast(pg_catalog.pg_attribute.c.attrelid, sqltypes.BIGINT) == sql.cast(con_sq.c.conrelid, sqltypes.BIGINT),
                ),
            )
            .where(
                # AURORA CHANGE: Cast OID to BIGINT for Aurora Data API compatibility with parameter binding
                sql.cast(con_sq.c.conrelid, sqltypes.BIGINT).in_(bindparam("oids"))
            )
            .subquery("attr")
        )

        final_query = (
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

        return final_query

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
        table_oids = self._get_table_oids(
            connection, schema, filter_names, scope, kind, **kw
        )
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
                            opts["postgresql_nulls_not_distinct"] = row[
                                "indnullsnotdistinct"
                            ]
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
        """Override to replace generate_subscripts with row_number() for Aurora Data API compatibility."""
        from sqlalchemy.dialects.postgresql import pg_catalog
        from sqlalchemy.dialects.postgresql import arraylib as _array
        from sqlalchemy.dialects.postgresql.ext import aggregate_order_by
        from sqlalchemy.sql.sqltypes import TEXT
        from sqlalchemy.sql import bindparam
        import sqlalchemy.sql.sqltypes as sqltypes

        # AURORA CHANGE: Replace generate_subscripts with unnest() WITH ORDINALITY for Aurora Data API compatibility
        # Aurora Data API doesn't support generate_subscripts function
        # Use window functions to maintain proper array element correspondence

        # First, create a base query for indexes
        idx_base = (
            select(
                pg_catalog.pg_index.c.indexrelid,
                pg_catalog.pg_index.c.indrelid,
                pg_catalog.pg_index.c.indkey,
                pg_catalog.pg_index.c.indclass
            )
            .where(
                ~pg_catalog.pg_index.c.indisprimary,
                # AURORA CHANGE: Cast OID to BIGINT for Aurora Data API compatibility
                sql.cast(pg_catalog.pg_index.c.indrelid, sqltypes.BIGINT).in_(bindparam("oids"))
            )
            .subquery("idx_base")
        )

        # Create unnested keys with ordinality
        idx_keys = (
            select(
                idx_base.c.indexrelid,
                idx_base.c.indrelid,
                sql.literal_column("u.key_val").label("attnum"),
                sql.func.row_number().over(
                    partition_by=idx_base.c.indexrelid,
                    order_by=sql.literal_column("u.ordinality")
                ).label("ord")
            )
            .select_from(
                idx_base.join(
                    sql.text("LATERAL unnest(indkey) WITH ORDINALITY AS u(key_val, ordinality)"),
                    sql.text("true")
                )
            )
            .subquery("idx_keys")
        )

        # Create unnested classes with ordinality
        idx_classes = (
            select(
                idx_base.c.indexrelid,
                sql.literal_column("u.class_val").label("att_opclass"),
                sql.func.row_number().over(
                    partition_by=idx_base.c.indexrelid,
                    order_by=sql.literal_column("u.ordinality")
                ).label("ord")
            )
            .select_from(
                idx_base.join(
                    sql.text("LATERAL unnest(indclass) WITH ORDINALITY AS u(class_val, ordinality)"),
                    sql.text("true")
                )
            )
            .subquery("idx_classes")
        )

        # Join keys and classes by index and order
        idx_sq = (
            select(
                idx_keys.c.indexrelid,
                idx_keys.c.indrelid,
                idx_keys.c.attnum,
                idx_classes.c.att_opclass,
                idx_keys.c.ord
            )
            .select_from(
                idx_keys.join(
                    idx_classes,
                    sql.and_(
                        idx_keys.c.indexrelid == idx_classes.c.indexrelid,
                        idx_keys.c.ord == idx_classes.c.ord
                    )
                )
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
                    # AURORA CHANGE: Cast OIDs to BIGINT for Aurora Data API compatibility (OID type not supported)
                    sql.cast(pg_catalog.pg_attribute.c.attrelid, sqltypes.BIGINT) == sql.cast(idx_sq.c.indrelid, sqltypes.BIGINT),
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
                pg_catalog.pg_constraint.c.conrelid.is_not(None).label(
                    "has_constraint"
                ),
                # AURORA CHANGE: Cast indoption from PostgreSQL int2vector type to TEXT
                # PostgreSQL int2vector is an array of small integers storing index column options/flags
                sql.cast(pg_catalog.pg_index.c.indoption, sqltypes.TEXT).label("indoption"),
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
                # AURORA CHANGE: Cast OID to BIGINT for Aurora Data API compatibility (OID type not supported)
                sql.cast(pg_catalog.pg_index.c.indrelid, sqltypes.BIGINT).in_(bindparam("oids")),
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
            .join(
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
                    pg_catalog.pg_constraint.c.contype
                    == sql.any_(_array.array(("p", "u", "x"))),
                ),
            )
            .order_by(
                pg_catalog.pg_index.c.indrelid, pg_catalog.pg_class.c.relname
            )
        )

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
            pg_catalog.pg_class.c.relname
        ).where(self._pg_class_relkind_condition(relkinds))

        oid_q = self._pg_class_filter_scope_schema(oid_q, schema, scope=scope)

        if has_filter_names:
            oid_q = oid_q.where(
                pg_catalog.pg_class.c.relname.in_(bindparam("filter_names"))
            )
        return oid_q

    def get_multi_check_constraints(
        self, connection, schema, filter_names, scope, kind, **kw
    ):
        """Return check constraints for multiple tables."""
        from sqlalchemy.dialects.postgresql import pg_catalog
        from sqlalchemy.sql import bindparam, select
        import sqlalchemy.sql.sqltypes as sqltypes
        from sqlalchemy import sql
        from collections import defaultdict
        from sqlalchemy.engine.reflection import ObjectKind

        table_oids = self._get_table_oids(
            connection, schema, filter_names, scope, kind, **kw
        )

        if not table_oids:
            return {}

        # Views don't have check constraints in PostgreSQL, return empty for views
        if kind in (ObjectKind.VIEW, ObjectKind.MATERIALIZED_VIEW, ObjectKind.ANY_VIEW):
            result_dict = {}
            for oid, table_name in table_oids:
                result_dict[(schema, table_name)] = []
            return result_dict

        # AURORA CHANGE: Cast OIDs and char types for Aurora Data API compatibility
        query = select(
            # AURORA CHANGE: Cast conrelid to BIGINT for Aurora Data API compatibility
            sql.cast(pg_catalog.pg_constraint.c.conrelid, sqltypes.BIGINT).label("relid"),
            # AURORA CHANGE: Cast conname from PostgreSQL "name" type to TEXT
            pg_catalog.pg_constraint.c.conname.cast(sqltypes.TEXT).label("name"),
            pg_catalog.pg_get_constraintdef(
                # AURORA CHANGE: Cast constraint OID to BIGINT for Aurora Data API compatibility
                sql.cast(pg_catalog.pg_constraint.c.oid, sqltypes.BIGINT)
            ).label("source"),
        ).select_from(
            pg_catalog.pg_constraint
        ).where(
            sql.and_(
                # AURORA CHANGE: Cast conrelid to BIGINT for Aurora Data API compatibility
                sql.cast(pg_catalog.pg_constraint.c.conrelid, sqltypes.BIGINT).in_(
                    bindparam("oids")
                ),
                # AURORA CHANGE: Cast contype from PostgreSQL "char" type to TEXT
                # PostgreSQL "char" stores constraint type ('c' = check constraint)
                pg_catalog.pg_constraint.c.contype.cast(sqltypes.TEXT) == "c",
            )
        ).order_by(
            pg_catalog.pg_constraint.c.conrelid,
            pg_catalog.pg_constraint.c.conname
        )

        # AURORA CHANGE: Convert OIDs to integers for Aurora Data API compatibility
        result = connection.execute(
            query, {"oids": [int(oid) for oid, _ in table_oids]}
        ).mappings()

        constraints_by_oid = defaultdict(list)
        for row in result:
            # Extract constraint definition
            constraint_text = row["source"]
            if constraint_text:
                # Remove "CHECK " prefix if present
                if constraint_text.upper().startswith("CHECK "):
                    constraint_text = constraint_text[6:]

                constraints_by_oid[row["relid"]].append({
                    "name": row["name"],
                    "sqltext": constraint_text.strip()
                })

        # Map back to schema, table_name format
        result_dict = {}
        for oid, table_name in table_oids:
            result_dict[(schema, table_name)] = constraints_by_oid.get(int(oid), [])

        return result_dict

    def get_table_options(self, connection, table_name, schema=None, **kw):
        """Return table options for Aurora Data API compatibility.

        Aurora Data API has limited support for PostgreSQL table options.
        Return empty dict to indicate no special options are supported.
        """
        # Suppress unused parameter warnings - parameters required by interface
        _ = connection, table_name, schema, kw
        return {}

    # def get_temp_table_names(self, connection, schema=None, **kw):
    #     """Return temporary table names for Aurora Data API compatibility."""
    #     from sqlalchemy.engine.reflection import ObjectScope

    #     temp_tables = self._get_relnames_for_relkinds(
    #         connection, schema, ["r", "p"], scope=ObjectScope.TEMPORARY
    #     )
    #     return temp_tables

    # def get_temp_view_names(self, connection, schema=None, **kw):
    #     """Return temporary view names for Aurora Data API compatibility."""
    #     from sqlalchemy.engine.reflection import ObjectScope

    #     temp_views = self._get_relnames_for_relkinds(
    #         connection, schema, ["v"], scope=ObjectScope.TEMPORARY
    #     )
    #     return temp_views

    # def _pg_class_filter_scope_schema(
    #     self, query, schema, scope, pg_class_table=None
    # ):
    #     """Override to handle Aurora Data API specific system table filtering.

    #     Aurora Data API may include system tables that should be filtered out.
    #     """
    #     from sqlalchemy.dialects.postgresql import pg_catalog
    #     from sqlalchemy.engine.reflection import ObjectScope
    #     from sqlalchemy import sql

    #     if pg_class_table is None:
    #         pg_class_table = pg_catalog.pg_class
    #     query = query.join(
    #         pg_catalog.pg_namespace,
    #         pg_catalog.pg_namespace.c.oid == pg_class_table.c.relnamespace,
    #     )

    #     if scope is ObjectScope.DEFAULT:
    #         query = query.where(pg_class_table.c.relpersistence != "t")
    #     elif scope is ObjectScope.TEMPORARY:
    #         query = query.where(pg_class_table.c.relpersistence == "t")
    #         # For temporary tables, don't apply the default system table filters
    #         if schema is None:
    #             # For temp tables, only filter by temp schemas
    #             query = query.where(
    #                 sql.or_(
    #                     pg_catalog.pg_namespace.c.nspname.like("pg_temp_%"),
    #                     pg_catalog.pg_namespace.c.nspname == "pg_temp",
    #                     pg_catalog.pg_namespace.c.oid == sql.func.pg_my_temp_schema()
    #                 )
    #             )
    #             return query  # Return early to skip default schema filtering

    #     if schema is None:
    #         # AURORA CHANGE: Enhanced system table filtering for Aurora Data API
    #         # Aurora Data API exposes pg_catalog tables, so we need to filter them out aggressively
    #         # Use pg_table_is_visible() to match PostgreSQL's standard behavior
    #         query = query.where(
    #             # Exclude system schemas entirely
    #             pg_catalog.pg_namespace.c.nspname != "pg_catalog",
    #             pg_catalog.pg_namespace.c.nspname != "information_schema",
    #             ~pg_catalog.pg_namespace.c.nspname.like("pg_temp_%"),
    #             pg_catalog.pg_namespace.c.nspname != "pg_temp",
    #             ~pg_catalog.pg_namespace.c.nspname.like("pg_%"),
    #             # Use pg_table_is_visible for correct visibility filtering
    #             sql.func.pg_table_is_visible(pg_class_table.c.oid),
    #             # Additional system table exclusions
    #             ~pg_class_table.c.relname.like("pg_%"),
    #             ~pg_class_table.c.relname.like("sql_%"),
    #             ~pg_class_table.c.relname.like("information_schema_%"),
    #         )
    #     else:
    #         query = query.where(pg_catalog.pg_namespace.c.nspname == schema)
    #     return query

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
                self._pg_class_relkind_condition(
                    pg_catalog.RELKINDS_VIEW + pg_catalog.RELKINDS_MAT_VIEW
                ),
            )
        )
        query = self._pg_class_filter_scope_schema(
            query, schema, scope=ObjectScope.ANY
        )
        res = connection.scalar(query)
        if res is None:
            raise exc.NoSuchTableError(
                f"{schema}.{view_name}" if schema else view_name
            )
        else:
            return res
