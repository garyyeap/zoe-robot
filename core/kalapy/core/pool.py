"""
kalapy.core.pool
~~~~~~~~~~~~~~~~

This module implements object pool that caches package instances and resources
provided by them.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LICENSE for more details.
"""
from __future__ import absolute_import

import re, os, sys, logging

try:
    import threading
except ImportError:
    import dummy_threading as threading

from werkzeug import find_modules, import_string
from werkzeug.routing import Map

from kalapy.conf import settings
from kalapy.utils.containers import OrderedDict


__all__ = ('pool',)


logger = logging.getLogger('pool')


_NAME_REGEX = re.compile('^((?:kalapy\.contrib\.)?(?:\w+)).*$')


class Pool(object):
    """An object pool that caches installed packages and resources provided by
    those packages.

    The pool is used to automatically load all the installed packages and the
    resources provided by them, like models and view functions.
    """

    __shared_state = dict(

        #: Cahce of all the :class:`kalapy.web.Package` objects, with package
        #: name as key and package instance as value.
        packages = OrderedDict(),

        #: Cache of all the :class:`kalapy.db.Model` classes, with package
        #: name as key and another dict as value with model name as key and
        #: model class as value.
        model_cache = OrderedDict(),

        #: Keep track of model names
        model_alias = {},

        #: Pending Model references, used to resolve relationship.
        model_pending = {},

        #: Cache of all the view functions provided by the installed packages
        view_functions = {},

        #: Holds the url map
        url_map = Map(),

        #: Whether the pool is fully loaded or not
        loaded = False,

        #: For internal use only.
        lock = threading.RLock(),
    )

    def __init__(self):
        self.__dict__ = self.__shared_state

    def load_modules(self, package, name):
        """Load the module/submodules of the given package by given name.
        """
        modules = tuple(find_modules(package, include_packages=True))
        fullname = '%s.%s' % (package, name)

        result = []

        if fullname in modules:
            logger.info(' * Loading module: %s' % fullname)
            mod = import_string(fullname)
            result.append(mod)

        try:
            submodules = tuple(find_modules(fullname))
        except (ValueError, AttributeError):
            return result

        for module in submodules:
            logger.info(' * Loading module: %s' % module)
            mod = import_string(module)
            result.append(mod)

        return result

    def load(self):
        """Load all the installed packages.
        """
        if self.loaded:
            return

        from kalapy.web.package import Package

        self.lock.acquire()
        try:
            for package in settings.INSTALLED_PACKAGES:
                if package in self.packages:
                    continue
                logger.info(' * Loading package: %s' % package)
                if package not in sys.modules:
                    import_string(package)

                self.packages[package] = Package(package)

                self.load_modules(package, 'models')
                self.load_modules(package, 'views')

            self.loaded = True
        finally:
            self.lock.release()

    def get_model(self, model_name):
        """Get the model from the cache of the given name. The format of the `model_name`
        should `package:model`.

        For example::

            >>> get_model('foo:Foo')
            >>> get_model('bar:Bar')

        The `model` part in the `model_name` is case insensitive.

        :param model_name: name of the model

        :returns: a Model class or None
        :raises: :class:`~TypeError` if model is not found.
        """
        from kalapy.db.model import ModelType

        if isinstance(model_name, ModelType):
            model_name = model_name._meta.name

        assert model_name.count(':') == 1, 'Invalid model name format'

        package, name = model_name.split(':')
        alias = self.model_alias.get(model_name.lower(), model_name.lower())
        try:
            return self.model_cache.get(package, {})[alias]
        except KeyError:
            raise TypeError(
                _('No such model %(name)r in package %(package)r',
                    name=name, package=package))

    def get_models(self, *packages):
        """Get the list of all the models from the cache for the provided package
        names. If package names are not provided returns list of all models.

        :arg packages: package names

        :returns: list of models
        :raises: :class:`~TypeError` if a package is not found.
        """
        result = []
        for package in (packages or self.model_cache):
            try:
                result.extend(self.model_cache[package].values())
            except KeyError:
                if package not in self.packages:
                    raise TypeError(_('No such package %(name)r', name=package))
        return result

    def register_model(self, cls):
        """Register the provided model class to the cache.

        :param cls: the model class
        """
        package, name = cls._meta.package, cls._meta.name
        alias = cls.__name__
        if package:
            alias = '%s:%s' % (package, alias)

        self.model_alias[alias] = name
        self.model_cache.setdefault(package, OrderedDict())[name] = cls

        # resolve any pending references
        for field in self.model_pending.pop(alias, []):
            field.prepare(field.model_class)

    def get_package(self, name):
        """Get package by the given name. The name can be a package name or
        name of a module provided by the package. For example::

            >>> pool.get_package('foo')
            ... <Package 'foo'>
            >>> pool.get_package('foo.models')
            ... <Package 'foo'>
            >>> pool.get_package('foo.views.submodule')
            ... <Package 'foo'>
            >>> pool.get_package('kalapy.contrib.sessions')
            ... <Package 'sessions'>

        :param name: name of the package or name of a module provided by the package.
        """
        try:
            name = _NAME_REGEX.match(name).group(1)
        except:
            raise TypeError(
                _('Invalid package name: %(name)', name=name))
        return self.packages.get(name)

    def get_static_paths(self):
        """Returns a maping of static directories provided by installed
        packages.
        """
        result = {}
        for package in self.packages.values():
            items = result.setdefault(package.static_prefix, [])
            items.insert(0, package._static_dir)
        return dict([(k, tuple(v)) for k, v in result.items()])

    def get_template_paths(self):
        """Returns a maping of template directories provided by installed
        packages.
        """
        result = {}
        for package in self.packages.values():
            items = result.setdefault(package.package.name, [])
            items.insert(0, package._template_dir)
        return dict([(k, tuple(v)) for k, v in result.items()])

pool = Pool()
