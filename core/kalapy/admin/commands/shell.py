"""
kalapy.admin.commands.shell
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module imeplements `shell` and `script` commands, which can be
used to start a python shell or launch a python script in the context
of current project.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LINCESE for more details.
"""
import os

from kalapy.admin import Command


class ScriptCommand(Command):
    """Run arbitrary python script in the context of current project.
    """
    name = 'script'
    usage = '%name <FILE>'

    def execute(self, options, args):
        try:
            script = args[0]
        except:
            self.print_help()

        if not os.path.exists(script):
            self.error("%r doesn't exist." % script)

        # Initialize the object pool
        from kalapy.core.pool import pool
        pool.load()

        execfile(script, {'__name__': '__main__'})

class ShellCommand(Command):
    """Runs a Python interactive interpreter. Tries to use IPython if available.
    """
    name = 'shell'

    options = (
        ('p', 'plain', False, 'use plain python interpreter, not ipython.'),
    )

    def execute(self, options, args):

        # Initialize the object pool
        from kalapy.core.pool import pool
        pool.load()

        try:
            if options.plain:
                raise ImportError
            import IPython
            shell = IPython.Shell.IPShell(argv=[])
            shell.mainloop()
        except ImportError:
            imported_objects = {}
            try: # Try activating rlcompleter, because it's handy.
                import readline
                import rlcompleter
                readline.set_completer(rlcompleter.Completer(imported_objects).complete)
                readline.parse_and_bind("tab:complete")
            except ImportError:
                pass

            import code
            code.interact(local=imported_objects)
