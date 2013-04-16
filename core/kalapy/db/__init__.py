"""
kalapy.db
~~~~~~~~~

This module implements the DAL API, an unique database abstraction layer
inspired of OpenERP and Django ORM.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LICENSE for more details.
"""
from kalapy.db.engines import DatabaseError, IntegrityError, \
    commit, rollback, run_in_transaction

from kalapy.db.fields import *
from kalapy.db.reference import *
from kalapy.db.model import *
from kalapy.db.query import *

# remove module references to hide them from direct outside access
map(lambda n: globals().pop(n), ['engines', 'model', 'fields', 'query', 'reference'])
