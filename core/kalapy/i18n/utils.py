# -*- coding: utf-8 -*-
"""
kalapy.i18n.utils
~~~~~~~~~~~~~~~~~

This module implements i18n support functions.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LICENSE for more details.
"""
import os, sys

from pytz import timezone, UTC
from babel import Locale
from babel.support import LazyProxy, Translations

from kalapy.conf import settings

#: cache of loaded translations (speedup)
TRANSLATIONS = {}


def get_translations():
    """Returns gettext translations to be used for current locale.
    """
    locale = str(get_locale())
    translations = TRANSLATIONS.get(locale)
    if translations is None:
        translations = load_translations('kalapy', locale)
        if isinstance(translations, Translations):
            for package in settings.INSTALLED_PACKAGES:
                tr = load_translations(package, locale)
                if isinstance(tr, Translations):
                    translations.merge(tr)
        TRANSLATIONS[locale] = translations

    return translations


def load_translations(import_name, locale):
    """Loads gettext translations for the given locale from the specified
    package represented by the given import name.
    """
    if import_name not in sys.modules:
        return None
    path = os.path.abspath(os.path.dirname(sys.modules[import_name].__file__))
    path = os.path.join(path, 'locale')
    return Translations.load(path, [locale])


def get_locale():
    """Returns the locale to be used for current request as `babel.Locale`
    object. If used outside of a request, it return default locale as specified
    by `settings.DEFAULT_LOCALE`.
    """
    from kalapy.web import request
    try:
        locale = getattr(request, 'babel_locale', None)
    except:
        locale = None

    if locale is None:
        try:
            locale = Locale.parse(request.accept_languages.best, sep='-')
            request.babel_locale = locale
        except:
            locale = Locale.parse(settings.DEFAULT_LOCALE)
    return locale


def get_timezone():
    """Returns the timezone to be used for current request as `pytz.timezone`
    object. If used outside of a request, it return default timezone as specified
    by `settings.DEFAULT_TIMEZONE`.
    """
    from kalapy.web import request
    try:
        tzinfo = getattr(request, 'babel_tzinfo', None)
    except:
        tzinfo = None

    if tzinfo is None:
        #XXX: should use user timezone
        tzinfo = timezone(settings.DEFAULT_TIMEZONE)
        if request:
            request.babel_tzinfo = tzinfo
    return tzinfo


def gettext(string, **kwargs):
    """Translates the given string with current locale and passes the given
    keyword variables as a mapping to format the string. The returned value
    is a lazy instance which will be translated when it is actually used.

    Example::

        h1 = gettext('Hello World!')
        h2 = gettext('Hello %(name)s!', name='World')

        @web.route('/say')
        def say():
            return h1

    :param string: the string to be translated
    :param kwargs: mapping to the format place holders
    :returns: a lazy instance to delay actual translation, translation will be
              performed when result is actually used.
    """
    def lazy(s, **kw):
        return get_translations().ugettext(s) % kw
    return LazyProxy(lazy, string, **kwargs)


def ngettext(string, plural, num, **kwargs):
    """Translates the given string with current locale and passes the given
    keyword variables as a mapping to format the string.

    It does a plural-forms lookup of a given string depending on the `num` and
    uses `plural` instead of `string` if `num` represents plural in the current
    locale.

    The returned value is a lazy instance which will be translated when it is
    actually used.

    Example::

        ngettext('%(num)d Apple', '%(num)d Apples!', num=len(apples))

    :param string: the string to be translated, singular form
    :param plural: the plural form of the string
    :param num: value of num placeholder
    :param kwargs: mapping to the format place holders
    :returns: a lazy instance to delay actual translation, translation will be
              performed when result is actually used.
    """
    def lazy(s, p, n, **kw):
        kw.setdefault('num', n)
        return get_translations().ungettext(s, p, n) % kw
    return LazyProxy(lazy, string, plural, num, **kwargs)
