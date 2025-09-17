"""
Async SQLAlchemy Aurora Data API dialect implementation
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from sqlalchemy import pool, util
from sqlalchemy.connectors.asyncio import AsyncAdapt_dbapi_connection
from sqlalchemy.connectors.asyncio import AsyncAdapt_dbapi_cursor
from sqlalchemy.connectors.asyncio import AsyncAdapt_dbapi_module
from sqlalchemy.util.concurrency import await_fallback, await_only

from .base import (
    BaseADAMySQLDialect,
    BaseADAPGDialect,
)

if TYPE_CHECKING:
    from sqlalchemy.connectors.asyncio import AsyncIODBAPIConnection
    from sqlalchemy.connectors.asyncio import AsyncIODBAPICursor
    from sqlalchemy.engine.interfaces import DBAPIConnection
    from sqlalchemy.engine.url import URL


class AsyncAdapt_aurora_data_api_cursor(AsyncAdapt_dbapi_cursor):
    """Async adapter for Aurora Data API cursor."""

    __slots__ = ()

    def _make_new_cursor(self, connection: AsyncIODBAPIConnection) -> AsyncIODBAPICursor:
        # Aurora Data API cursor() method is async and returns a coroutine
        return self.await_(connection.cursor())


class AsyncAdapt_aurora_data_api_connection(AsyncAdapt_dbapi_connection):
    """Async adapter for Aurora Data API connection."""

    __slots__ = ()

    _cursor_cls = AsyncAdapt_aurora_data_api_cursor

    def close(self) -> None:
        """Close the connection."""
        self.await_(self._connection.close())

    def commit(self) -> None:
        """Commit the transaction."""
        self.await_(self._connection.commit())

    def rollback(self) -> None:
        """Roll back the transaction."""
        self.await_(self._connection.rollback())


class AsyncAdaptFallback_aurora_data_api_connection(AsyncAdapt_aurora_data_api_connection):
    """Fallback async adapter for Aurora Data API connection."""

    __slots__ = ()

    await_ = staticmethod(await_fallback)


class AsyncAdapt_aurora_data_api_dbapi(AsyncAdapt_dbapi_module):
    """Async adapter for Aurora Data API DBAPI module."""

    def __init__(self, aurora_data_api_async):
        self.aurora_data_api_async = aurora_data_api_async
        self.paramstyle = "named"
        self._init_dbapi_attributes()

    def _init_dbapi_attributes(self) -> None:
        """Initialize DBAPI attributes from the aurora-data-api async module."""
        for name in (
            "Warning",
            "Error",
            "InterfaceError",
            "DataError",
            "DatabaseError",
            "OperationalError",
            "IntegrityError",
            "InternalError",
            "ProgrammingError",
            "NotSupportedError",
            "apilevel",
            "threadsafety",
            "paramstyle",
            "Date",
            "Time",
            "Timestamp",
            "DateFromTicks",
            "TimeFromTicks",
            "TimestampFromTicks",
            "Binary",
            "STRING",
            "BINARY",
            "NUMBER",
            "DATETIME",
            "ROWID",
            "DECIMAL",
        ):
            if hasattr(self.aurora_data_api_async, name):
                setattr(self, name, getattr(self.aurora_data_api_async, name))

    async def _create_rds_client(self):
        """Create a fresh RDS client for the current event loop."""
        import aiobotocore.session

        session = aiobotocore.session.get_session()
        client_context = session.create_client("rds-data")
        return await client_context.__aenter__(), client_context

    def connect(self, *args: Any, **kwargs: Any) -> AsyncAdapt_aurora_data_api_connection:
        """Create an async connection."""
        async_fallback = kwargs.pop("async_fallback", False)
        creator_fn = kwargs.pop("async_creator_fn", self.aurora_data_api_async.connect)

        # Create a custom connection creation function that sets up the RDS client
        async def create_connection_with_client(*args, **kwargs):
            client, client_context = await self._create_rds_client()
            kwargs["rds_data_client"] = client
            connection = await creator_fn(*args, **kwargs)
            # Store the client context for cleanup
            connection._client_context_for_cleanup = client_context
            return connection

        if util.asbool(async_fallback):
            conn = AsyncAdaptFallback_aurora_data_api_connection(
                self,
                await_fallback(create_connection_with_client(*args, **kwargs)),
            )
        else:
            conn = AsyncAdapt_aurora_data_api_connection(
                self,
                await_only(create_connection_with_client(*args, **kwargs)),
            )

        return conn


class AsyncAuroraMySQLDataAPIDialect(BaseADAMySQLDialect):
    """Async Aurora MySQL Data API dialect."""

    driver = "aurora_data_api_async"
    is_async = True
    has_terminate = True

    @classmethod
    def import_dbapi(cls) -> AsyncAdapt_aurora_data_api_dbapi:
        """Import the async DBAPI module."""
        import aurora_data_api.async_ as aurora_data_api_async

        return AsyncAdapt_aurora_data_api_dbapi(aurora_data_api_async)

    @classmethod
    def get_pool_class(cls, url: URL) -> type:
        """Get the appropriate pool class."""
        async_fallback = url.query.get("async_fallback", False)

        if util.asbool(async_fallback):
            return pool.FallbackAsyncAdaptedQueuePool
        else:
            return pool.AsyncAdaptedQueuePool

    def do_terminate(self, dbapi_connection: DBAPIConnection) -> None:
        """Terminate the connection."""
        dbapi_connection.close()

    @classmethod
    def load_provisioning(cls):
        """Load provisioning hooks for Aurora dialect testing."""
        __import__("sqlalchemy_aurora_data_api.provision")


class AsyncAuroraPostgresDataAPIDialect(BaseADAPGDialect):
    """Async Aurora PostgreSQL Data API dialect."""

    driver = "aurora_data_api_async"
    is_async = True
    has_terminate = True

    @classmethod
    def import_dbapi(cls) -> AsyncAdapt_aurora_data_api_dbapi:
        """Import the async DBAPI module."""
        import aurora_data_api.async_ as aurora_data_api_async

        return AsyncAdapt_aurora_data_api_dbapi(aurora_data_api_async)

    @classmethod
    def get_pool_class(cls, url: URL) -> type:
        """Get the appropriate pool class."""
        async_fallback = url.query.get("async_fallback", False)

        if util.asbool(async_fallback):
            return pool.FallbackAsyncAdaptedQueuePool
        else:
            return pool.AsyncAdaptedQueuePool

    def do_terminate(self, dbapi_connection: DBAPIConnection) -> None:
        """Terminate the connection."""
        dbapi_connection.close()

    @classmethod
    def load_provisioning(cls):
        """Load provisioning hooks for Aurora dialect testing."""
        __import__("sqlalchemy_aurora_data_api.provision")


# Dialect registration will be done in __init__.py
dialect = AsyncAuroraMySQLDataAPIDialect
