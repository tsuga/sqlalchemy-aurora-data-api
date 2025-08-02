"""
sqlalchemy-aurora-data-api
"""

from collections import deque
import json, datetime, re, asyncio
import time

from sqlalchemy import cast, func, util
import sqlalchemy.sql.sqltypes as sqltypes
from sqlalchemy.dialects.postgresql.base import PGDialect, PGExecutionContext
from sqlalchemy.dialects.postgresql import JSON, JSONB, UUID, DATE, TIME, TIMESTAMP, ARRAY, ENUM
from sqlalchemy.dialects.mysql.base import MySQLDialect

import aurora_data_api


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


class _ADA_ARRAY(ARRAY):
    def bind_processor(self, dialect):
        def process(value):
            # FIXME: escape strings properly here
            return "\v".join(value) if isinstance(value, list) else value

        return process

    def bind_expression(self, value):
        return func.string_to_array(value, "\v")


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

    @classmethod
    def import_dbapi(cls):
        return aurora_data_api

    def _extract_error_code(self, exception):
        return exception.args[0].value



# class AuroraMySQLDataAPIDialectAsync(AuroraMySQLDataAPIDialect):
#     driver = "aurora_data_api"
#     is_async = True
#     @classmethod
#     def import_dbapi(cls):
#         import aurora_data_api.async_
#         return aurora_data_api.async_


from aurora_data_api.async_ import AsyncAuroraDataAPICursor
from sqlalchemy.util.concurrency import await_fallback
from sqlalchemy.util.concurrency import await_only
from sqlalchemy.engine import AdaptedConnection

# FIXME: sqlalchemy.connectors.asyncio.AsyncAdapt_dbapi_cursor
class AsyncAdapt_asyncpg_cursor:
    __slots__ = (
        "_adapt_connection",
        "_connection",
        "_rows",
        "description",
        "arraysize",
        "rowcount",
        "_cursor",
        "_invalidate_schema_cache_asof",
    )

    server_side = False

    def __init__(self, adapt_connection):
        self._adapt_connection = adapt_connection
        self._connection = adapt_connection._connection
        self._rows = deque()
        self._cursor = None
        # self._cursor = adapt_connection.cursor()
        self.description = None
        self.arraysize = 1
        self.rowcount = -1
        self._invalidate_schema_cache_asof = 0

    def close(self):
        self._rows.clear()

    def _handle_exception(self, error):
        self._adapt_connection._handle_exception(error)

    # async def _prepare_and_execute(self, operation, parameters):
    #     adapt_connection = self._adapt_connection

    #     async with adapt_connection._execute_mutex:
    #         # if not adapt_connection._started:
    #         #     await adapt_connection._start_transaction()

    #         if parameters is None:
    #             parameters = ()

    #         try:
    #             prepared_stmt, attributes = await adapt_connection._prepare(
    #                 operation, self._invalidate_schema_cache_asof
    #             )

    #             if attributes:
    #                 self.description = [
    #                     (
    #                         attr.name,
    #                         attr.type.oid,
    #                         None,
    #                         None,
    #                         None,
    #                         None,
    #                         None,
    #                     )
    #                     for attr in attributes
    #                 ]
    #             else:
    #                 self.description = None

    #             if self.server_side:
    #                 self._cursor = await prepared_stmt.cursor(*parameters)
    #                 self.rowcount = -1
    #             else:
    #                 self._rows = deque(await prepared_stmt.fetch(*parameters))
    #                 status = prepared_stmt.get_statusmsg()

    #                 reg = re.match(
    #                     r"(?:SELECT|UPDATE|DELETE|INSERT \d+) (\d+)",
    #                     status or "",
    #                 )
    #                 if reg:
    #                     self.rowcount = int(reg.group(1))
    #                 else:
    #                     self.rowcount = -1

    #         except Exception as error:
    #             self._handle_exception(error)

    async def _prepare_and_execute(self, operation, parameters):# FIXME: rename this to _execute
        adapt_connection = self._adapt_connection


        
        async with adapt_connection._execute_mutex:
            # if not adapt_connection._started:
            #     await adapt_connection._start_transaction()

            self._cursor = await self._connection.cursor()

            if parameters is None:
                parameters = ()






            try:
                # return await self._cursor.execute(
                #     operation, parameters
                # )
                await self._cursor.execute(
                    operation, parameters
                )


                if self._cursor.description:
                    self.description = self._cursor.description
                    self._rows = deque(await self._cursor.fetchall())
                else:
                    self.description = None
                    self.rowcount = self._cursor.rowcount

                await self._cursor.close()
                
            except Exception as error:
                self._handle_exception(error)

    async def _executemany(self, operation, seq_of_parameters):
        adapt_connection = self._adapt_connection

        self.description = None
        async with adapt_connection._execute_mutex:
            # await adapt_connection._check_type_cache_invalidation(
            #     self._invalidate_schema_cache_asof
            # )

            # if not adapt_connection._started:
            #     await adapt_connection._start_transaction()

            try:
                return await self._connection.executemany(
                    operation, seq_of_parameters
                )
            except Exception as error:
                self._handle_exception(error)

    def execute(self, operation, parameters=None):
        self._adapt_connection.await_(
            self._prepare_and_execute(operation, parameters)
            # self._execute(operation, parameters)
        )

    def executemany(self, operation, seq_of_parameters):
        return self._adapt_connection.await_(
            self._executemany(operation, seq_of_parameters)
        )

    def setinputsizes(self, *inputsizes):
        raise NotImplementedError()

    def __iter__(self):
        while self._rows:
            yield self._rows.popleft()

    def fetchone(self):
        if self._rows:
            return self._rows.popleft()
        else:
            return None

    def fetchmany(self, size=None):
        if size is None:
            size = self.arraysize

        rr = self._rows
        return [rr.popleft() for _ in range(min(size, len(rr)))]

    def fetchall(self):
        retval = list(self._rows)
        self._rows.clear()
        return retval


