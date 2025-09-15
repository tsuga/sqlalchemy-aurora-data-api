from sqlalchemy import util
import sqlalchemy.sql.sqltypes as sqltypes
from sqlalchemy.dialects.postgresql.base import PGDialect, PGInspector
from sqlalchemy.dialects.postgresql import JSON, JSONB, UUID, ARRAY
from sqlalchemy.dialects.mysql.base import MySQLDialect
from .base import (
    _ADA_ARRAY,
    _ADA_DATE,
    _ADA_SA_JSON,
    _ADA_JSON,
    _ADA_JSONB,
    _ADA_TIME,
    _ADA_TIMESTAMP,
    _ADA_UUID,
    _ADA_ENUM,
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


class AuroraPostgresDataAPIInspector(PGInspector):
    pass


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
            sqltypes.Date: _ADA_DATE,
            sqltypes.Time: _ADA_TIME,
            sqltypes.DateTime: _ADA_TIMESTAMP,
            sqltypes.Enum: _ADA_ENUM,
            ARRAY: _ADA_ARRAY,
        },
    )
    supports_sane_multi_rowcount = False
    supports_statement_cache = True
    inspector = AuroraPostgresDataAPIInspector

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
        opts.pop("host", None)
        opts.pop("port", None)
        opts.pop("user", None)
        opts.pop("password", None)

        return [], connect_args

    @classmethod
    def load_provisioning(cls):
        """Load provisioning hooks for Aurora dialect testing."""
        __import__("sqlalchemy_aurora_data_api.provision")
