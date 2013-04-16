"""
kalapy.db.engines.utils
~~~~~~~~~~~~~~~~~~~~~~~

This module defines several utility functions to type cast values from
python to database and vice versa.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LICENSE for more details.
"""
import re, decimal, datetime


re_datetime = re.compile(
    "(\d+)-(\d+)-(\d+) (\d+):(\d+):(\d+)(?:.(\d+)(?:-(\d+))?)?")

def datetime_to_python(value):
    """Convert the string date value in python datetime.datetime striping out
    tzinfo as we always store the datetime with UTC timezone. The `DateTime`
    field should convert user input datetime values to UTC datetime considering
    current timezone.

    >>> datetime_to_python('2010-05-07 11:34:00.530134-05')
    datetime.datetime(2010, 5, 7, 11, 34, 00, 530134)
    >>> datetime_to_python('2009-07-11 09:57:00-05')
    datetime.datetime(2009, 7, 11, 9, 57, 0)

    :returns: datetime.datetime instance
    """
    if not value: return None
    times = list(re_datetime.match(value).groups())

    # strip out the timezone info
    if len(times) == 8:
        times.pop()

    # no microseconds?
    if times[-1] is None:
        times.pop()

    return datetime.datetime(*map(int, times))

def decimal_to_python(value):
    """Convert the given value into decimal.Decimal
    """
    if value is None: return None
    return decimal.Decimal(value)

def decimal_to_database(value):
    """Convert the given decimal.Decimal value to
    string to be stored in database.
    """
    if value is None: return None
    return str(value)

def str_to_database(value):
    """Adapter to convert string value into unicode
    if database doesn't support str values.
    """
    return value.decode('utf-8')