class AsyncAdapt_asyncpg_connection(AdaptedConnection):
    __slots__ = (
        "dbapi",
        "isolation_level",
        "_isolation_setting",
        "readonly",
        "deferrable",
        "_transaction",
        "_started",
        "_prepared_statement_cache",
        "_prepared_statement_name_func",
        # "_invalidate_schema_cache_asof",
        "_execute_mutex",
    )

    await_ = staticmethod(await_only)

    def __init__(
        self,
        dbapi,
        connection,
        prepared_statement_cache_size=100,
        prepared_statement_name_func=None,
    ):
        self.dbapi = dbapi
        self._connection = connection
        self.isolation_level = self._isolation_setting = None
        self.readonly = False
        self.deferrable = False
        self._transaction = None
        self._started = False
        # self._invalidate_schema_cache_asof = time.time()
        self._execute_mutex = asyncio.Lock()

        if prepared_statement_cache_size:
            self._prepared_statement_cache = util.LRUCache(
                prepared_statement_cache_size
            )
        else:
            self._prepared_statement_cache = None

        if prepared_statement_name_func:
            self._prepared_statement_name_func = prepared_statement_name_func
        else:
            self._prepared_statement_name_func = self._default_name_func

    # async def _check_type_cache_invalidation(self, invalidate_timestamp):
    #     if invalidate_timestamp > self._invalidate_schema_cache_asof:
    #         await self._connection.reload_schema_state()
    #         self._invalidate_schema_cache_asof = invalidate_timestamp

    async def _prepare(self, operation, invalidate_timestamp):
        # await self._check_type_cache_invalidation(invalidate_timestamp)

        cache = self._prepared_statement_cache
        if cache is None:
            prepared_stmt = await self._connection.prepare(
                operation, name=self._prepared_statement_name_func()
            )
            attributes = prepared_stmt.get_attributes()
            return prepared_stmt, attributes

        # asyncpg uses a type cache for the "attributes" which seems to go
        # stale independently of the PreparedStatement itself, so place that
        # collection in the cache as well.
        if operation in cache:
            prepared_stmt, attributes, cached_timestamp = cache[operation]

            # preparedstatements themselves also go stale for certain DDL
            # changes such as size of a VARCHAR changing, so there is also
            # a cross-connection invalidation timestamp
            if cached_timestamp > invalidate_timestamp:
                return prepared_stmt, attributes

        prepared_stmt = await self._connection.prepare(
            operation, name=self._prepared_statement_name_func()
        )
        attributes = prepared_stmt.get_attributes()
        cache[operation] = (prepared_stmt, attributes, time.time())

        return prepared_stmt, attributes

    def _handle_exception(self, error):
        # if self._connection.is_closed():
        #     self._transaction = None
        #     self._started = False

        # if not isinstance(error, AsyncAdapt_asyncpg_dbapi.Error):
        #     exception_mapping = self.dbapi._asyncpg_error_translate

        #     for super_ in type(error).__mro__:
        #         if super_ in exception_mapping:
        #             translated_error = exception_mapping[super_](
        #                 "%s: %s" % (type(error), error)
        #             )
        #             translated_error.pgcode = translated_error.sqlstate = (
        #                 getattr(error, "sqlstate", None)
        #             )
        #             raise translated_error from error
        #     else:
        #         raise error
        # else:
        #     raise error
        raise error

    @property
    def autocommit(self):
        return self.isolation_level == "autocommit"

    @autocommit.setter
    def autocommit(self, value):
        if value:
            self.isolation_level = "autocommit"
        else:
            self.isolation_level = self._isolation_setting

    def ping(self):
        try:
            _ = self.await_(self._async_ping())
        except Exception as error:
            self._handle_exception(error)

    async def _async_ping(self):
        if self._transaction is None and self.isolation_level != "autocommit":
            # create a tranasction explicitly to support pgbouncer
            # transaction mode.   See #10226
            tr = self._connection.transaction()
            await tr.start()
            try:
                await self._connection.fetchrow(";")
            finally:
                await tr.rollback()
        else:
            await self._connection.fetchrow(";")

    def set_isolation_level(self, level):
        if self._started:
            self.rollback()
        self.isolation_level = self._isolation_setting = level

    async def _start_transaction(self):
        if self.isolation_level == "autocommit":
            return

        try:
            self._transaction = self._connection.transaction(
                isolation=self.isolation_level,
                readonly=self.readonly,
                deferrable=self.deferrable,
            )
            await self._transaction.start()
        except Exception as error:
            self._handle_exception(error)
        else:
            self._started = True

    def cursor(self, server_side=False):
        if server_side:
            return AsyncAdapt_asyncpg_ss_cursor(self)
        else:
            return AsyncAdapt_asyncpg_cursor(self)

    async def _rollback_and_discard(self):
        try:
            await self._transaction.rollback()
        finally:
            # if asyncpg .rollback() was actually called, then whether or
            # not it raised or succeeded, the transation is done, discard it
            self._transaction = None
            self._started = False

    async def _commit_and_discard(self):
        try:
            await self._transaction.commit()
        finally:
            # if asyncpg .commit() was actually called, then whether or
            # not it raised or succeeded, the transation is done, discard it
            self._transaction = None
            self._started = False

    def rollback(self):
        if self._started:
            try:
                self.await_(self._rollback_and_discard())
                self._transaction = None
                self._started = False
            except Exception as error:
                # don't dereference asyncpg transaction if we didn't
                # actually try to call rollback() on it
                self._handle_exception(error)

    def commit(self):
        if self._started:
            try:
                self.await_(self._commit_and_discard())
                self._transaction = None
                self._started = False
            except Exception as error:
                # don't dereference asyncpg transaction if we didn't
                # actually try to call commit() on it
                self._handle_exception(error)

    def close(self):
        self.rollback()

        self.await_(self._connection.close())

    def terminate(self):
        if util.concurrency.in_greenlet():
            # in a greenlet; this is the connection was invalidated
            # case.
            try:
                # try to gracefully close; see #10717
                # timeout added in asyncpg 0.14.0 December 2017
                self.await_(asyncio.shield(self._connection.close(timeout=2)))
            except (
                asyncio.TimeoutError,
                asyncio.CancelledError,
                OSError,
                self.dbapi.asyncpg.PostgresError, # FIXME
            ) as e:
                # in the case where we are recycling an old connection
                # that may have already been disconnected, close() will
                # fail with the above timeout.  in this case, terminate
                # the connection without any further waiting.
                # see issue #8419
                self._connection.terminate()
                if isinstance(e, asyncio.CancelledError):
                    # re-raise CancelledError if we were cancelled
                    raise
        else:
            # not in a greenlet; this is the gc cleanup case
            self._connection.terminate()
        self._started = False

    @staticmethod
    def _default_name_func():
        return None

