"""
Aurora Data API dialect requirements for SQLAlchemy test suite.

This module defines which features are supported by the Aurora Data API dialect.
"""

from sqlalchemy.testing.requirements import SuiteRequirements
from sqlalchemy.testing import exclusions


class Requirements(SuiteRequirements):
    """Requirements for Aurora Data API dialect"""

    @property
    def foreign_keys(self):
        """Aurora supports foreign key constraints"""
        return exclusions.open()

    @property
    def primary_key_constraint_reflection(self):
        """Aurora supports primary key reflection"""
        return exclusions.open()

    @property
    def index_reflection(self):
        """Aurora supports index reflection"""
        return exclusions.open()

    @property
    def unique_constraint_reflection(self):
        """Aurora supports unique constraint reflection"""
        return exclusions.open()

    @property
    def table_reflection(self):
        """Aurora supports table reflection"""
        return exclusions.open()

    @property
    def schema_reflection(self):
        """Aurora supports schema reflection"""
        return exclusions.open()

    @property
    def autoincrement_insert(self):
        """Aurora supports autoincrement on INSERT"""
        return exclusions.open()

    @property
    def sequences(self):
        """Aurora does not support sequences (MySQL-based)"""
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
        """Aurora Data API provides lastrowid functionality"""
        return exclusions.open()

    @property
    def insertmanyvalues(self):
        """Aurora supports INSERT many values"""
        return exclusions.open()

    @property
    def insert_returning(self):
        """Aurora does not support INSERT...RETURNING (MySQL limitation)"""
        return exclusions.closed()

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
    def precision_generic_float_type(self):
        """Aurora supports precision in FLOAT type"""
        return exclusions.open()

    @property
    def precision_numerics_general(self):
        """Aurora supports precision in DECIMAL/NUMERIC types"""
        return exclusions.open()

    @property
    def precision_numerics_enotation_large(self):
        """Aurora supports large precision numerics"""
        return exclusions.open()

    @property
    def precision_numerics_enotation_small(self):
        """Aurora supports small precision numerics"""
        return exclusions.open()

    @property
    def precision_numerics_many_significant_digits(self):
        """Aurora supports many significant digits"""
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
    def datetime_microseconds(self):
        """Aurora supports microseconds in datetime"""
        return exclusions.open()

    @property
    def time_microseconds(self):
        """Aurora supports microseconds in time"""
        return exclusions.open()

    @property
    def date_coerces_from_datetime(self):
        """Aurora coerces datetime to date"""
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
    def unbounded_varchar(self):
        """Aurora supports TEXT type for unbounded varchar"""
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
    def nullable_booleans(self):
        """Aurora supports nullable boolean columns"""
        return exclusions.open()

    @property
    def standalone_binds(self):
        """Aurora Data API may have limitations with standalone binds"""
        return exclusions.closed()

    @property
    def intersect(self):
        """Aurora does not support INTERSECT (MySQL limitation)"""
        return exclusions.closed()

    @property
    def except_(self):
        """Aurora does not support EXCEPT (MySQL limitation)"""
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
    def implicitly_named_constraints(self):
        """Aurora generates implicit constraint names"""
        return exclusions.open()

    @property
    def duplicate_names_in_cursor_description(self):
        """Aurora handles duplicate column names in cursor description"""
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