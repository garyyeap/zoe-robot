"""
kalapy.db.engines.sqlite3
~~~~~~~~~~~~~~~~~~~~~~~~~

SQLite3 backend engine.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LICENSE for more details.
"""
import os, decimal
import sqlite3 as dbapi

from kalapy.db.engines import utils
from kalapy.db.engines.relational import RelationalDatabase


dbapi.register_converter('bool', lambda s: s == '1')
dbapi.register_converter('datetime', utils.datetime_to_python)
dbapi.register_converter('decimal', utils.decimal_to_python)
dbapi.register_adapter(decimal.Decimal, utils.decimal_to_database)
dbapi.register_adapter(str, utils.str_to_database)


__all__ = ('DatabaseError', 'IntegrityError', 'Database')


DatabaseError = dbapi.DatabaseError
IntegrityError = dbapi.IntegrityError


class Database(RelationalDatabase):

    data_types = {
        "key"       :   "INTEGER PRIMARY KEY AUTOINCREMENT",
        "reference" :   "INTEGER",
        "char"      :   "VARCHAR(%(size)s)",
        "text"      :   "TEXT",
        "integer"   :   "INTEGER",
        "float"     :   "FLOAT",
        "decimal"   :   "DECIMAL",
        "boolean"   :   "BOOL",
        "datetime"  :   "DATETIME",
        "binary"    :   "BLOB",
    }

    def connect(self):
        if self.connection is not None:
            return self

        if self.name != ":memory:":
            if not os.path.isfile(self.name):
                raise DatabaseError(
                    _("Database %(name)r doesn't exist.", name=self.name))

        self.connection = dbapi.connect(self.name, detect_types=dbapi.PARSE_DECLTYPES)
        return self

    def exists_table(self, model):
        cursor = self.cursor()
        cursor.execute("""
            SELECT "name" FROM sqlite_master
                WHERE type = "table" AND name = %s;
            """, (model._meta.table,))
        return bool(cursor.fetchone())


    def cursor(self):
        if not self.connection:
            self.connect()
        return self.connection.cursor(factory=SQLiteCursor)


class SQLiteCursor(dbapi.Cursor):

    def execute(self, query, params=()):
        query = self.convert_query(query, len(params))
        return super(SQLiteCursor, self).execute(query, params)

    def executemany(self, query, params_list):
        query = self.convert_query(query, len(params_list[0]))
        return super(SQLiteCursor, self).executemany(query, params_list)

    def convert_query(self, query, num_params):
        return query % tuple("?" * num_params)

