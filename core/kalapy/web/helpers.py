# -*- coding: utf-8 -*-
"""
kalapy.web.helpers
~~~~~~~~~~~~~~~~~~

Implements helper functions.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LICENSE for more details.
"""
try:
    import simplejson as json
except ImportError:
    import json

from werkzeug import redirect

from kalapy.web.local import _request_context
from kalapy.web.package import Package
from kalapy.web.wrappers import Response


__all__ = ('route', 'url_for', 'locate', 'jsonify', 'json')


def route(rule, **options):
    """A decorator to register a view function for a given URL rule.

    Example::

        @web.route('/<path:page>')
        def index(page):
            ...

        @web.route('/<path:page>', methods=('POST',))
        def save(page):
            ...

        @web.route('/<path:page>/edit')
        def edit(page):
            ...

    For more information, see...

    :param rule: the URL rule as string
    :param methods: a list of http methods this rule is limited to like
                   (``'GET'``, ``'POST'``, etc). By default a rule is
                   limited to ``'GET'`` (and implicitly ``'HEAD'``).
    :param options: other options to be forwarded to the underlying
                    :class:`werkzeug.routing.Rule` object.
    """
    def wrapper(func):
        package = Package.from_view_function(func)
        return package.route(rule, **options)(func)
    return wrapper


def url_for(endpoint, **values):
    """Generate a URL for the given endpoint with the method provided. The
    endpoint is a name of the view function in the current package defined
    in the views module. If you want to refer an endpoint from another package,
    prefix it with package name like ``"package:view_func"``. If your view
    functions are organized in submodules other then in the views module, the
    endpoint name should be in ``"module.view_func"`` format. The endpoint
    prefixed with a ``.`` will be resolved against current module.

    Here are few examples:

    =============== ======================= ============================
    Active Package  Target Endpoint         Target Function
    =============== ======================= ============================
    `blog`          ``'index'``             `blog.views.index`
    `blog`          ``'page.index'``        `blog.views.page.index`
    `blog`          ``'.edit'``             `blog.views.page.edit`
    `wiki`          ``'index'``             `wiki.views.index`
    `blog`          ``'wiki:index'``        `wiki.views.index`
    `any`           ``'wiki:index'``        `wiki.views.index`
    `any`           ``'blog:index'``        `blog.views.index`
    `any`           ``'blog:page.index'``   `blog.views.page.index`
    =============== ======================= ============================

    Where `blog.views.index` is defined in `blogs/views/__init__.py` and
    `blog.views.page.index` is defined in `blogs/views/page.py` and so on.

    Variable arguments that are unknown to the target endpoint are appended
    to the generated URL as query arguments.

    This function can also be used to generate URL for static contents in
    templates. In that case, if you want to refer global static dir then
    just prefix the endpoint with ':' like `:static`.

    Here are few examples:

    =============== =================== ==============================
    Active Package  Target Endpoint     Target Static Dir
    =============== =================== ==============================
    `blog`          ``'static'``        `/blog/static`
    `wiki`          ``'static'``        `/wiki/static`
    `any`           ``':static'``       `/static`
    `any`           ``'blog:static'``   `/blog/static`
    =============== =================== ==============================

    For more information, see...

    :param endpoint: the endpoint for the URL
    :param values: the variable arguments for the URL
    :param _external: if set to True, an absolute URL will be generated.

    :returns: generate URL string
    :raises: :class:`BuildError`
    """

    ctx = _request_context
    reference = None
    external = values.pop('_external', False)

    if ':' in endpoint:
        reference, endpoint = endpoint.split(':', 1)

    if endpoint == 'static':
        if reference is None:
            reference = ctx.request.package
    else:
        if endpoint.startswith('.'):
            endpoint = endpoint[1:]
            reference = ctx.request.endpoint.rsplit('.', 1)[0]
        if not reference:
            reference = ctx.request.package
    if reference:
        endpoint = '%s.%s' % (reference, endpoint)
    return ctx.url_adapter.build(endpoint, values, force_external=external)


def locate(endpoint, **values):
    """Similar to `werkzeug.redirect` but uses `url_for` to generate
    target location from the url rules.

    :param endpoint: the endpoint for the URL
    :param values: the variable arguments for the URL
    :param _external: if set to True, an absolute URL will be generated.
    :param _code: http status code, default 302
    """
    code = values.pop('_code', 302)
    return redirect(url_for(endpoint, **values), code)


def jsonify(*args, **kw):
    """Creates a :class:`Response` with JSON representation of the given
    data provided from the arguments with an `application/json` mimetype.
    The arguments to this function are same as :class:`dict` constructor.

    Example::

        @web.route('/user/info')
        def get_user():
            return jsonify(name="somename", active=True, key=34)

    This will send a JSON response to the client like this::

        {
            'name': 'somename',
            'active': true,
            'key': 34
        }

    :returns: an instance of :class:`Response`
    """
    return Response(json.dumps(dict(*args, **kw)), mimetype='application/json')
