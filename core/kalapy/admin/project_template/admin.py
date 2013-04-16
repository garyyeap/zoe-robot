#!/usr/bin/env python
import os, sys
from os.path import dirname, abspath

from kalapy import admin


if abspath(os.curdir) != abspath(dirname(__file__)):
    print "Error: The admin script should be run from the project dir."
    sys.exit(1)

try:
    import settings
except ImportError:
    print "Error: Can't find 'settings.py'"
    sys.exit(1)

if __name__ == "__main__":
    admin.execute_command(None, settings)
