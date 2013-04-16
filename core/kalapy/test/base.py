"""
kalapy.test.base
~~~~~~~~~~~~~~~~

This module implements TestCase class, the base class for creating test cases.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LICENSE for more details.
"""
import re, unittest

from werkzeug import Client

from kalapy.web import Application, Response


__all__ = ('TestCase',)


def test_app():
    """Returns an Application instance
    """
    return Application() # Application is a Singleton


class TestCase(unittest.TestCase):

    def __call__(self, result=None):
        """Overriden to create ``self.client`` attribute, an instance of
        :class:`werkzeug.Client`, which can be used to send virtual requests
        to the test application.
        """
        self.test_app = test_app()
        self.client = Client(self.test_app, Response)
        super(TestCase, self).__call__(result)

    def request_context(self, *args, **kw):
        """Create a request context for use in tests. The arguments passed will
        be used to create a WSGI environment to create a request instance (see
        :func:`werkzeug.create_environ` for more information). This method must
        be used with the ``with`` statement.

        For example::

            with self.request_context():
                do_something_with(request)
        """
        from werkzeug import create_environ
        return self.test_app.request_context(create_environ(*args, **kw))

    def assertMatch(self, data, pattern, message=None, flags=0):
        """Tests whether the given pattern matches to the given data.
        """
        if re.search(pattern, data, flags) is None:
            if message is None:
                message = 'No match for %r in the given data' % pattern
            raise self.failureException(message)
