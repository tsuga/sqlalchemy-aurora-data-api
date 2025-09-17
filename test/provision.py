"""
Provision hooks for Aurora Data API dialect testing.
"""

import logging
import os

from sqlalchemy.testing.provision import (
    generate_driver_url,
    create_db,
    drop_db,
    temp_table_keyword_args,
    configure_follower,
    post_configure_engine,
    set_default_schema_on_connection,
    drop_all_schema_objects_pre_tables,
    drop_all_schema_objects_post_tables,
    prepare_for_drop_tables,
)
from sqlalchemy import text, inspect

log = logging.getLogger(__name__)

# Ensure AWS region is set for testing
if not os.environ.get("AWS_DEFAULT_REGION"):
    os.environ["AWS_DEFAULT_REGION"] = "ap-northeast-1"


@generate_driver_url.for_db("aurora")
def generate_driver_url(url, driver, query_str):
    """Generate driver-specific URLs for Aurora dialect testing."""
    backend = url.get_backend_name()

    # Aurora uses the same URL format regardless of driver
    # Just return the original URL as Aurora handles connection internally
    return url


@create_db.for_db("aurora")
def _aurora_create_db(cfg, eng, ident):
    """Create database for Aurora testing."""
    # Aurora Data API doesn't support CREATE DATABASE
    # The database is pre-configured in the Aurora cluster
    log.info(f"Aurora: Using pre-configured database for test {ident}")
    # Return early to skip actual database creation
    return


@drop_db.for_db("aurora")
def _aurora_drop_db(cfg, eng, ident):
    """Drop database for Aurora testing."""
    # Aurora Data API doesn't support DROP DATABASE
    # Just log that cleanup is not needed
    log.info(f"Aurora: Cleanup not needed for test {ident}")


@temp_table_keyword_args.for_db("aurora")
def _aurora_temp_table_keyword_args(cfg, eng):
    """Temporary table arguments for Aurora.

    Aurora Data API has session handling differences that affect temporary tables.
    Using ON COMMIT PRESERVE ROWS to ensure temp tables persist within the session.
    """
    # Return temporary table configuration for Aurora PostgreSQL
    # Note: Aurora Data API may have different session semantics than regular PostgreSQL
    return {"prefixes": ["TEMPORARY"], "postgresql_on_commit": "PRESERVE ROWS"}


@configure_follower.for_db("aurora")
def _aurora_configure_follower(config, ident):
    """Configure follower for Aurora testing."""
    # Aurora doesn't need special follower configuration
    # Use the same database configuration
    log.info(f"Aurora: Configuring follower for {ident}")


@set_default_schema_on_connection.for_db("aurora")
def _aurora_set_default_schema_on_connection(cfg, dbapi_connection, schema_name):
    """Set default schema on Aurora connection."""
    # For Aurora PostgreSQL, set the search_path like standard PostgreSQL
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute(f"SET search_path = '{schema_name}'")
        log.info(f"Aurora: Set search_path to {schema_name}")
    except Exception as e:
        log.warning(f"Aurora: Failed to set search_path to {schema_name}: {e}")
    finally:
        if "cursor" in locals():
            cursor.close()


@post_configure_engine.for_db("aurora")
def _aurora_post_configure_engine(url, engine, follower_ident):
    """Create test schemas after engine configuration."""
    log.info("Aurora: Creating test schemas")

    try:
        with engine.begin() as conn:
            # Create test schemas if they don't exist
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS test_schema"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS test_schema_2"))
            log.info("Aurora: Successfully created test schemas")
    except Exception as e:
        log.warning(f"Aurora: Failed to create test schemas: {e}")
        # This might not be fatal if schemas already exist


@drop_all_schema_objects_pre_tables.for_db("aurora")
def _aurora_drop_all_schema_objects_pre_tables(cfg, eng):
    """Drop schema objects before tables for Aurora.

    Aurora Data API may have different transaction handling for prepared transactions.
    """
    try:
        with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            # Try to rollback any prepared transactions
            for xid in conn.exec_driver_sql("select gid from pg_prepared_xacts").scalars():
                try:
                    conn.exec_driver_sql("ROLLBACK PREPARED '%s'" % xid)
                except Exception as e:
                    log.warning(f"Aurora: Failed to rollback prepared transaction {xid}: {e}")
    except Exception as e:
        log.warning(f"Aurora: Failed to check prepared transactions: {e}")


@drop_all_schema_objects_post_tables.for_db("aurora")
def _aurora_drop_all_schema_objects_post_tables(cfg, eng):
    """Drop schema objects after tables for Aurora."""
    from sqlalchemy.dialects import postgresql

    try:
        inspector = inspect(eng)
        with eng.begin() as conn:
            for enum in inspector.get_enums("*"):
                try:
                    conn.execute(postgresql.DropEnumType(postgresql.ENUM(name=enum["name"], schema=enum["schema"])))
                except Exception as e:
                    log.warning(f"Aurora: Failed to drop enum {enum['name']}: {e}")
    except Exception as e:
        log.warning(f"Aurora: Failed to drop schema objects: {e}")


@prepare_for_drop_tables.for_db("aurora")
def _aurora_prepare_for_drop_tables(config, connection):
    """Prepare for dropping tables in Aurora.

    Aurora Data API may have different locking behavior than standard PostgreSQL.
    """
    try:
        result = connection.exec_driver_sql(
            "select pid, state, wait_event_type, query "
            "from pg_stat_activity where "
            "usename=current_user "
            "and datname=current_database() and state='idle in transaction' "
            "and pid != pg_backend_pid()"
        )
        rows = result.all()
        if rows:
            log.warning(
                "Aurora: PostgreSQL may not be able to DROP tables due to "
                "idle in transaction: %s" % ("; ".join(row._mapping["query"] for row in rows))
            )
    except Exception as e:
        log.warning(f"Aurora: Failed to check for idle transactions: {e}")
