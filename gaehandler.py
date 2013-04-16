#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys
reload(sys)
sys.setdefaultencoding('utf8')

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_CORE = os.path.join(PROJECT_DIR, 'core')
PROJECT_LIB = os.path.join(PROJECT_DIR, 'lib')
WORD_LIB = os.path.join(PROJECT_DIR, 'wordlib')

sys.path = [PROJECT_CORE] +[PROJECT_LIB]+[WORD_LIB] + sys.path

from google.appengine.ext.webapp import util
from kalapy.web import Application
from kalapy.admin import setup_environment

import settings
setup_environment(settings)

def main():
    app = Application()
    util.run_wsgi_app(app)

if __name__ == "__main__":
    main()

