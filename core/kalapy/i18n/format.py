# -*- coding: utf-8 -*-
"""
kalapy.i18n.format
~~~~~~~~~~~~~~~~~~

This module implements i18n format functions.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LICENSE for more details.
"""
from datetime import datetime
from decimal import Decimal

from babel import numbers, dates

from kalapy.i18n.utils import get_locale


def format_date(date=None, format='medium'):
    """Returns a date formated according to the given format in the context
    of current locale. If `date` is None, current date is assumed.

    :param date: an instance of :class:`~datetime.date` or None
    :param format: format pattern, one of `short`, `medium`, `long` or `full`.
    :returns: formated date as string
    """
    return dates.format_date(date, format=format, locale=get_locale())


def format_time(time=None, format='medium'):
    """Returns a time formated according to the given format in the context
    of current locale. If `time` is None, current time is assumed.

    :param time: an instance of :class:`~datetime.time` or None
    :param format: format pattern, one of `short`, `medium`, `long` or `full`.
    :returns: formated time as string
    """
    return dates.format_time(time, format=format, locale=get_locale())


def format_datetime(datetime=None, format='medium'):
    """Returns a datetime formated according to the given format in the context
    of current locale. If `datetime` is None, current time is assumed.

    :param datetime: an instance of :class:`~datetime.datetime` or None
    :param format: format pattern, one of `short`, `medium`, `long` or `full`.
    :returns: formated datetime as string
    """
    return dates.format_datetime(datetime, format=format, locale=get_locale())


def format_number(number):
    """Returns a formatted decimal value in the context of current locale.

    :param number: an integer value
    """
    return dates.format_number(number, locale=get_locale())


def format_decimal(decimal, digits=2):
    """Returns a formatted decimal value in the context of current locale. The
    appropriate thousands grouping and the decimal separator are used according
    to the current locale.

    For example::

        >>> format_decimal(12345.4321, digits=2)
        ... '12,345.43'
        >>> format_decimal(Decimal('12345.4321'), digits=2)
        ... '12,345.43'


    :param decimal: a float or Decimal value
    :param digits: number of digits to the right of decimal seperator
    """
    locale = get_locale()
    value = ('%%.%df' % digits) % decimal
    num, decimals = value.split('.')
    num = numbers.format_number(int(num), locale=locale)
    if digits == 0:
        return num
    return num + numbers.get_decimal_symbol(locale) + decimals


def parse_date(string):
    """Parse a date from a string.
    """
    return dates.parse_date(string, locale=get_locale())


def parse_time(string):
    """Parse a time from a string.
    """
    return dates.parse_time(string, locale=get_locale())


def parse_datetime(string):
    """Parse a datetime from a string.
    """
    return dates.parse_datetime(string, locale=get_locale())


def parse_number(string):
    """Parse a localized number string into a long integer.
    """
    return numbers.parse_number(string, locale=get_locale())


def parse_decimal(string, force_decimal=False):
    """Parse a localized decimal string into a float if `force_decimal` is
    False, else into a real :class:`decimal.Decimal` value.

    :param string: localized decimal string value
    :param force_decimal: whether to return Decimal instead of float
    """
    locale = get_locale()
    sep = numbers.get_decimal_symbol(locale)
    num, decimals = string.rsplit(sep, 1)
    num = numbers.parse_number(num, locale=locale)
    string = '%s.%s' % (num, decimals)
    return Decimal(string) if force_decimal else float(string)

