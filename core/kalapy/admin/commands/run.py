"""
kalapy.admin.commands.run
~~~~~~~~~~~~~~~~~~~~~~~~~

This module implements `runserver` command which is used to run a simple
wsgi server during development.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LINCESE for more details.
"""
from kalapy.admin import Command
from kalapy.web import simple_server


class RunServer(Command):
    """Start a simple wsgi application server (for development environment)
    """
    name = 'runserver'
    usage = '%name [options]'

    options = (
        ('p', 'port', 8080, 'Port of the server to run on'),
        ('a', 'address', '127.0.0.1', 'Address to which the server should bind.'),
        ('n', 'no-reload', False, 'Do not use auto-reload feature.'),
    )

    def execute(self, options, args):
        host = options.address
        port = options.port
        use_reloader = not options.no_reload
        simple_server(host, port, use_reloader)

