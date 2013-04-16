"""
kalapy.contrib.sessions
~~~~~~~~~~~~~~~~~~~~~~~

This package implements session middleware, flash message api and few
session storage backends like `memory`, `memcached` and `database`.

In order to enable session support in a project, this package should be
included in `settings.INSTALLED_PACKAGES` and `settings.MIDDLEWARE_CLASSES`
should list the `kalapy.contrib.sessions.SessionMiddleware` as very first
middleware class in the list.

Then the `session` can be accessed via `request.session` variable.

Besides the session support, this package also implements support for
flashing messages which can be passed through the next requests.

For more details on flashing messages see :func:`flash` and :func:`flashes`.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LINCESE for more details.
"""
from werkzeug import import_string

from kalapy.contrib.sessions.flash import flash, flashes
from kalapy.conf import settings
from kalapy.web import Middleware


class SessionMiddleware(Middleware):
    """Implements Session middleware.
    """
    def __init__(self):
        engine = import_string(
            'kalapy.contrib.sessions.engines.%s' % settings.SESSION_ENGINE)
        self.store = engine.Store()
        opts = settings.SESSION_COOKIE
        self.cookie_name = opts.get('name', 'session_id')
        self.cookie_age = opts.get('age', 0)

    def process_request(self, request):
        sid = request.cookies.get(self.cookie_name, None)
        request.session = self.store.get(sid) if sid else self.store.new()
        request.flash = flash
        request.flashes = flashes

    def process_response(self, request, response):
        try:
            session = request.session
        except AttributeError:
            pass
        else:
            if session.should_save:
                self.store.save(session)
                response.set_cookie(
                    self.cookie_name, session.sid,
                    max_age=self.cookie_age)
