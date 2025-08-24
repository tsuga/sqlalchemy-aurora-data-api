"""
Async SQLAlchemy Aurora Data API dialect implementation
"""

from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING

from sqlalchemy import pool, util
from sqlalchemy.dialects.mysql.base import MySQLDialect
from sqlalchemy.dialects.postgresql.base import PGDialect
from sqlalchemy.connectors.asyncio import AsyncAdapt_dbapi_connection
from sqlalchemy.connectors.asyncio import AsyncAdapt_dbapi_cursor
from sqlalchemy.connectors.asyncio import AsyncAdapt_dbapi_module
from sqlalchemy.util.concurrency import await_fallback, await_only

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

if TYPE_CHECKING:
    from sqlalchemy.connectors.asyncio import AsyncIODBAPIConnection
    from sqlalchemy.connectors.asyncio import AsyncIODBAPICursor
    from sqlalchemy.engine.interfaces import ConnectArgsType
    from sqlalchemy.engine.interfaces import DBAPIConnection
    from sqlalchemy.engine.url import URL

import sqlalchemy.sql.sqltypes as sqltypes
from sqlalchemy.dialects.postgresql import JSON, JSONB, UUID, ARRAY


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
        try:
            if hasattr(self._connection, "close") and callable(self._connection.close):
                # Check if we're in a running event loop context
                import asyncio

                try:
                    # Try to get current running loop
                    loop = asyncio.get_running_loop()
                    if loop.is_closed():
                        # If loop is closed, don't attempt async cleanup
                        return
                except RuntimeError:
                    # No running loop, can't perform async cleanup
                    return

                self.await_(self._connection.close())
        except (RuntimeError, Exception) as e:
            # Handle cases where event loop is closed or other cleanup issues
            if "Event loop is closed" not in str(e) and "no running event loop" not in str(e):
                # Re-raise unexpected errors
                import warnings

                warnings.warn(f"Error during connection cleanup: {e}", RuntimeWarning)

    def commit(self) -> None:
        """Commit the transaction."""
        try:
            if hasattr(self._connection, "commit") and callable(self._connection.commit):
                self.await_(self._connection.commit())
        except (RuntimeError, Exception) as e:
            if "Event loop is closed" not in str(e):
                raise

    def rollback(self) -> None:
        """Roll back the transaction."""
        try:
            if hasattr(self._connection, "rollback") and callable(self._connection.rollback):
                self.await_(self._connection.rollback())
        except (RuntimeError, Exception) as e:
            if "Event loop is closed" not in str(e):
                raise


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

    def connect(self, *args: Any, **kwargs: Any) -> AsyncAdapt_aurora_data_api_connection:
        """Create an async connection."""
        async_fallback = kwargs.pop("async_fallback", False)
        creator_fn = kwargs.pop("async_creator_fn", self.aurora_data_api_async.connect)

        if util.asbool(async_fallback):
            return AsyncAdaptFallback_aurora_data_api_connection(
                self,
                await_fallback(creator_fn(*args, **kwargs)),
            )
        else:
            return AsyncAdapt_aurora_data_api_connection(
                self,
                await_only(creator_fn(*args, **kwargs)),
            )


class AsyncAuroraMySQLDataAPIDialect(MySQLDialect):
    """Async Aurora MySQL Data API dialect."""

    driver = "aurora_data_api_async"
    default_schema_name = None
    supports_native_decimal = True
    supports_statement_cache = True
    is_async = True
    has_terminate = True

    # Aurora Data API doesn't support server-side cursors
    supports_server_side_cursors = False

    colspecs = util.update_copy(
        MySQLDialect.colspecs,
        {
            sqltypes.Date: _ADA_DATE,
            sqltypes.Time: _ADA_TIME,
            sqltypes.DateTime: _ADA_TIMESTAMP,
        },
    )

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

    def on_connect(self):
        """Return a callable that will be executed on each new connection."""

        def on_connect_impl(dbapi_connection, connection_record):
            # Ensure proper cleanup on connection close
            def cleanup():
                try:
                    if hasattr(dbapi_connection, "_connection"):
                        # Access the underlying Aurora Data API connection
                        aurora_conn = dbapi_connection._connection
                        if hasattr(aurora_conn, "close"):
                            # Schedule cleanup but don't wait for it to complete
                            import asyncio

                            try:
                                loop = asyncio.get_running_loop()
                                if not loop.is_closed():
                                    asyncio.create_task(aurora_conn.close())
                            except RuntimeError:
                                pass  # No running loop, skip cleanup
                except Exception:
                    pass  # Ignore cleanup errors

            # Register cleanup callback
            connection_record.info.setdefault("cleanup_callbacks", []).append(cleanup)

        return on_connect_impl

    def _detect_charset(self, connection):
        """Detect charset from connection."""
        return connection.execute("SHOW VARIABLES LIKE 'character_set_client'").fetchone()[1]

    def _extract_error_code(self, exception):
        """Extract error code from exception."""
        return exception.args[0].value

    def do_terminate(self, dbapi_connection: DBAPIConnection) -> None:
        """Terminate the connection."""
        dbapi_connection.close()

    def create_connect_args(self, url: URL, _translate_args: Optional[Dict[str, Any]] = None) -> ConnectArgsType:
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

        return [], connect_args


class AsyncAuroraPostgresDataAPIDialect(PGDialect):
    """Async Aurora PostgreSQL Data API dialect."""

    driver = "aurora_data_api_async"
    default_schema_name = None
    supports_statement_cache = True
    is_async = True
    has_terminate = True

    # Aurora Data API doesn't support server-side cursors
    supports_server_side_cursors = False
    # Aurora Data API doesn't support multi rowcount
    supports_sane_multi_rowcount = False

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

    def _extract_error_code(self, exception):
        """Extract error code from exception."""
        return exception.args[0].value

    def do_terminate(self, dbapi_connection: DBAPIConnection) -> None:
        """Terminate the connection."""
        dbapi_connection.close()

    def create_connect_args(self, url: URL, _translate_args: Optional[Dict[str, Any]] = None) -> ConnectArgsType:
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

        return [], connect_args


# Dialect registration will be done in __init__.py
dialect = AsyncAuroraMySQLDataAPIDialect
