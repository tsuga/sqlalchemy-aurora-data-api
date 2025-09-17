from sqlalchemy.testing.suite import *  # noqa: F403
from sqlalchemy import testing
import pytest

from sqlalchemy.testing.suite.test_types import JSONTest as _JSONTest  # noqa
from sqlalchemy.testing.suite.test_insert import InsertBehaviorTest as _InsertBehaviorTest  # noqa
from sqlalchemy.testing.suite.test_dialect import DifficultParametersTest as _DifficultParametersTest  # noqa
from sqlalchemy.testing import mock, engines, eq_
from sqlalchemy import select
import json


# Override InsertBehaviorTest to handle Aurora Data API specific behavior
class InsertBehaviorTest(_InsertBehaviorTest):  # noqa: F811
    def test_no_results_for_non_returning_insert(self, connection):
        """Override this test for Aurora Data API.

        Aurora Data API supports RETURNING clauses but handles implicit_returning=False
        tables differently than standard PostgreSQL. Aurora's behavior differs from
        the expected PostgreSQL behavior in this test.

        Reference: Aurora supports RETURNING but not generatedFields.
        """
        pytest.skip("Aurora Data API: implicit_returning=False table behavior differs from standard PostgreSQL")


class JSONTest(_JSONTest):
    def test_round_trip_custom_json(self):
        """Override this test for Aurora Data API.

        Aurora Data API returns JSON with compact formatting (no spaces).
        The test expects standard json.dumps() format: '{"key1": "data1"}'
        But Aurora returns compact format: '{"key1":"data1"}'
        Both are valid JSON, but the test is strict about whitespace formatting.
        Avoiding runtime JSON re-parsing for performance reasons.
        """
        data_table = self.tables.data_table
        data_element = {"key1": "data1"}

        js = mock.Mock(side_effect=json.dumps)
        jd = mock.Mock(side_effect=json.loads)
        engine = engines.testing_engine(
            options=dict(json_serializer=js, json_deserializer=jd)
        )

        # support sqlite :memory: database...
        data_table.create(engine, checkfirst=True)
        with engine.begin() as conn:
            conn.execute(
                data_table.insert(), {"name": "row1", "data": data_element}
            )
            row = conn.execute(select(data_table.c.data)).first()

            eq_(row, (data_element,))
            eq_(js.mock_calls, [mock.call(data_element)])
            if testing.requires.json_deserializer_binary.enabled:
                eq_(
                    jd.mock_calls,
                    [mock.call(json.dumps(data_element).encode())],
                )
            else:
                # Aurora Data API returns JSON without spaces
                expected_json = json.dumps(data_element, separators=(',', ':'))
                eq_(jd.mock_calls, [mock.call(expected_json)])

# Override DifficultParametersTest to skip problematic parameter tests
class DifficultParametersTest(_DifficultParametersTest):
    """Override to skip tests that fail due to Aurora Data API parameter naming restrictions."""

    @pytest.mark.skip(reason="Aurora Data API doesn't support special characters in parameter names")
    def test_standalone_bindparam_escape(self, *args, **kwargs):
        pass

    @pytest.mark.skip(reason="Aurora Data API doesn't support special characters in parameter names")
    def test_standalone_bindparam_escape_expanding(self, *args, **kwargs):
        pass
