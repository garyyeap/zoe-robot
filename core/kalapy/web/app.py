# -*- coding: utf-8 -*-
"""
kalapy.web.app
~~~~~~~~~~~~~~

This module implements the central WSGI :class:`Application` object.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LICENSE for more details.
"""
from __future__ import with_statement

import os

from jinja2.loaders import PrefixLoader, FileSystemLoader
from werkzeug import SharedDataMiddleware, import_string
from werkzeug.exceptions import HTTPException, InternalServerError
from werkzeug.routing import Rule

from kalapy.conf import settings
from kalapy.core import signals
from kalapy.core.pool import pool
from kalapy.core.logging import init_logger

from kalapy.web.helpers import url_for
from kalapy.web.local import RequestContext, request
from kalapy.web.templating import JinjaEnvironment
from kalapy.web.wrappers import Request, Response


__all__ = ('Middleware', 'Application', 'simple_server',)


class Middleware(object):
    """Application middleware objects (don't confuse with WSGI middleware).
    This is more similar to `Django's` middleware. It allows to hook into
    application's request/response cycle. It's a ligh, low-level 'plugin'
    system for globally alter the the application input/output.

    It defines following interface methods, which derived middleware classes
    should override.

    `process_request`

        this method will be called before request starts.

    `process_response`

        this method will be called after request is finished and response
        is successfully generated.

    `process_exception`

        this method will be called when any exception occurred during request/
        response cycle.

    For more information on middleware, see...
    """

    def process_request(self, request):
        """This method will be called before request starts.
        """
        pass

    def process_response(self, request, response):
        """This method will be called after response is successfully generated.
        """
        pass

    def process_exception(self, request, exception):
        """This method will be called if any exception occurs during request/
        response cycle.
        """
        pass


class StaticMiddleware(SharedDataMiddleware):
    """Custom SharedDataMiddleware to support static directory overriding by
    addon packages.
    """
    def get_package_loader(self, *paths):
        def loader(path):
            if path is None:
                return None, None
            for part in paths:
                filename = os.path.join(part, path)
                if os.path.isfile(filename):
                    return os.path.basename(path), self._opener(filename)
            return None, None
        return loader

    @classmethod
    def from_paths(cls, app, *mappings):
        """A class method to create static middleware from the given mappings.
        """
        assert len(mappings) > 0, 'atleast one mapping required'

        paths = dict()
        map(paths.update, mappings)

        def expand_paths(val):
            if isinstance(val, basestring):
                if not os.path.isabs(val):
                    return os.path.join(settings.PROJECT_DIR, val)
                return val
            if isinstance(val, (list, tuple)):
                return tuple(map(expand_paths, val))
            return val

        return cls(app, dict([(k, expand_paths(v)) for k,v in paths.items()]))


class ApplicationType(type):
    """A metaclass to ensure singleton Application instance.
    """
    instance = None
    def __call__(cls):
        if cls.instance is None:
            cls.instance = super(ApplicationType, cls).__call__()
        return cls.instance