class AsyncAdaptFallback_asyncpg_connection(AsyncAdapt_asyncpg_connection):
    __slots__ = ()

    await_ = staticmethod(await_fallback)


class AsyncAdapt_asyncpg_dbapi:
    def __init__(self, aurora_data_api_async):
        self.aurora_data_api_async = aurora_data_api_async
        self.paramstyle = "named"

    def connect(self, *arg, **kw):
        async_fallback = kw.pop("async_fallback", False)
        creator_fn = kw.pop("async_creator_fn", self.aurora_data_api_async.connect)
        prepared_statement_cache_size = kw.pop(
            "prepared_statement_cache_size", 100
        )
        prepared_statement_name_func = kw.pop(
            "prepared_statement_name_func", None
        )

        if util.asbool(async_fallback):
            return AsyncAdaptFallback_asyncpg_connection(
                self,
                await_fallback(creator_fn(*arg, **kw)),
                prepared_statement_cache_size=prepared_statement_cache_size,
                prepared_statement_name_func=prepared_statement_name_func,
            )
        else:
            return AsyncAdapt_asyncpg_connection(
                self,
                await_only(creator_fn(*arg, **kw)),
                prepared_statement_cache_size=prepared_statement_cache_size,
                prepared_statement_name_func=prepared_statement_name_func,
            )
    
    class Error(Exception):  # FIXME
        pass


