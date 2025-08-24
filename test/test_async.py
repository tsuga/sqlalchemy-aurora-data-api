import os
import sys
import unittest
import logging
import datetime
import enum
import asyncio
from uuid import uuid4

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Float,
    LargeBinary,
    Numeric,
    Date,
    Time,
    DateTime,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, JSON, DATE, TIME, TIMESTAMP, ARRAY
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy_aurora_data_api import register_dialects, _ADA_TIMESTAMP  # noqa
from sqlalchemy_aurora_data_api.async_ import AsyncAuroraMySQLDataAPIDialect, AsyncAuroraPostgresDataAPIDialect

logging.basicConfig(level=logging.INFO)
logging.getLogger("aurora_data_api").setLevel(logging.DEBUG)
logging.getLogger("urllib3.connectionpool").setLevel(logging.DEBUG)

dialect_interface_attributes = {
    "name",
    "driver",
    "positional",
    "paramstyle",
    "statement_compiler",
    "ddl_compiler",
    "server_version_info",
    "default_schema_name",
    "execution_ctx_cls",
    "execute_sequence_format",
    "preparer",
    "supports_alter",
    "max_identifier_length",
    "supports_sane_rowcount",
    "supports_sane_multi_rowcount",
    "preexecute_autoincrement_sequences",
    "colspecs",
    "supports_default_values",
    "supports_sequences",
    "sequences_optional",
    "supports_native_enum",
    "supports_native_boolean",
    "dbapi_exception_translation_map",
    "is_async",
    "has_terminate",
}

dialect_interface_methods = {
    "connect",
    "create_connect_args",
    "create_xid",
    "denormalize_name",
    "do_begin",
    "do_begin_twophase",
    "do_close",
    "do_commit",
    "do_commit_twophase",
    "do_execute",
    "do_execute_no_params",
    "do_executemany",
    "do_prepare_twophase",
    "do_recover_twophase",
    "do_release_savepoint",
    "do_rollback",
    "do_rollback_to_savepoint",
    "do_rollback_twophase",
    "do_savepoint",
    "do_terminate",
    "engine_created",
    "get_check_constraints",
    "get_columns",
    "get_dialect_cls",
    "get_foreign_keys",
    "get_indexes",
    "get_isolation_level",
    "get_pk_constraint",
    "get_table_comment",
    "get_table_names",
    "get_temp_table_names",
    "get_temp_view_names",
    "get_unique_constraints",
    "get_view_definition",
    "get_view_names",
    "has_sequence",
    "has_table",
    "initialize",
    "is_disconnect",
    "normalize_name",
    "reset_isolation_level",
    "set_isolation_level",
    "type_descriptor",
}

AsyncBasicBase = declarative_base()
AsyncBase = declarative_base()


class Socks(enum.Enum):
    red = 1
    green = 2
    black = 3


class AsyncBasicUser(AsyncBasicBase):
    __tablename__ = "sqlalchemy_aurora_data_api_async_testI"

    id = Column(Integer, primary_key=True)
    name = Column(String(64))
    fullname = Column(String(64))
    nickname = Column(String(64))
    birthday = Column(Date)
    eats_breakfast_at = Column(Time)
    married_at = Column(DateTime)


class AsyncUser(AsyncBase):
    __tablename__ = "sqlalchemy_aurora_data_api_async_testJ"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    fullname = Column(String)
    nickname = Column(String)
    doc = Column(JSONB)
    doc2 = Column(JSON)
    uuid = Column(UUID)
    uuid2 = Column(UUID(as_uuid=True), default=uuid4)
    flag = Column(Boolean, nullable=True)
    nonesuch = Column(Boolean, nullable=True)
    birthday = Column(DATE)
    wakes_up_at = Column(TIME)
    added = Column(TIMESTAMP)
    floated = Column(Float)
    nybbled = Column(LargeBinary)
    friends = Column(ARRAY(String))
    num_friends = Numeric(asdecimal=True)
    num_laptops = Numeric(asdecimal=False)
    first_date = Column(Date)
    note = Column(Text)


