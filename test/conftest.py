from sqlalchemy.dialects import registry

# Register Aurora dialect
registry.register("aurora", "sqlalchemy_aurora_data_api.sync", "AuroraPostgresDataAPIDialect")

# Import pytest and configure
import pytest

# Register assert rewrite - handle warning gracefully
try:
    pytest.register_assert_rewrite("sqlalchemy.testing.assertions")
except Exception:
    pass  # Already registered or not available

# Import SQLAlchemy testing plugin
from sqlalchemy.testing.plugin import pytestplugin