class PGExecutionContext_aurora_data_api_async(PGExecutionContext):
    def handle_dbapi_exception(self, e):
        if isinstance(
            e,
            (
                self.dialect.dbapi.InvalidCachedStatementError,
                self.dialect.dbapi.InternalServerError,
            ),
        ):
            self.dialect._invalidate_schema_cache()

    def pre_exec(self):
        # if self.isddl:
        #     self.dialect._invalidate_schema_cache()

        # self.cursor._invalidate_schema_cache_asof = (
        #     self.dialect._invalidate_schema_cache_asof
        # )

        if not self.compiled:
            return


class AuroraPostgresDataAPIDialectAsync(AuroraPostgresDataAPIDialect):
    # driver = "aurora_data_api.async_"
    is_async = True
    execution_ctx_cls = PGExecutionContext_aurora_data_api_async

    # @classmethod
    # def import_dbapi(cls):
    #     return AsyncAdapt_asyncpg_dbapi(__import__("asyncpg"))


    # @classmethod
    # def import_dbapi(cls):
    #     import aurora_data_api.async_
    #     return aurora_data_api.async_

    @classmethod
    def import_dbapi(cls):
        import aurora_data_api.async_
        return AsyncAdapt_asyncpg_dbapi(aurora_data_api.async_)



def register_dialects():
    from sqlalchemy.dialects import registry

    registry.register("mysql.auroradataapi", __name__, AuroraMySQLDataAPIDialect.__name__)
    registry.register("postgresql.auroradataapi", __name__, AuroraPostgresDataAPIDialect.__name__)