class Application(object):
    """The Application class implements a WSGI application. This class is
    responsible to request dispatching, middleware processing, generating
    proper response from the view function return values etc.
    """
    __metaclass__ = ApplicationType

    def __init__(self):

        #: If application is runing in debug mode.
        self.debug = settings.DEBUG

        # Initialize logging.
        init_logger()

        # Initialize the object pool
        pool.load()

        #: List of all the registered middlewares (settings.MIDDLEWARE_CLASSES)
        self.middlewares = [import_string(s)() for s in settings.MIDDLEWARE_CLASSES]

        # static data middleware
        self.dispatch = StaticMiddleware.from_paths(self.dispatch, {
                '/static': os.path.join(settings.PROJECT_DIR, 'static'),
            }, pool.get_static_paths(), settings.STATIC_LINKS)

        pool.url_map.add(
            Rule('/static/<filename>',
                endpoint='static', methods=('GET',), build_only=True))

        #: The jinja2 environment
        self.jinja_env = self._create_jinja_env(pool.get_template_paths())

    def _create_jinja_env(self, paths):
        """Creates Jinja template loader for the provided template paths.
        Returns a JinjaEnvironment instance.
        """
        paths[''] = (os.path.join(settings.PROJECT_DIR, 'templates'),)
        paths = dict([(k, FileSystemLoader(v)) for k, v in paths.items()])

        jinja_loader = PrefixLoader(paths, delimiter=':')

        jinja_env = JinjaEnvironment(
            loader=jinja_loader,
            autoescape=True,
            extensions=['jinja2.ext.autoescape', 'jinja2.ext.with_'])

        jinja_env.globals.update(
            url_for=url_for,
            request=request)

        if settings.USE_I18N:
            from kalapy.web.templating import gettext, ngettext
            jinja_env.add_extension('jinja2.ext.i18n')
            jinja_env.install_gettext_callables(gettext, ngettext, newstyle=True)
            jinja_env.globals.update({
                '_': gettext,
                'gettext': gettext,
                'ngettext': ngettext
            })

        return jinja_env

    def process_request(self, request):
        """This method will be called before actual request dispatching and
        will call all the registered middleware's respective `process_request`
        methods. If any of these methods returns any values, it is considered
        as if it was the return value of the view function and further request
        handling will be stopped.
        """
        for mw in self.middlewares:
            rv = mw.process_request(request)
            if rv is not None:
                return rv

    def process_response(self, request, response):
        """This method will be called after response is successfully created and
        will call all the registered middleware's respective `process_response`
        methods.
        """
        for mw in reversed(self.middlewares):
            rv = mw.process_response(request, response)
            if rv is not None:
                return rv
        return response

    def process_exception(self, request, exception):
        """This method will be called if there is any unhandled exception
        occurs during request handling. In turn, this method will call all the
        registered middleware's respective `process_exception` methods.
        """
        for mw in self.middlewares:
            rv = mw.process_exception(request, exception)
            if rv is not None:
                return rv

    def make_response(self, value):
        """Converts the given value into a real response object that is an
        instance of :class:`Response`.

        :param value: the value to be converted
        """
        if value is None:
            raise ValueError('View function should return a response')
        if isinstance(value, Response):
            return value
        if isinstance(value, basestring):
            return Response(value)
        if isinstance(value, tuple):
            return Response(*value)
        return Response.force_type(value, request.environ)

    def get_response(self, request):
        """Returns an :class:`Response` instance for the given `request` object.
        """
        if request.routing_exception is not None:
            raise request.routing_exception

        response = self.process_request(request)
        if response is not None:
            return response

        func, args = request.view_func, request.view_args
        try:
            return self.make_response(func(**args))
        except Exception, e:
            response = self.process_exception(request, e)
            if response is not None:
                return response
            raise

    def request_context(self, environ):
        """Create request context from the given environ. This must be used with
        the ``with`` statement as the context is bould to the current context.

        For example::

            with app.request_context():
                do_something_with(request)

        :param environ: the wsgi environment to be used to create request.
        """
        req = Request(environ)
        ctx = RequestContext(self, req)

        ctx.url_adapter = pool.url_map.bind_to_environ(environ)
        try:
            req.endpoint, req.view_args = ctx.url_adapter.match()
            req.view_func = pool.view_functions[req.endpoint]
        except HTTPException, e:
            req.routing_exception = e

        return ctx

    def dispatch(self, environ, start_response):
        """The actual wsgi application. This is not implemented in `__call__`
        so that wsgi middlewares can be applied without losing a reference to
        the class.
        """
        with self.request_context(environ) as ctx:
            signals.send('request-started')
            try:
                try:
                    response = self.get_response(ctx.request)
                except HTTPException, e:
                    response = e
                    if e.code == 404 and self.debug and not len(pool.view_functions):
                        response = self.make_response(WELCOME_PAGE)
                except Exception, e:
                    signals.send('request-exception', error=e)
                    if self.debug:
                        raise
                    response = InternalServerError()
                response = self.process_response(request, response)
            finally:
                signals.send('request-finished')
            return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.dispatch(environ, start_response)


def simple_server(host='127.0.0.1', port=8080, use_reloader=False):
    """Run a simple server for development purpose.

    :param host: host name
    :param post: port number
    :param use_reloader: whether to reload the server if any of the loaded
                         module changed.
    """
    from werkzeug import run_simple
    # create a wsgi application
    app = Application()
    run_simple(host, port, app, use_reloader=use_reloader, use_debugger=app.debug)


#: The welcome page, will be shown if there is no routing rules defined.
WELCOME_PAGE = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
    "http://www.w3.org/TR/html4/loose.dtd">
<html lang="en">
<head>
  <meta http-equiv="content-type" content="text/html; charset=utf-8">
  <title>Welcome to KalaPy</title>
  <style type="text/css">
    body { font: .9em serif; }
    html * { padding: 0; margin: 0; }
    body * { padding: 10px 20px; }
    body * * { padding:0; }
    div { border-bottom: 1px solid #ddd; }
    a { color: #377BA8; }
    a { text-decoration: none; }
    a:hover { border-bottom: 1px solid #eee; }
    h1 { font-weight: normal; color: #212224; text-shadow: white 0px 1px 0px; }
    h2 { font-weight: normal; color: #666; }
    ul { margin: 1em; margin-left: 2em; }
    .welcome { background-color: #bed4eb; }
    .help { background:#f6f6f6; }
    .notes { background:#eee; }
  </style>
</head>
<body>
  <div class="welcome">
    <h1>Welcome to KalaPy</h1>
    <h2>Congratulations on your first KalaPy project...</h2>
  </div>
  <div class="help">
    <p>You haven't done any work yet. Here's what to do next.</p>
    <ul>
      <li>Go to the project directory.</li>
      <li>Edit the <code>settings.py</code> file as required.</li>
      <li>
        Create your first application package by running
        <code>python ./admin.py startpackage [packagename]</code> command.
      </li>
      <li>
        Define some routes in the <code>views.py</code> of your
        application package.
      </li>
      <li>
        Activate your package by appending it to <code>INSTALLED_PACKAGES</code>
        settings.
      </li>
      <li>
        Start the server with <code>python ./admin.py runserver</code> command.
      </li>
    </ul>
    <p>
      See <a href="http://www.kalapy.org/docs">KalaPy documentation</a> for
      more information.
    </p>
  </div>
  <div class="notes">
    You are seeing this page because you have <code>DEBUG = True</code> in your
    <code>settings.py</code> file and you haven't defined any routing rules.
  </div>
</body>
</html>
"""
