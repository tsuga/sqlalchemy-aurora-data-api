"""
sqlalchemy-aurora-data-api
"""

from .sync import AuroraMySQLDataAPIDialect, AuroraPostgresDataAPIDialect

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

    registry.register("mysql.auroradataapi", __name__, AuroraMySQLDataAPIDialect.__name__)
    registry.register("postgresql.auroradataapi", __name__, AuroraPostgresDataAPIDialect.__name__)
