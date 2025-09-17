from .base import (
    BaseADAMySQLDialect,
    BaseADAPGDialect,
)

import aurora_data_api


class AuroraMySQLDataAPIDialect(BaseADAMySQLDialect):
    # See https://docs.sqlalchemy.org/en/13/core/internals.html#sqlalchemy.engine.interfaces.Dialect
    driver = "aurora_data_api"

    @classmethod
    def import_dbapi(cls):
        return aurora_data_api

    @classmethod
    def load_provisioning(cls):
        """Load provisioning hooks for Aurora dialect testing."""
        __import__("sqlalchemy_aurora_data_api.provision")

    def do_execute(self, cursor, statement, parameters, context=None):
        """Override to handle exception mapping."""
        try:
            cursor.execute(statement, parameters)
        except Exception as e:
            transformed_e = self._handle_dbapi_exception(e)
            raise transformed_e from e


class AuroraPostgresDataAPIDialect(BaseADAPGDialect):
    driver = "aurora_data_api"

    @classmethod
    def import_dbapi(cls):
        return aurora_data_api

    @classmethod
    def load_provisioning(cls):
        """Load provisioning hooks for Aurora dialect testing."""
        __import__("sqlalchemy_aurora_data_api.provision")

    def do_execute(self, cursor, statement, parameters, context=None):
        """Override to handle exception mapping."""
        try:
            cursor.execute(statement, parameters)
        except Exception as e:
            transformed_e = self._handle_dbapi_exception(e)
            raise transformed_e from e
