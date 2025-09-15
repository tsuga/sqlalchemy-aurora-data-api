import datetime
import re
import decimal

from sqlalchemy import cast, func
import sqlalchemy.sql.sqltypes as sqltypes
from sqlalchemy.dialects.postgresql import JSON, JSONB, UUID, DATE, TIME, TIMESTAMP, ARRAY, ENUM


class _ADA_SA_JSON(sqltypes.JSON):
    def bind_expression(self, value):
        return cast(value, sqltypes.JSON)


class _ADA_JSON(JSON):
    def bind_expression(self, value):
        return cast(value, JSON)


class _ADA_JSONB(JSONB):
    def bind_expression(self, value):
        return cast(value, JSONB)


class _ADA_UUID(UUID):
    def bind_expression(self, value):
        return cast(value, UUID)

    def result_processor(self, dialect, coltype):
        import uuid
        def process(value):
            if isinstance(value, str):
                # Check if as_uuid=False was specified
                if hasattr(self, 'as_uuid') and not self.as_uuid:
                    return value  # Return as string
                return uuid.UUID(value)
            return value
        return process


class _ADA_ENUM(ENUM):
    def bind_expression(self, value):
        return cast(value, self)


# TODO: is TZ awareness needed here?
class _ADA_DATETIME_MIXIN:
    iso_ts_re = re.compile(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+")

    @staticmethod
    def ms(value):
        # Three digit fractional second component, truncated and zero padded. This is what the data api requires.
        return str(value.microsecond).zfill(6)[:-3]

    def bind_processor(self, dialect):
        def process(value):
            return value.isoformat() if isinstance(value, self.py_type) else value

        return process

    def bind_expression(self, value):
        return cast(value, self.sa_type)

    def result_processor(self, dialect, coltype):
        def process(value):
            # When the microsecond component ends in zeros, they are omitted from the return value,
            # and datetime.datetime.fromisoformat can't parse the result (example: '2019-10-31 09:37:17.31869
            # '). Pad it.
            if isinstance(value, str) and self.iso_ts_re.match(value):
                value = self.iso_ts_re.sub(lambda match: match.group(0).ljust(26, "0"), value)
            if isinstance(value, str):
                try:
                    return self.py_type.fromisoformat(value)
                except AttributeError:  # fromisoformat not supported on Python < 3.7
                    if self.py_type == datetime.date:
                        return datetime.datetime.strptime(value, "%Y-%m-%d").date()
                    if self.py_type == datetime.time:
                        return datetime.datetime.strptime(value, "%H:%M:%S").time()
                    if "." in value:
                        return datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f")
                    return datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            return value

        return process


class _ADA_DATE(_ADA_DATETIME_MIXIN, DATE):
    py_type = datetime.date
    sa_type = sqltypes.Date

    def bind_processor(self, dialect):
        def process(value):
            return value.strftime("%Y-%m-%d") if isinstance(value, self.py_type) else value

        return process


class _ADA_TIME(_ADA_DATETIME_MIXIN, TIME):
    py_type = datetime.time
    sa_type = sqltypes.Time

    def bind_processor(self, dialect):
        def process(value):
            return value.strftime("%H:%M:%S.") + self.ms(value) if isinstance(value, self.py_type) else value

        return process


class _ADA_TIMESTAMP(_ADA_DATETIME_MIXIN, TIMESTAMP):
    py_type = datetime.datetime
    sa_type = sqltypes.DateTime

    def bind_processor(self, dialect):
        def process(value):
            return value.strftime("%Y-%m-%d %H:%M:%S.") + self.ms(value) if isinstance(value, self.py_type) else value

        return process




class _ADA_NUMERIC(sqltypes.Numeric):
    def result_processor(self, dialect, coltype):
        def process(value):
            if value is None:
                return value

            # Aurora Data API returns numeric values as float (doubleValue)
            # For asdecimal=True (default), convert float to Decimal
            if self.asdecimal and isinstance(value, float):
                return decimal.Decimal(str(value))

            # Handle asdecimal=False case: return float as-is
            if not self.asdecimal:
                if isinstance(value, decimal.Decimal):
                    return float(value)
                return float(value) if not isinstance(value, float) else value

            # For other cases (already Decimal), return as-is
            return value
        return process


class _ADA_FLOAT(sqltypes.Float):
    """Aurora Data API Float type to distinguish from Numeric."""
    pass


class _ADA_DOUBLE(sqltypes.Double):
    """Aurora Data API Double type to distinguish from Numeric."""
    pass


class _ADA_ARRAY(ARRAY):
    def bind_processor(self, dialect):
        def process(value):
            # FIXME: escape strings properly here
            return "\v".join(value) if isinstance(value, list) else value

        return process

    def bind_expression(self, value):
        return func.string_to_array(value, "\v")
