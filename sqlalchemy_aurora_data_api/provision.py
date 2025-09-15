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
)
from sqlalchemy import text

log = logging.getLogger(__name__)

# Ensure AWS region is set for testing
if not os.environ.get('AWS_DEFAULT_REGION'):
    os.environ['AWS_DEFAULT_REGION'] = 'ap-northeast-1'


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
    """Temporary table arguments for Aurora."""
    # Aurora supports standard temporary tables
    return {"prefixes": ["TEMPORARY"]}


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
        if 'cursor' in locals():
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