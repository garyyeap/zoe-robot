"""
kalapy.test.utils
~~~~~~~~~~~~~~~~~

This module implements helper functions for test api.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD,
"""
import re, sys, unittest
from werkzeug import find_modules, import_string

__all__ = ('build_suite', 'run_tests')

TEST_MODULE = 'tests'

def build_suite(name):
    """Build test suite for the given name. A name can be either a package name
    or a fully qualified name of the test class or a specific test method within
    a package prefixed with ``package_name:``.

    For example:

        >>> build_suite('hello')
        >>> build_suite('hello:HelloTest')
        >>> build_suite('hello:HelloTest.test_hello')
        >>> build_suite('foo:foo.FooTest')
        >>> build_suite('foo:bar.BarTest')

    :returns:
        an instance of `TestSuite`
    """
    try:
        package, test = name.split(':')
    except:
        package, test = name, None

    test_module = '%s.%s' % (package, TEST_MODULE)
    test_fullname = '%s.%s' % (test_module, test) if test else test_module

    suite = unittest.TestSuite()

    match = re.match('(.*?)\.(test_\w+)$', test_fullname)
    if match:
        try:
            TestClass = import_string(match.group(1))
        except ImportError:
            raise ImportError(match.group(1))
        suite.addTest(TestClass(match.group(2)))

    elif test:
        try:
            TestClass = import_string(test_fullname)
        except AttributeError:
            raise AttributeError(test_fullname)
        if isinstance(TestClass, unittest.TestCase.__class__):
            suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestClass))
        else:
            suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(TestClass))

    else:
        try:
            test_modules = list(find_modules(test_module))
        except ValueError:
            test_modules = [test_module]
        for module in map(import_string, test_modules):
            suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(module))

    return suite

def run_tests(names, verbosity=1):
    """Run unittests for all the test names.

    A name can be either a package name or a fully qualified name of the
    test class or a specific test method within a package prefixed with
    ``package_name:``.

    For example:

        >>> run_tests('hello')
        >>> run_tests('hello:HelloTest')
        >>> run_tests('hello:HelloTest.test_hello')
        >>> run_tests('foo:foo.FooTest')
        >>> run_tests('foo:bar.BarTest')

    :param names: a sequence of names
    :param verbosity: verbose level
    """

    from kalapy.core.pool import pool
    from kalapy.db.engines import database

    database.connect()
    try:
        # Initialize the object pool
        pool.load()
        suite = unittest.TestSuite()
        for name in names:
            suite.addTest(build_suite(name))
        result = unittest.TextTestRunner(verbosity=verbosity).run(suite)
    finally:
        database.close()

    return len(result.failures) + len(result.errors)
