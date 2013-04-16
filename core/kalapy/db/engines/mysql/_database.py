"""
kalapy.db.engines.mysql
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

MySQL backend engine.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LICENSE for more details.
"""
import MySQLdb as dbapi
from MySQLdb.converters import conversions
from MySQLdb.constants import FIELD_TYPE

from kalapy.db.engines import utils
from kalapy.db.engines.relational import RelationalDatabase


__all__ = ('DatabaseError', 'IntegrityError', 'Database')


DatabaseError = dbapi.DatabaseError
IntegrityError = dbapi.IntegrityError

CONV = conversions.copy()
CONV.update({
    FIELD_TYPE.DECIMAL: utils.decimal_to_python,
})

class Database(RelationalDatabase):

    data_types = {
        "key"       :   "INTEGER AUTO_INCREMENT PRIMARY KEY",
        "reference" :   "INTEGER",
        "char"      :   "VARCHAR(%(size)s)",
        "text"      :   "LONGTEXT",
        "integer"   :   "INTEGER",
        "float"     :   "DOUBLE",
        "decimal"   :   "DECIMAL(%(max_digits)s, %(decimal_places)s)",
        "boolean"   :   "BOOL",
        "datetime"  :   "DATETIME",
        "binary"    :   "BLOB",
    }

    schema_mime = 'text/x-mysql'

    def __init__(self, name, host=None, port=None, user=None, password=None):
        super(Database, self).__init__(name, host, port, user, password)
        self.connection = None

    def connect(self):
        if self.connection is not None:
            return self

        args = {
            'db': self.name,
            'charset': 'utf8',
            'use_unicode': True,
            'conv': CONV,
        }
        if self.user:
            args['user'] = self.user
        if self.password:
            args['passwd'] = self.password
        if self.host:
            args['host'] = self.host
        if self.port:
            args['port'] = self.port
        self.connection = dbapi.connect(**args)
        return self

    def fix_quote(self, sql):
        return sql.replace('"', '`')

    def get_create_sql(self, model):
        sql = super(Database, self).get_create_sql(model)
        return "%s ENGINE=`InnoDB`;" % (sql[:-1],)

    def exists_table(self, model):
        cursor = self.cursor()
        cursor.execute("""
            SELECT COUNT(*)
                FROM information_schema.tables
                    WHERE table_name = %s AND table_schema = %s;
            """, (model._meta.table, self.name,))
        return bool(cursor.fetchone()[0])

    def lastrowid(self, cursor, model):
        cursor.execute('SELECT LAST_INSERT_ID()')
        return cursor.fetchone()[0]
