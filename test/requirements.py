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
        return exclusions.open()

    @property
    def sequences_optional(self):
        """Aurora does not support sequences"""
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
    def reflects_json_type(self):
        """Aurora supports JSON type reflection"""
        return exclusions.open()

    @property
    def json_type(self):
        """Aurora supports JSON type"""
        return exclusions.open()


    @property
    def unicode_connections(self):
        """Aurora supports unicode connections"""
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
    def savepoints(self):
        """Aurora Data API may not support savepoints"""
        return exclusions.closed()

    @property
    def two_phase_transactions(self):
        """Aurora Data API does not support two-phase transactions"""
        return exclusions.closed()

    @property
    def schemas(self):
        """Aurora supports schemas (databases in MySQL terms)"""
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
        """Aurora Data API only supports millisecond precision (3 digits)
        
        Reference: https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api-operations.html
        """
        return exclusions.closed()

    @property
    def time_microseconds(self):
        """Aurora Data API only supports millisecond precision (3 digits)
                
        Reference: https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api-operations.html
        """
        return exclusions.closed()

    @property
    def timestamp_microseconds(self):
        """target dialect supports representation of Python datetime.datetime() with microsecond objects but only if TIMESTAMP is used."""
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

    # All requirements that are closed() in SQLAlchemy base - set to open() for manual testing
    # These will be closed one by one as we find issues

    @property
    def table_ddl_if_exists(self):
        """target platform supports IF NOT EXISTS / IF EXISTS for tables."""
        return exclusions.open()

    @property
    def index_ddl_if_exists(self):
        """target platform supports IF NOT EXISTS / IF EXISTS for indexes."""
        return exclusions.open()

    @property
    def uuid_data_type(self):
        """Return databases that support the UUID datatype."""
        return exclusions.open()

    @property
    def foreign_keys_reflect_as_index(self):
        """Target database creates an index that's reflected for foreign keys."""
        return exclusions.open()

    @property
    def unique_index_reflect_as_unique_constraints(self):
        """Target database reflects unique indexes as unique constrains."""
        return exclusions.open()

    @property
    def unique_constraints_reflect_as_index(self):
        """Target database reflects unique constraints as indexes."""
        return exclusions.open()

    @property
    def table_value_constructor(self):
        """Database / dialect supports a query like:
        SELECT * FROM VALUES ( (c1, c2), (c1, c2), ...) AS some_table(col1, col2)
        """
        return exclusions.open()

    @property
    def boolean_col_expressions(self):
        """Target database must support boolean expressions as columns"""
        return exclusions.open()

    @property
    def non_updating_cascade(self):
        """target database must *not* support ON UPDATE..CASCADE behavior in foreign keys."""
        return exclusions.open()

    @property
    def deferrable_fks(self):
        return exclusions.open()

    @property
    def nullsordering(self):
        """Target backends that support nulls ordering."""
        return exclusions.open()

    @property
    def intersect(self):
        """Target database must support INTERSECT or equivalent."""
        return exclusions.open()

    @property
    def except_(self):
        """Target database must support EXCEPT or equivalent (i.e. MINUS)."""
        return exclusions.open()

    @property
    def window_functions(self):
        """Target database must support window functions."""
        return exclusions.open()

    @property
    def ctes(self):
        """Target database supports CTEs"""
        return exclusions.open()

    @property
    def ctes_with_update_delete(self):
        """target database supports CTES that ride on top of a normal UPDATE or DELETE statement which refers to the CTE in a correlated subquery."""
        return exclusions.open()

    @property
    def ctes_with_values(self):
        """target database supports CTES that ride on top of a VALUES clause."""
        return exclusions.open()

    @property
    def ctes_on_dml(self):
        """target database supports CTES which consist of INSERT, UPDATE or DELETE *within* the CTE, e.g. WITH x AS (UPDATE....)"""
        return exclusions.open()

    @property
    def tuple_in(self):
        """Target platform supports the syntax "(x, y) IN ((x1, y1), (x2, y2), ...)" """
        return exclusions.open()

    @property
    def emulated_lastrowid(self):
        """target dialect retrieves cursor.lastrowid, or fetches from a database-side function after an insert() construct executes, within the get_lastrowid() method."""
        return exclusions.open()

    @property
    def emulated_lastrowid_even_with_sequences(self):
        """target dialect retrieves cursor.lastrowid or an equivalent after an insert() construct executes, even if the table has a Sequence on it."""
        return exclusions.open()

    @property
    def views(self):
        """Target database must support VIEWs."""
        return exclusions.open()

    @property
    def cross_schema_fk_reflection(self):
        """target system must support reflection of inter-schema foreign keys"""
        return exclusions.open()

    @property
    def foreign_key_constraint_name_reflection(self):
        """Target supports reflection of FOREIGN KEY constraints and will return the name of the constraint that was used in the "CONSTRAINT <name> FOREIGN KEY" DDL."""
        return exclusions.open()

    @property
    def implicit_default_schema(self):
        """target system has a strong concept of 'default' schema that can be referred to implicitly. basically, PostgreSQL."""
        return exclusions.open()

    @property
    def default_schema_name_switch(self):
        """target dialect implements provisioning module including set_default_schema_on_connection"""
        return exclusions.open()

    @property
    def reflects_pk_names(self):
        return exclusions.open()

    @property
    def reflect_tables_no_columns(self):
        """target database supports creation and reflection of tables with no columns, or at least tables that seem to have no columns."""
        return exclusions.open()

    @property
    def temp_table_comment_reflection(self):
        """indicates if database supports comments on temp tables and the dialect can reflect them"""
        return exclusions.open()

    @property
    def comment_reflection(self):
        """Indicates if the database support table comment reflection"""
        return exclusions.open()

    @property
    def comment_reflection_full_unicode(self):
        """Indicates if the database support table comment reflection in the full unicode range, including emoji etc."""
        return exclusions.open()

    @property
    def constraint_comment_reflection(self):
        """indicates if the database support comments on constraints and their reflection"""
        return exclusions.open()

    @property
    def schema_create_delete(self):
        """target database supports schema create and dropped with 'CREATE SCHEMA' and 'DROP SCHEMA'"""
        return exclusions.open()

    @property
    def foreign_key_constraint_option_reflection_ondelete(self):
        return exclusions.open()

    @property
    def fk_constraint_option_reflection_ondelete_restrict(self):
        return exclusions.open()

    @property
    def fk_constraint_option_reflection_ondelete_noaction(self):
        return exclusions.open()

    @property
    def foreign_key_constraint_option_reflection_onupdate(self):
        return exclusions.open()

    @property
    def fk_constraint_option_reflection_onupdate_restrict(self):
        return exclusions.open()

    @property
    def temp_table_names(self):
        """target dialect supports listing of temporary table names"""
        return exclusions.open()

    @property
    def has_temp_table(self):
        """target dialect supports checking a single temp table name"""
        return exclusions.open()

    @property
    def temporary_views(self):
        """target database supports temporary views"""
        return exclusions.open()

    @property
    def index_reflects_included_columns(self):
        return exclusions.open()

    @property
    def reflect_indexes_with_ascdesc_as_expression(self):
        """target database supports reflecting INDEX with per-column ASC/DESC but reflects them as expressions (like oracle)."""
        return exclusions.open()

    @property
    def indexes_with_expressions(self):
        """target database supports CREATE INDEX against SQL expressions."""
        return exclusions.open()

    @property
    def reflect_indexes_with_expressions(self):
        """target database supports reflection of indexes with SQL expressions."""
        return exclusions.open()

    @property
    def inline_check_constraint_reflection(self):
        """target dialect supports reflection of inline check constraints"""
        return exclusions.open()

    @property
    def check_constraint_reflection(self):
        """target dialect supports reflection of check constraints"""
        return exclusions.open()

    @property
    def nvarchar_types(self):
        """target database supports NVARCHAR and NCHAR as an actual datatype"""
        return exclusions.open()

    @property
    def unicode_ddl(self):
        """Target driver must support some degree of non-ascii symbol names."""
        return exclusions.open()

    @property
    def datetime_interval(self):
        """Aurora Data API does not support INTERVAL data type.

        Reference: Reference: https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api-operations.html
        INTERVAL type returns UnsupportedResultException via Aurora Data API.
        """
        return exclusions.closed()

    @property
    def datetime_literals(self):
        """target dialect supports rendering of a date, time, or datetime as a literal string, e.g. via the TypeEngine.literal_processor() method."""
        return exclusions.open()

    @property
    def datetime_timezone(self):
        """Aurora Data API does not support timezone-aware datetime types.

        Reference: https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api-operations.html
        Aurora Data API does not support timezone-aware types.
        """
        return exclusions.closed()

    @property
    def time_timezone(self):
        """Aurora Data API does not support timezone-aware time types.

        Reference: https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api-operations.html
        Aurora Data API does not support timezone-aware types.
        """
        return exclusions.closed()

    @property
    def datetime_historic(self):
        """target dialect supports representation of Python datetime.datetime() objects with historic (pre 1970) values."""
        return exclusions.open()

    @property
    def date_historic(self):
        """target dialect supports representation of Python datetime.datetime() objects with historic (pre 1970) values."""
        return exclusions.open()

    @property
    def autocommit(self):
        """target dialect supports 'AUTOCOMMIT' as an isolation_level"""
        return exclusions.open()

    @property
    def isolation_level(self):
        """target dialect supports general isolation level settings."""
        return exclusions.open()

    @property
    def array_type(self):
        """Aurora Data API does not support array types.

        Reference: https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/data-api.differences.html
        Aurora Serverless v2's Data API does not support multidimensional array columns.
        """
        return exclusions.closed()

    @property
    def json_array_indexes(self):
        """Aurora Data API does not support PostgreSQL JSON operators like #>, #>>, ->.

        Error: "operator does not exist: json #> text"
        Aurora Data API appears to have limited support for PostgreSQL-specific JSON operators.
        """
        return exclusions.closed()

    @property
    def legacy_unconditional_json_extract(self):
        """Aurora Data API does not support PostgreSQL JSON operators like #>, #>>, ->.

        PostgreSQL JSON operators (#>, #>>, ->) are not available via Aurora Data API,
        causing "operator does not exist" errors in JSON path queries.
        """
        return exclusions.closed()

    @property
    def precision_numerics_enotation_small(self):
        """target backend supports Decimal() objects using E notation to represent very small values."""
        return exclusions.open()

    @property
    def server_defaults(self):
        """Target backend supports server side defaults for columns"""
        return exclusions.open()

    @property
    def expression_server_defaults(self):
        """Target backend supports server side defaults with SQL expressions for columns"""
        return exclusions.open()

    @property
    def precision_numerics_retains_significant_digits(self):
        """A precision numeric type will return empty significant digits, i.e. a value such as 10.000 will come back in Decimal form with the .000 maintained."""
        return exclusions.open()

    @property
    def infinity_floats(self):
        """Aurora Data API does not support NaN and Infinity values.

        Reference: AWS error message "UnsupportedResultException: NaN and Infinity values are not supported"
        """
        return exclusions.closed()

    @property
    def float_or_double_precision_behaves_generically(self):
        return exclusions.open()

    @property
    def update_from(self):
        """Target must support UPDATE..FROM syntax"""
        return exclusions.open()

    @property
    def delete_from(self):
        """Target must support DELETE FROM..FROM or DELETE..USING syntax"""
        return exclusions.open()

    @property
    def mod_operator_as_percent_sign(self):
        """target database must use a plain percent '%' as the 'modulus' operator."""
        return exclusions.open()

    @property
    def percent_schema_names(self):
        """target backend supports weird identifiers with percent signs in them, e.g. 'some % column'."""
        return exclusions.open()

    @property
    def order_by_label_with_expression(self):
        """target backend supports ORDER BY a column label within an expression."""
        return exclusions.open()

    @property
    def async_dialect(self):
        """dialect makes use of await_() to invoke operations on the DBAPI."""
        return exclusions.open()

    @property
    def computed_columns(self):
        "Supports computed columns"
        return exclusions.open()

    @property
    def computed_columns_stored(self):
        "Supports computed columns with `persisted=True`"
        return exclusions.open()

    @property
    def computed_columns_virtual(self):
        "Supports computed columns with `persisted=False`"
        return exclusions.open()

    @property
    def computed_columns_default_persisted(self):
        """If the default persistence is virtual or stored when `persisted` is omitted"""
        return exclusions.open()

    @property
    def computed_columns_reflect_persisted(self):
        """If persistence information is returned by the reflection of computed columns"""
        return exclusions.open()

    @property
    def identity_columns(self):
        """If a backend supports GENERATED { ALWAYS | BY DEFAULT } AS IDENTITY"""
        return exclusions.open()

    @property
    def identity_columns_standard(self):
        """If a backend supports GENERATED { ALWAYS | BY DEFAULT } AS IDENTITY with a standard syntax. This is mainly to exclude MSSql."""
        return exclusions.open()

    @property
    def regexp_match(self):
        """backend supports the regexp_match operator."""
        return exclusions.open()

    @property
    def regexp_replace(self):
        """backend supports the regexp_replace operator."""
        return exclusions.open()

    @property
    def fetch_first(self):
        """backend supports the fetch first clause."""
        return exclusions.open()

    @property
    def fetch_percent(self):
        """backend supports the fetch first clause with percent."""
        return exclusions.open()

    @property
    def fetch_ties(self):
        """backend supports the fetch first clause with ties."""
        return exclusions.open()

    @property
    def fetch_no_order_by(self):
        """backend supports the fetch first without order by"""
        return exclusions.open()

    @property
    def fetch_offset_with_options(self):
        """backend supports the offset when using fetch first with percent or ties. basically this is "not mssql" """
        return exclusions.open()

    @property
    def fetch_expression(self):
        """backend supports fetch / offset with expression in them, like SELECT * FROM some_table OFFSET 1 + 1 ROWS FETCH FIRST 1 + 1 ROWS ONLY"""
        return exclusions.open()

    @property
    def reflect_table_options(self):
        """Target database must support reflecting table_options."""
        return exclusions.open()

    @property
    def materialized_views(self):
        """Target database must support MATERIALIZED VIEWs."""
        return exclusions.open()

    @property
    def materialized_views_reflect_pk(self):
        """Target database reflect MATERIALIZED VIEWs pks."""
        return exclusions.open()

    @property
    def supports_bitwise_or(self):
        """Target database supports bitwise or"""
        return exclusions.open()

    @property
    def supports_bitwise_and(self):
        """Target database supports bitwise and"""
        return exclusions.open()

    @property
    def supports_bitwise_not(self):
        """Target database supports bitwise not"""
        return exclusions.open()

    @property
    def supports_bitwise_xor(self):
        """Target database supports bitwise xor"""
        return exclusions.open()

    @property
    def supports_bitwise_shift(self):
        """Target database supports bitwise left or right shift"""
        return exclusions.open()

    # Aurora Data API numeric precision limitations

    @property
    def numeric_received_as_decimal_untyped(self):
        """Aurora Data API returns NUMERIC/DECIMAL as float, not Decimal.

        Aurora Data API Value structure only supports doubleValue (Double) for numeric types,
        not a dedicated decimal field. This causes precision loss for exact decimal values.
        Reference: https://docs.aws.amazon.com/rdsdataservice/latest/APIReference/API_Value.html
        """
        return exclusions.closed()

    @property
    def precision_generic_float_type(self):
        """Aurora Data API converts NUMERIC to float with potential precision loss.

        Due to the doubleValue limitation in Aurora Data API, exact decimal precision
        cannot be guaranteed for all numeric values.
        """
        return exclusions.closed()


