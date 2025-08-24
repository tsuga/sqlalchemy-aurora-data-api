"""
sqlalchemy-aurora-data-api
"""

from .sync import AuroraMySQLDataAPIDialect, AuroraPostgresDataAPIDialect
from .async_ import AsyncAuroraMySQLDataAPIDialect, AsyncAuroraPostgresDataAPIDialect

# compatibility export
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


def register_dialects():
    from sqlalchemy.dialects import registry

    # Sync dialects
    registry.register("mysql.auroradataapi", __name__, AuroraMySQLDataAPIDialect.__name__)
    registry.register("postgresql.auroradataapi", __name__, AuroraPostgresDataAPIDialect.__name__)

    # Async dialects
    registry.register("mysql.auroradataapiasync", __name__, AsyncAuroraMySQLDataAPIDialect.__name__)
    registry.register("postgresql.auroradataapiasync", __name__, AsyncAuroraPostgresDataAPIDialect.__name__)
