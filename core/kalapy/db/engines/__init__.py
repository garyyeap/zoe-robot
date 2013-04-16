"""
kalapy.db.engines
~~~~~~~~~~~~~~~~~

This module provides database backend storage interface. Dynamically
loads the configured storage engine and exports implemented interfaces.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LICENSE for more details.
"""
import os

from werkzeug import import_string
from werkzeug.local import LocalStack

from kalapy.conf import settings, ConfigError
from kalapy.core import signals


__all__ = ('Database', 'DatabaseError', 'IntegrityError', 'database')


if not settings.DATABASE_ENGINE:
    settings.DATABASE_ENGINE = 'dummy'

engine = settings.DATABASE_ENGINE
engine = engine if '.' in engine else 'kalapy.db.engines.%s' % engine

try:
    engine = import_string(engine)
    Database = engine.Database
    DatabaseError = engine.DatabaseError
    IntegrityError = engine.IntegrityError
except (ImportError, AttributeError):
    raise ConfigError(
        _("Engine %(name)r not supported.", name=settings.DATABASE_ENGINE))


class Connection(object):

    __ctx = LocalStack()

    def __getattr__(self, name):
        if self.__ctx.top is None:
            self.connect()
        return getattr(self.__ctx.top, name)

    def connect(self):
        if self.__ctx.top is None:
            db = Database(
                    name=settings.DATABASE_NAME,
                    host=settings.DATABASE_HOST,
                    port=settings.DATABASE_PORT,
                    user=settings.DATABASE_USER,
                    password=settings.DATABASE_PASSWORD)
            self.__ctx.push(db)
        self.__ctx.top.connect()

    def close(self):
        if self.__ctx.top is not None:
            self.__ctx.top.close()
            self.__ctx.pop()


#: context local database connection
database = Connection()


def commit():
    """Commit the changes to the database.
    """
    database.commit()


def rollback():
    """Rollback all the changes made since the last commit.
    """
    database.rollback()


def run_in_transaction(func, *args, **kw):
    """A helper function to run the specified func in a transaction.
    """
    return database.run_in_transaction(func, *args, **kw)


def open_connection():
    """Open database connection when request started.
    """
    database.connect()


def close_connection():
    """Close database connection when request ends.
    """
    database.close()

def rollback_connection(error):
    """Rollback database connection, if there is any unhandled exception
    during request processing.
    """
    database.rollback()

# only register signals if database is configured.
if settings.DATABASE_NAME:
    signals.connect('request-started')(open_connection)
    signals.connect('request-finished')(close_connection)
    signals.connect('request-exception')(rollback_connection)
