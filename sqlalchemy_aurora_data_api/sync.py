from sqlalchemy import select, util, sql, exc as sqlalchemy_exc
import sqlalchemy.sql.sqltypes as sqltypes
from sqlalchemy.dialects.postgresql.base import PGDialect
from sqlalchemy.dialects.postgresql import JSON, JSONB, UUID, ARRAY
from sqlalchemy.dialects.mysql.base import MySQLDialect
from sqlalchemy.util import memoized_property

import re
from .columns_override import _columns_query_override
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
        """Override to cast CHAR/name type columns to TEXT for Aurora Data API compatibility."""
        return _columns_query_override(self, schema, has_filter_names, scope, kind)
