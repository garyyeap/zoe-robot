# -*- coding: utf-8 -*-
"""
kalapy.web.wrappers
~~~~~~~~~~~~~~~~~~~

Implements :class:`Request` and :class:`Response`.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LICENSE for more details.
"""
from werkzeug import Request as BaseRequest, Response as BaseResponse

__all__ = ('Request', 'Response',)


class Request(BaseRequest):
    """The request object, remembers the matched endpoint, view arguments and
    current package.

    .. seealso:: :class:`werkzeug.Request`
    """

    #: The endpoint that matched the request. If an exception happend during
    #: url match, this will be ``None``.
    endpoint = None

    #: The view function referenced by the :attr:`endpoint`.
    view_func = None

    #: A dict of arguments that matched the request. If an exception happend
    #: during url match, this will be ``None``.
    view_args = None

    #: The exception raised during url matching else ``None``.
    #: This is usually a :exc:`~werkzeug.exceptions.NotFound` or similar.
    routing_exception = None

    @property
    def package(self):
        """The name of the current package.
        """
        try:
            return self.endpoint.split('.', 1)[0]
        except:
            return None


class Response(BaseResponse):
    """The response object that is used by default, with default mimetype
    set to `'text/html'`.

    .. seealso:: :class:`werkzeug.Response`
    """
    default_mimetype = 'text/html'
