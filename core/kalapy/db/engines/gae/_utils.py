"""
kalapy.db.engines.gae
~~~~~~~~~~~~~~~~~~~~~

Implementes Google AppEngine backend support functions.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LICENSE for more details.
"""
import os, sys


def setup_stubs():

    GAE_HOME = os.environ.get('GAE_HOME')
    if not GAE_HOME:
        print "Set environment variable GAE_HOME pointing to AppEngine SDK."
        sys.exit(0)

    if not os.path.exists(os.path.join(GAE_HOME, "dev_appserver.py")):
        print "The environment variable GAE_HOME doesn't point to AppEngine SDK."
        sys.exit(0)

    from kalapy.conf import settings
    sys.path = [os.path.join(settings.PROJECT_DIR, 'lib'), GAE_HOME] + sys.path

    from dev_appserver import fix_sys_path
    fix_sys_path()
    from google.appengine.tools.dev_appserver import SetupStubs, LoadAppConfig
    from google.appengine.tools.dev_appserver_main import ParseArguments

    args, option_dict = ParseArguments(['', settings.PROJECT_DIR])
    config, matcher = LoadAppConfig(settings.PROJECT_DIR, {})
    SetupStubs(config.application, **option_dict)

