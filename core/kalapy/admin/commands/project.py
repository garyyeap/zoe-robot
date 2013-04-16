"""
kalapy.admin.commands.project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module implements `project` and `package` commands to new projects
and packages.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LINCESE for more details.
"""
import os, sys, re, shutil, string

from kalapy.admin import Command, ActionCommand, CommandError


def copy_helper(source, target, context):
    """Copy source directory to target directory. Expand the templates with
    the given context.
    """
    if not os.path.isabs(source):
        source = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), source)

    names = os.listdir(source)
    if names and not os.path.exists(target):
        os.mkdir(target)

    for name in names:
        srcname = os.path.join(source, name)
        dstname = os.path.join(target, name)

        if os.path.isdir(srcname):
            copy_helper(srcname, dstname, context)
            continue

        if srcname[-4:] in ('.pyc', '.pyo'):
            continue

        if srcname.endswith('_t'):
            dstname = dstname[:-2]

        if os.path.exists(dstname):
            continue

        shutil.copy2(srcname, dstname)

        if srcname.endswith('_t'):
            content = open(srcname).read()
            content = string.Template(content).safe_substitute(context)

            fo = open(dstname, 'w')
            fo.write(content)
            fo.close()

        #XXX: make python scripts executable (pip install issue?)
        if dstname.endswith('.py') and open(dstname).read(2) == '#!':
            try:
                os.chmod(dstname, 0775)
            except:
                pass


def check_name(name):
    """Check whether the name is valid name.
    """
    if not re.match('^[_a-zA-Z]\w*$', name):
        raise CommandError("Invalid name '%s'" % name)

    # make sure there is no such contrib package
    try:
        __import__('kalapy.contrib.%s' % name)
    except ImportError:
        pass
    else:
        raise CommandError(
            _('Name conflicts with \'kalapy.contrib.%(name)s\' package.', name=name))

    try:
        __import__(name)
    except ImportError:
        return name
    else:
        raise CommandError(
            _('Name conflicts with an existing python module.'))


class StartProject(Command):
    """Create a KalaPy project with the given project name in the current directory.
    """
    name = "project"
    usage = "<project>"

    scope = None

    def execute(self, options, args):
        try:
            name = check_name(args[0])
        except IndexError:
            self.print_help()
        except CommandError, e:
            self.error(e)

        if options.verbose:
            print "Creating %s..." % name
        copy_helper('project_template', name, {'name': name, 'name_lower': name.lower()})


class StartPackage(Command):
    """Create a KalaPy package with the given name in the current directory.
    """
    name = "package"
    usage = "%name <name>"

    def execute(self, options, args):
        try:
            name = check_name(args[0])
        except IndexError:
            self.print_help()
        except CommandError, e:
            self.error(e)

        if options.verbose:
            print "Creating %s..." % name
        copy_helper('package_template', name, {'name': name})

        for d in ('static', 'templates',):
            os.mkdir('%s/%s' % (name, d))

class GAEProject(ActionCommand):
    """Perform google appengine specific tasks.

    Use the 'appcfg.py' and 'dev_appserver.py' (included in appengine sdk)
    for other appengine specific tasks.
    """
    name = "gae"

    options = (
        ('a', 'address', 'localhost', 'hostname for the appserver'),
        ('p', 'port', '8080', 'port number for the appserver'),
        ('i', 'install', False, 'install libs (extra libs as arguments)'),
    )

    def setup_stubs(self, options):
        from kalapy.db.engines.gae._utils import setup_stubs
        setup_stubs()
        import logging
        logging.getLogger().setLevel(
            logging.INFO if options.verbose else logging.WARN)

    def action_runserver(self, options, args):
        """launch 'dev_appserver.py runserver'
        """
        self.setup_stubs(options)
        from google.appengine.tools import dev_appserver_main
        dev_appserver_main.main(
            ['runserver', '-a', options.address, '-p', options.port, '.'])

    def action_update(self, options, args):
        """launch 'appcfg.py update'
        """
        self.setup_stubs(options)
        from google.appengine.tools import appcfg
        appcfg.main(['appcfg.py', 'update', '.'])

    def action_rollback(self, options, args):
        """launch 'appcfg.py rollback'
        """
        self.setup_stubs(options)
        from google.appengine.tools import appcfg
        appcfg.main(['', 'rollback', '.'])

    def action_prepare(self, options, args):
        """prepare this project for google appengine.
        """
        from kalapy.conf import settings
        name = settings.PROJECT_NAME
        context = {'appname': name.lower(), 'name': name}
        if not os.path.exists('app.yaml') and options.verbose:
            print "Creating app.yaml..."
        copy_helper('gae_template', os.curdir, context)

        if options.install:
            self.install_libs(options, args)

    def install_libs(self, options, args):
        """install dependencies in lib dir.
        """
        from werkzeug import import_string
        libs = set(['kalapy', 'werkzeug', 'jinja2',
                    'babel', 'pytz', 'simplejson'] + args)

        if not os.path.exists("lib"):
            os.mkdir("lib")

        for lib in libs:
            mod = import_string(lib)
            src = mod.__file__
            if src.endswith('.pyc'):
                src = src[:-1]
            if src.endswith('__init__.py'):
                src = os.path.dirname(mod.__file__)
                dest = os.path.join("lib", lib)
                if not os.path.exists(dest):
                    if options.verbose:
                        print "Copying %s" % lib
                    shutil.copytree(src, dest)
            else:
                dest = os.path.join("lib", "%s" % os.path.basename(src))
                if os.path.exists(dest):
                    continue
                if options.verbose:
                    print "Copying %s" % os.path.basename(dest)
                shutil.copy2(src, dest)

        def do_clean(args, path, files):
            for f in files:
                f = os.path.join(path, f)
                __, x = os.path.splitext(f)
                if x in args:
                    os.remove(f)
        os.path.walk("lib", do_clean, ['.pyc', '.pyo', '.so'])
