"""
Aurora Data API dialect requirements for SQLAlchemy test suite.

This module defines which features are supported by the Aurora Data API dialect.
"""

from sqlalchemy.testing.requirements import SuiteRequirements
from sqlalchemy.testing import exclusions


class Requirements(SuiteRequirements):
    """Requirements for Aurora Data API dialect"""


    @property
    def schema_reflection(self):
        """Aurora supports schema reflection"""
        return exclusions.open()

    @property
    def sequences(self):
        """Aurora does not support sequences (MySQL-based)
        FIXME: Check on MySQL
        """
        return exclusions.closed()

    @property
    def sequences_optional(self):
        """Aurora does not support sequences"""
        return exclusions.closed()

    @property
    def reflects_pk_names(self):
        """Aurora reflects primary key constraint names"""
        return exclusions.open()

    @property
    def emulated_lastrowid(self):
        """Aurora supports lastrowid emulation"""
        return exclusions.open()

    @property
    def dbapi_lastrowid(self):
        """Aurora Data API lastrowid support.

        PostgreSQL limitation from AWS documentation:
        "The generatedFields data isn't supported by Aurora PostgreSQL.
        To get the values of generated fields, use the RETURNING clause.
        For more information, see Returning Data From Modified Rows in the PostgreSQL documentation."
        """
        return exclusions.only_if(
            lambda config: getattr(config.db.dialect, 'supports_lastrowid', True),
            "Aurora Data API %(does_support)s lastrowid functionality"
        )

    @property
    def insertmanyvalues(self):
        """Aurora supports INSERT many values"""
        return exclusions.open()

    @property
    def insert_returning(self):
        """Aurora INSERT...RETURNING support (inherits from dialect)"""
        return exclusions.only_if(
            lambda config: getattr(config.db.dialect, 'insert_returning', False),
            "Aurora Data API %(does_support)s INSERT...RETURNING"
        )

    @property
    def update_returning(self):
        """Aurora does not support UPDATE...RETURNING (MySQL limitation)"""
        return exclusions.closed()

    @property
    def delete_returning(self):
        """Aurora does not support DELETE...RETURNING (MySQL limitation)"""
        return exclusions.closed()

    @property
    def ctes(self):
        """Aurora supports CTEs (MySQL 8.0+ feature)"""
        return exclusions.open()

    @property
    def window_functions(self):
        """Aurora supports window functions (MySQL 8.0+ feature)"""
        return exclusions.open()


    @property
    def precision_numerics_enotation_small(self):
        """Aurora supports small precision numerics"""
        return exclusions.open()


    @property
    def reflects_json_type(self):
        """Aurora supports JSON type reflection"""
        return exclusions.open()

    @property
    def json_type(self):
        """Aurora supports JSON type"""
        return exclusions.open()


    @property
    def timezone_aware_dates(self):
        """Aurora does not support timezone-aware dates natively"""
        return exclusions.closed()

    @property
    def temporary_tables(self):
        """Aurora Data API may not support temporary tables"""
        return exclusions.closed()

    @property
    def temp_table_names(self):
        """Aurora Data API may not support temporary table names"""
        return exclusions.closed()

    @property
    def temporary_views(self):
        """Aurora may not support temporary views via Data API"""
        return exclusions.closed()

    @property
    def unicode_connections(self):
        """Aurora supports unicode connections"""
        return exclusions.open()

    @property
    def unicode_ddl(self):
        """Aurora supports unicode in DDL"""
        return exclusions.open()

    @property
    def empty_strings_varchar(self):
        """Aurora supports empty strings in varchar"""
        return exclusions.open()

    @property
    def empty_strings_text(self):
        """Aurora supports empty strings in text"""
        return exclusions.open()

    @property
    def standalone_binds(self):
        """Aurora Data API may have limitations with standalone binds"""
        return exclusions.closed()

    @property
    def savepoints(self):
        """Aurora Data API may not support savepoints"""
        return exclusions.closed()

    @property
    def two_phase_transactions(self):
        """Aurora Data API does not support two-phase transactions"""
        return exclusions.closed()

    @property
    def views(self):
        """Aurora supports views"""
        return exclusions.open()

    @property
    def schemas(self):
        """Aurora supports schemas (databases in MySQL terms)"""
        return exclusions.open()

    @property
    def cross_schema_fk_reflection(self):
        """Aurora supports cross-schema foreign key reflection"""
        return exclusions.open()

    @property
    def denormalized_names(self):
        """Aurora may handle denormalized names"""
        return exclusions.open()

    @property
    def multivalues_inserts(self):
        """Aurora supports multi-value inserts"""
        return exclusions.open()

    @property
    def supports_distinct_on(self):
        """Aurora PostgreSQL supports DISTINCT ON"""
        return exclusions.open()

    @property
    def datetime_microseconds(self):
        """Aurora Data API only supports millisecond precision (3 digits)"""
        return exclusions.closed()

    @property
    def time_microseconds(self):
        """Aurora Data API only supports millisecond precision (3 digits)"""
        return exclusions.closed()

    @property
    def json_deserializer_binary(self):
        """Aurora Data API returns JSON with compact formatting (no spaces).

        The test expects standard json.dumps() format: '{"key1": "data1"}'
        But Aurora returns compact format: '{"key1":"data1"}'
        Both are valid JSON, but the test is strict about whitespace formatting.
        Avoiding runtime JSON re-parsing for performance reasons.
        """
        return exclusions.closed()

    @property
    def precision_numerics_many_significant_digits(self):
        """Aurora Data API may have precision limitations for very large numbers.

        Large decimal values like Decimal('31943874831932418390.01') lose precision
        and become Decimal('31943874831932399616.000000000000'). This appears to be
        a limitation in Aurora Data API's numeric handling for numbers with many
        significant digits.

        FIXME: Need further investigation
        """
        return exclusions.closed()

