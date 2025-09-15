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
)

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