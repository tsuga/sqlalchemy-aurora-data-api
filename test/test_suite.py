# from sqlalchemy.testing.suite import *
from sqlalchemy import testing

from sqlalchemy.testing.suite.test_select import *  # noqa

# from sqlalchemy.testing.suite import (
#     ComponentReflectionTest as _ComponentReflectionTest,
# )
# from sqlalchemy.testing.suite import (
#     ExpandingBoundInTest as _ExpandingBoundInTest,
# )
# from sqlalchemy.testing.suite import InsertBehaviorTest as _InsertBehaviorTest
# from sqlalchemy.testing.suite import (
#     LongNameBlowoutTest as _LongNameBlowoutTest,
# )
# from sqlalchemy.testing.suite import NumericTest as _NumericTest
# from sqlalchemy.testing.suite import OrderByLabelTest as _OrderByLabelTest


# class ComponentReflectionTest(_ComponentReflectionTest):
#     @testing.skip("aurora")
#     def test_get_foreign_keys(self):
#         # Aurora Data API may not support all foreign key reflection options
#         return


# class ExpandingBoundInTest(_ExpandingBoundInTest):
#     @testing.skip("aurora")
#     def test_null_in_empty_set_is_false_bindparam(self):
#         # Aurora Data API may handle empty sets differently
#         return

#     @testing.skip("aurora")
#     def test_null_in_empty_set_is_false_direct(self):
#         return

#     @testing.skip("aurora")
#     def test_null_in_empty_set_is_false(self):
#         return


# class InsertBehaviorTest(_InsertBehaviorTest):
#     @testing.skip("aurora")
#     def test_empty_insert(self):
#         # Aurora Data API may not support empty inserts
#         return

#     @testing.skip("aurora")
#     def test_empty_insert_multiple(self):
#         # Aurora Data API may not support empty inserts
#         return


# class LongNameBlowoutTest(_LongNameBlowoutTest):
#     @testing.skip("aurora")
#     def test_long_convention_name(self):
#         # Aurora Data API may have identifier length limitations
#         return


# class NumericTest(_NumericTest):
#     @testing.skip("aurora")
#     def test_decimal_coerce_round_trip(self):
#         # Aurora Data API decimal handling may differ
#         return

#     @testing.skip("aurora")
#     def test_decimal_coerce_round_trip_w_cast(self):
#         # Aurora Data API decimal handling may differ
#         return


# class OrderByLabelTest(_OrderByLabelTest):
#     @testing.skip("aurora")
#     def test_composed_multiple(self):
#         # Complex ORDER BY statements may not be supported
#         return