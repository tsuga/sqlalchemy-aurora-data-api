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
    def index_reflection(self):
        """Aurora Data API doesn't support generate_subscripts function needed for index reflection.

        AWS limitation: The generate_subscripts(int2vector, bigint) function does not exist
        in Aurora PostgreSQL via Data API. This function is required by SQLAlchemy's
        PostgreSQL dialect for complex index reflection operations.
        FIXME: This may have impact on Alembic
        """
        # return exclusions.closed()
        return exclusions.open()


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

    # @property
    # def json_deserializer_binary(self):
    #     """Aurora Data API returns JSON with compact formatting (no spaces).

    #     The test expects standard json.dumps() format: '{"key1": "data1"}'
    #     But Aurora returns compact format: '{"key1":"data1"}'
    #     Both are valid JSON, but the test is strict about whitespace formatting.
    #     Avoiding runtime JSON re-parsing for performance reasons.
    #     """
    #     return exclusions.closed()

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
        """Aurora Data API has limitations with index DDL due to reflection issues.

        Index DDL operations fail because they rely on index reflection which uses
        the unsupported generate_subscripts function. Aurora supports the DDL syntax
        but the tests fail due to reflection limitations.
        FIXME: This may have impact on Alembic
        """
        # return exclusions.closed()
        return exclusions.open()
        

    @property
    def uuid_data_type(self):
        """Return databases that support the UUID datatype."""
        return exclusions.open()

    @property
    def foreign_keys_reflect_as_index(self):
        """PostgreSQL does not automatically create indexes for foreign key constraints.

        Unlike some databases, PostgreSQL and Aurora PostgreSQL require explicit
        index creation for foreign key columns. Foreign key constraints themselves
        are created, but associated indexes must be manually added if needed for
        performance optimization.
        PG does not support this as per DefaultRequirements
        """
        return exclusions.closed()

    @property
    def unique_index_reflect_as_unique_constraints(self):
        """Target database reflects unique indexes as unique constrains.
        PG does not support this as per DefaultRequirements"""
        return exclusions.closed()

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
        """target database must *not* support ON UPDATE..CASCADE behavior in foreign keys.
        PG does not support this as per DefaultRequirements"""
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
        """Aurora Data API has limitations with schema switching and search_path persistence.

        While SET search_path works within a transaction, Aurora Data API's session management
        may not persist schema changes across connections in the same way as standard PostgreSQL.
        The _get_default_schema_name method needs proper implementation to query current search_path.

        TODO: Investigate Aurora Data API session management and implement proper schema switching
        that works with SQLAlchemy's event-driven schema change mechanism.
        """
        return exclusions.closed()

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
        """Aurora Data API has complex schema resolution for temporary tables in pg_temp schemas.

        FIXME: Further investigation needed for temporary table reflection
        Current implementation in _get_table_oids handles TEMPORARY scope but get_columns still fails
        with NoSuchTableError for temporary tables like user_tmp_main.
        The relpersistence column handling may need Aurora-specific overrides.
        """
        return exclusions.closed()

    @property
    def temporary_views(self):
        """Aurora Data API has complex schema resolution for temporary views in pg_temp schemas.

        FIXME: Further investigation needed for temporary view reflection
        Similar issues as temporary tables with schema resolution in pg_temp schemas.
        The relpersistence column handling may need Aurora-specific overrides.
        """
        return exclusions.closed()

    @property
    def index_reflects_included_columns(self):
        """Aurora Data API does not support reflecting covering indexes with INCLUDE columns.

        Technical limitation: PostgreSQL covering indexes with INCLUDE clause are not properly
        reflected via Aurora Data API. When testing:

        CREATE INDEX t_idx ON t (x) INCLUDE (y)

        The get_indexes() method returns an empty array [] instead of the expected:
        [{'name': 't_idx', 'column_names': ['x'], 'include_columns': ['y'], 'unique': False}]

        This indicates Aurora Data API's metadata retrieval limitations for complex index
        structures that include non-key columns via the INCLUDE clause.

        FIXME: Further investigation needed to determine if this is a fundamental Aurora
        Data API limitation or if custom reflection logic can be implemented.
        """
        return exclusions.closed()

    @property
    def reflect_indexes_with_ascdesc_as_expression(self):
        """target database supports reflecting INDEX with per-column ASC/DESC but reflects them as expressions (like oracle).
        Supported only on Oracle as per DefaultRequirements"""
        return exclusions.closed()

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
        """target database supports NVARCHAR and NCHAR as an actual datatype
        Not supported on PG as per DefaultRequirements"""
        return exclusions.closed()

    @property
    def unicode_ddl(self):
        """Aurora Data API doesn't support Unicode characters in parameter names.

        AWS limitation: Named parameter syntax with Unicode characters is invalid.
        The Aurora Data API validates parameter names and rejects Unicode characters.
        """
        return exclusions.closed()

    @property
    def unusual_column_name_characters(self):
        """Aurora Data API has strict limitations on parameter naming and special character handling.

        AWS limitation: Named parameter syntax with special characters like
        slashes (/), question marks (?), parentheses ((, )), and other non-alphanumeric characters
        are invalid. Aurora Data API validates parameter names strictly and
        rejects names containing special characters.

        This affects multiple test categories:
        - test_round_trip_same_named_column: Column names with special characters
        - test_standalone_bindparam_escape: Bind parameters with special characters
        - test_standalone_bindparam_escape_expanding: Expanding bind parameters with special characters
        - BizarroCharacterTest: Table/column names with parentheses like "(2)", "(3)"

        Actual error from Aurora Data API:
        "botocore.exceptions.ClientError: An error occurred (ValidationException)
         when calling the ExecuteStatement operation: Named parameter syntax is
         invalid, input: /slashes/"

        FIXME: Further investigation needed for special character table name handling
        BizarroCharacterTest failures indicate that special character table names
        are not being properly reflected/filtered in system tables. This may be
        related to pg_table_is_visible function or schema filtering logic.
        """
        return exclusions.closed()

    @property
    def standalone_bindparam_escape(self):
        """Aurora Data API parameter escaping with unusual characters not supported.

        Related to unusual_column_name_characters - Aurora Data API's strict
        parameter validation prevents use of special characters in bind parameter
        names, affecting standalone parameter escaping functionality.

        Same ValidationException errors occur for parameters with /, ?, and other
        special characters.
        """
        return exclusions.closed()

    @property
    def standalone_bindparam_escape_expanding(self):
        """Aurora Data API expanding parameter escaping with unusual characters not supported.

        Related to unusual_column_name_characters - Aurora Data API's strict
        parameter validation prevents use of special characters in bind parameter
        names, affecting expanding parameter escaping functionality.

        Same ValidationException errors occur for parameters with /, ?, and other
        special characters.
        """
        return exclusions.closed()

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
        """Aurora Data API has different autocommit semantics than SQLAlchemy expects.

        SQLAlchemy's AUTOCOMMIT mode expects transactions to start normally but
        have rollback/commit operations be no-ops, with data persisting after rollback.

        Aurora Data API's skip_begin_transaction avoids transactions entirely,
        which is a different behavioral model.

        TODO: Implement Aurora-specific AUTOCOMMIT behavior that matches SQLAlchemy's
        expectations by overriding do_rollback/do_commit to be no-ops in AUTOCOMMIT mode.
        """
        return exclusions.closed()

    @property
    def isolation_level(self):
        """Aurora Data API has limitations with session-level isolation level settings.

        While Aurora PostgreSQL supports standard isolation levels, the Data API
        may not properly handle session-level isolation level changes with
        'SET SESSION TRANSACTION ISOLATION LEVEL' commands.

        Test failures show that isolation levels are not being applied correctly:
        - AssertionError: 'READ COMMITTED' != 'SERIALIZABLE'
        - AssertionError: 'READ COMMITTED' != 'READ UNCOMMITTED'

        This suggests that isolation level changes do not persist or take effect
        as expected through the Aurora Data API interface.

        TODO: Investigate if Aurora Data API supports session-level isolation
        level changes, or if transaction-level settings are required.
        """
        return exclusions.closed()

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
        """PostgreSQL does not support virtual (non-persisted) computed columns.

        PostgreSQL only supports STORED (persisted) generated columns via
        GENERATED ALWAYS AS (...) STORED syntax. Virtual columns that compute
        on-the-fly are not supported until PostgreSQL 18.

        Reference: https://www.postgresql.org/docs/current/ddl-generated-columns.html
        """
        return exclusions.closed()

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
        """Aurora Data API does not support identity column reflection due to system table limitations.

        Technical limitation: Identity column reflection fails with:
        ERROR: column "id1" of relation "pg_stats_ext" does not exist; SQLState: 42703

        This is the same pg_stats_ext system table issue identified earlier. The identity
        column reflection logic uses complex queries that reference Aurora Data API
        unsupported system table structures, including:
        - pg_stats_ext table column structure inconsistencies
        - Complex joins with pg_sequence, pg_class, pg_attribute tables
        - Advanced metadata queries using pg_get_serial_sequence() function

        While Aurora PostgreSQL supports GENERATED ALWAYS AS IDENTITY syntax for creating
        identity columns, the reflection (metadata introspection) functionality is limited
        by Aurora Data API's system catalog access restrictions.

        FIXME: Further investigation needed to implement simplified identity column
        reflection that avoids problematic system table queries.
        """
        return exclusions.closed()

    @property
    def identity_columns_standard(self):
        """Aurora Data API identity column standard syntax support limited by reflection issues.

        Related to identity_columns requirement - while the DDL syntax is supported,
        reflection limitations prevent proper testing of standard identity column behavior.
        """
        return exclusions.closed()

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
        """Aurora Data API does not support FETCH FIRST with PERCENT.

        Error: "syntax error at or near 'PERCENT'"
        Aurora PostgreSQL does not fully support the FETCH FIRST n PERCENT syntax.
        Reference: AWS documentation recommends calculating percentage manually and using LIMIT.
        """
        return exclusions.closed()

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
        """Aurora Data API does not support OFFSET with PERCENT options.

        Since FETCH FIRST n PERCENT is not supported, offset with percent options
        is also not available in Aurora Data API.
        """
        return exclusions.closed()

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
        """Aurora Data API does not support bitwise shift operators (<< and >>).

        Error: "operator does not exist: integer << bigint"
        While PostgreSQL supports these operators, Aurora Data API reports them as undefined.
        """
        return exclusions.closed()

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

    @property
    def insert_executemany_returning(self):
        """Aurora Data API has inconsistent returns_rows behavior for no_implicit_returning tables.

        When using return_defaults() with executemany on tables that have implicit_returning=False,
        the result still returns rows, but the test expects returns_rows=False.

        FIXME: This may be correct behavior - table-level implicit_returning=False should only
        affect implicit RETURNING, not explicit return_defaults(). Need to investigate if this
        test expectation is appropriate for Aurora Data API's PostgreSQL RETURNING support.

        Reference: Aurora supports RETURNING clause but not generatedFields.
        """
        return exclusions.closed()


