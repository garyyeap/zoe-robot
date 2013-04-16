"""
kalapy.admin.commands.test
~~~~~~~~~~~~~~~~~~~~~~~~~~

This module implements `test` command to run testsuites.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LINCESE for more details.
"""
import os

from kalapy.admin import Command, execute_command
from kalapy.conf import settings
from kalapy.test import run_tests


class TestCommand(Command):
    """Run the tests specified by the given names. A test name can be,

        package_name of an installed package or
        package_name:test_fullname

        A test_fullname should be a fully qualified name relative to
        package.tests module. For example:

        %prog test foo
        %prog test foo:FooTest
        %prog test foo:FooTest.test_foo
        %prog test bar:db_tests.DBTest
        %prog test bar:db_tests.DBTest.test_mymodel
        %prog test bar:view_tests.PaginationTest

    If test names are not given run all the tests of the installed packages.
    """
    name = 'test'
    usage = '%name [name [name [name [...]]]]'

    def packages_with_tests(self):
        for pkg in os.listdir(settings.PROJECT_DIR):
            if pkg in settings.INSTALLED_PACKAGES and \
                (os.path.exists(os.path.join(pkg, 'tests.py')) or \
                 os.path.exists(os.path.join(pkg, 'tests', '__init__.py'))):
                    yield pkg

    def execute(self, options, args):

        dbname = settings.DATABASE_NAME
        if settings.DATABASE_ENGINE == 'sqlite3':
            dbname = os.path.basename(dbname)
        if dbname and not dbname.lower().startswith('test_'):
            self.error("Invalid database %r, test database name must start with 'test_'" % dbname)

        args = args or self.packages_with_tests()

        if not args:
            raise self.error('No package installed yet.')

        # sync database tables
        execute_command(['database', 'sync'])

        run_tests(args, 2 if options.verbose else 0)
