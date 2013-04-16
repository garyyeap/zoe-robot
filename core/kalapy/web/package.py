# -*- coding: utf-8 -*-
"""
kalapy.web.package
~~~~~~~~~~~~~~~~~~

Implements :class:`Package` that represent a package.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LICENSE for more details.
"""
import os, sys

try:
    import threading
except ImportError:
    import dummy_threading as threading

from werkzeug import find_modules, import_string
from werkzeug.routing import Rule

from kalapy.conf import Settings, settings, package_settings
from kalapy.utils.containers import OrderedDict
from kalapy.core.pool import pool


__all__ = ('Package',)


class PackageType(type):
    """A meta class to ensure only one instance of :class:`Package` exists
    for a given package name.
    """

    #: cache of all the Package instances
    ALL = {}

    def __call__(cls, *args):
        name = args[0] if args else None
        if name not in cls.ALL:
            cls.ALL[name] = super(PackageType, cls).__call__(*args)
        return cls.ALL[name]

    def from_view_function(cls, func):
        """A factory method to create package instance from the view function.
        """
        return cls(func.__module__.split('.views', 1)[0])


class Package(object):
    """Container object that represents an installed package.

    A package can be enabled/disabled from `settings.INSTALLED_PACKAGES`. This
    class is intended for internal use only.

    For more information on packages, see...

    :param name: name of the package
    :param path: directory path where package is located
    """
    __metaclass__ = PackageType

    #: Package settings
    settings = None

    def __init__(self, import_name):

        self.name = import_name.rsplit('.', 1)[-1]
        self.path = os.path.abspath(
            os.path.dirname(sys.modules[import_name].__file__))

        options = dict(NAME=self.name)
        try:
            execfile(os.path.join(self.path, 'settings.py'), {}, options)
        except IOError:
            pass
        self.settings = Settings(package_settings, **options)

        # static directory
        self._static_dir = os.path.join(self.path, 'static')

        # add rule for static urls
        self.add_rule('/%s/static/<filename>' % self.package.name,
            'static', build_only=True)

        # template directory
        self._template_dir = os.path.join(self.path, 'templates')

    def __repr__(self):
        return "<%s '%s'>" % (self.__class__.__name__, self.name)

    @property
    def submount(self):
        """Submount for the package. If this is an addon package then it is
        the same as the extending package.
        """
        if self.settings.EXTENDS:
            return self.package.submount
        return self.settings.SUBMOUNT

    @property
    def package(self):
        """The parent package this package is extending otherwise the self.
        """
        if self.settings.EXTENDS:
            assert self.settings.EXTENDS in settings.INSTALLED_PACKAGES, \
                "no such package installed: %s" % self.settings.EXTENDS
            return Package(self.settings.EXTENDS)
        return self

    @property
    def static_prefix(self):
        return "%s/%s/static" % (
            self.submount or '',
            self.package.name)

    def add_rule(self, rule, endpoint, func=None, **options):
        """Add URL rule with the specified rule string, endpoint, view
        function and options.

        Function must be provided if endpoint is None. In that case endpoint
        will be automatically generated from the function name. Also, the
        endpoint will be prefixed with current package name.

        Other options are similar to :class:`werkzeug.routing.Rule` constructor.
        """
        if endpoint is None:
            assert func is not None, 'expected view function if endpoint' \
                    ' is not provided'

        if endpoint is None:
            endpoint = '%s.%s' % (func.__module__, func.__name__)
            __, endpoint = endpoint.rsplit('views.', 1)

        endpoint = '%s.%s' % (self.package.name, endpoint)

        options.setdefault('methods', ('GET',))
        options['endpoint'] = endpoint

        if self.submount:
            rule = '%s%s' % (self.submount, rule)

        pool.url_map.add(Rule(rule, **options))
        if func is not None:
            pool.view_functions[endpoint] = func

    def route(self, rule, **options):
        """Same as :func:`route`
        """
        def wrapper(func):
            self.add_rule(rule, None, func, **options)
            return func
        return wrapper