class TestAsyncAuroraDataAPI(unittest.TestCase):
    # Base class: False, subclasses: True
    _run_tests = False

    @classmethod
    def tearDownClass(cls):
        pass

    def test_interface_conformance(self):
        if not self._run_tests:
            self.skipTest("Base class test - only run in subclasses")

        for attr in dialect_interface_attributes:
            self.assertIn(attr, dir(self.engine.sync_engine.dialect))

        for attr in dialect_interface_methods:
            self.assertIn(attr, dir(self.engine.sync_engine.dialect))
            assert callable(getattr(self.engine.sync_engine.dialect, attr))

    def test_dialect_properties(self):
        if not self._run_tests:
            self.skipTest("Base class test - only run in subclasses")

        dialect = self.engine.sync_engine.dialect
        self.assertTrue(dialect.is_async)
        self.assertTrue(dialect.has_terminate)
        self.assertFalse(dialect.supports_server_side_cursors)


class TestAsyncAuroraDataAPIPostgresDialect(TestAsyncAuroraDataAPI):
    dialect = "postgresql+auroradataapiasync://"
    _run_tests = True  # Enable test execution in subclass

    @classmethod
    def setUpClass(cls):
        register_dialects()
        cls.db_name = os.environ.get("AURORA_DB_NAME", __name__)
        cls.engine = create_async_engine(
            cls.dialect + ":@/" + cls.db_name,
            connect_args={
                "aurora_cluster_arn": os.environ.get("AURORA_CLUSTER_ARN"),
                "secret_arn": os.environ.get("SECRET_ARN"),
            },
        )

    def test_execute(self):
        async def async_test():
            async with self.engine.connect() as conn:
                result = await conn.execute(text("select * from pg_catalog.pg_tables limit 5"))
                rows = result.fetchall()
                for row in rows:
                    print(row)

        if os.environ.get("AURORA_CLUSTER_ARN") and os.environ.get("SECRET_ARN"):
            asyncio.run(async_test())
        else:
            self.skipTest("Aurora credentials not provided")

    def test_orm(self):
        async def async_test():
            async with self.engine.connect() as conn:
                # Test simple query first
                result = await conn.execute(text("SELECT 1 as test_value"))
                row = result.fetchone()
                self.assertEqual(row.test_value, 1)

                # Test table creation
                await conn.execute(text("DROP TABLE IF EXISTS async_test_table"))
                await conn.execute(
                    text("""
                    CREATE TABLE async_test_table (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(50),
                        value INTEGER
                    )
                """)
                )

                # Test insert
                await conn.execute(
                    text("""
                    INSERT INTO async_test_table (name, value) VALUES ('test', 42)
                """)
                )

                # Test select
                result = await conn.execute(text("SELECT name, value FROM async_test_table WHERE name = 'test'"))
                row = result.fetchone()
                self.assertEqual(row.name, "test")
                self.assertEqual(row.value, 42)

                await conn.commit()

        if os.environ.get("AURORA_CLUSTER_ARN") and os.environ.get("SECRET_ARN"):
            asyncio.run(async_test())
        else:
            self.skipTest("Aurora credentials not provided")

    @unittest.skipIf(sys.version_info < (3, 7), "Skipping test that requires Python 3.7+")
    def test_timestamp_microsecond_padding(self):
        ts = "2019-10-31 09:37:17.3186"
        processor = _ADA_TIMESTAMP.result_processor(_ADA_TIMESTAMP, None, None)
        self.assertEqual(processor(ts), datetime.datetime.fromisoformat(ts.ljust(26, "0")))


class TestAsyncAuroraDataAPIMySQLDialect(TestAsyncAuroraDataAPI):
    dialect = "mysql+auroradataapiasync://"
    _run_tests = True  # Enable test execution in subclass

    @classmethod
    def setUpClass(cls):
        register_dialects()
        cls.db_name = os.environ.get("AURORA_DB_NAME", __name__)
        cls.engine = create_async_engine(cls.dialect + ":@/" + cls.db_name + "?charset=utf8mb4")

    def test_execute(self):
        async def async_test():
            async with self.engine.connect() as conn:
                result = await conn.execute(text("select * from information_schema.tables limit 5"))
                rows = result.fetchall()
                for row in rows:
                    print(row)

        if os.environ.get("AURORA_CLUSTER_ARN") and os.environ.get("SECRET_ARN"):
            asyncio.run(async_test())
        else:
            self.skipTest("Aurora credentials not provided")

    def test_orm(self):
        async def async_test():
            async with self.engine.connect() as conn:
                # Test simple query first
                result = await conn.execute(text("SELECT 1 as test_value"))
                row = result.fetchone()
                self.assertEqual(row.test_value, 1)

                # Test table creation
                await conn.execute(text("DROP TABLE IF EXISTS async_test_table"))
                await conn.execute(
                    text("""
                    CREATE TABLE async_test_table (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(50),
                        value INT
                    )
                """)
                )

                # Test insert
                await conn.execute(
                    text("""
                    INSERT INTO async_test_table (name, value) VALUES ('test', 42)
                """)
                )

                # Test select
                result = await conn.execute(text("SELECT name, value FROM async_test_table WHERE name = 'test'"))
                row = result.fetchone()
                self.assertEqual(row.name, "test")
                self.assertEqual(row.value, 42)

                await conn.commit()

        if os.environ.get("AURORA_CLUSTER_ARN") and os.environ.get("SECRET_ARN"):
            asyncio.run(async_test())
        else:
            self.skipTest("Aurora credentials not provided")


class TestAsyncDialectUnit(unittest.TestCase):
    """Unit tests for async dialects without requiring Aurora connection."""

    def test_mysql_dialect_creation(self):
        dialect = AsyncAuroraMySQLDataAPIDialect()
        self.assertEqual(dialect.driver, "aurora_data_api_async")
        self.assertTrue(dialect.is_async)
        self.assertTrue(dialect.has_terminate)
        self.assertFalse(dialect.supports_server_side_cursors)

    def test_postgres_dialect_creation(self):
        dialect = AsyncAuroraPostgresDataAPIDialect()
        self.assertEqual(dialect.driver, "aurora_data_api_async")
        self.assertTrue(dialect.is_async)
        self.assertTrue(dialect.has_terminate)
        self.assertFalse(dialect.supports_server_side_cursors)
        self.assertFalse(dialect.supports_sane_multi_rowcount)

    def test_mysql_connection_args(self):
        from sqlalchemy.engine.url import make_url

        dialect = AsyncAuroraMySQLDataAPIDialect()
        url = make_url(
            "mysql+auroradataapiasync:///?aurora_cluster_arn=test-arn&secret_arn=test-secret&database=test-db&charset=utf8mb4"
        )

        args, kwargs = dialect.create_connect_args(url)

        self.assertEqual(args, [])
        self.assertIn("aurora_cluster_arn", kwargs)
        self.assertIn("secret_arn", kwargs)
        self.assertIn("database", kwargs)
        self.assertIn("charset", kwargs)
        self.assertEqual(kwargs["aurora_cluster_arn"], "test-arn")
        self.assertEqual(kwargs["secret_arn"], "test-secret")
        self.assertEqual(kwargs["database"], "test-db")
        self.assertEqual(kwargs["charset"], "utf8mb4")

    def test_postgres_connection_args(self):
        from sqlalchemy.engine.url import make_url

        dialect = AsyncAuroraPostgresDataAPIDialect()
        url = make_url(
            "postgresql+auroradataapiasync:///?aurora_cluster_arn=test-arn&secret_arn=test-secret&dbname=test-db"
        )

        args, kwargs = dialect.create_connect_args(url)

        self.assertEqual(args, [])
        self.assertIn("aurora_cluster_arn", kwargs)
        self.assertIn("secret_arn", kwargs)
        self.assertIn("database", kwargs)
        self.assertEqual(kwargs["aurora_cluster_arn"], "test-arn")
        self.assertEqual(kwargs["secret_arn"], "test-secret")
        self.assertEqual(kwargs["database"], "test-db")


if __name__ == "__main__":
    unittest.main()
