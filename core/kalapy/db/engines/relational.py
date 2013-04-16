"""
kalapy.db.engines.relational
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module provides an abstract implementation of database engine interface
for relational database systems. Engines for an RDBMS should inherit from the
:class:`RelationalDatabase` instead of :class:`IDatabase`.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LICENSE for more details.
"""
import re

from kalapy.db.engines.interface import IDatabase
from kalapy.db.model import Model
from kalapy.db.reference import ManyToOne


__all__ = ('RelationalDatabase', 'QueryBuilder',)


class RelationalDatabase(IDatabase):

    data_types = {}

    schema_mime = 'text/x-sql'

    def __init__(self, name, host=None, port=None, user=None, password=None):
        super(RelationalDatabase, self).__init__(name, host, port, user, password)
        self.connection = None

    def get_data_type(self, field):
        """Get the internal datatype for the given field supported by the
        database.

        :param field: an instance of :class:`Field`
        """
        try:
            return self.data_types[field.data_type] % dict(
                [(k, getattr(field, k)) for k in dir(field)])
        except KeyError:
            raise TypeError(
                _('Unsupported datatype %(type)r', type=field.data_type))

    def close(self):
        if self.connection:
            self.connection.close()
        self.connection = None

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def cursor(self):
        """Return a `dbapi2` complaint cursor instance.
        """
        if not self.connection:
            self.connect()
        return self.connection.cursor()

    def fix_quote(self, sql):
        """Subclass should override this method to fix quotation marks.
        """
        return sql

    def get_field_sql(self, field, for_alter=False):
        res = '"%s" %s' % (field.name, self.get_data_type(field))
        if not for_alter:
            if field.is_required:
                res = "%s NOT NULL" % res
        return res

    def get_fk_sql(self, field):
        res = 'FOREIGN KEY ("%s") REFERENCES "%s" ("key")' % (
                field.name, field.reference._meta.table)
        if field.cascade:
            res = '%s ON DELETE CASCADE' % res
        elif field.is_required:
            res = '%s ON DELETE RESTRICT' % res
        elif field.cascade is None:
            res = '%s ON DELETE SET NULL' % res
        return res

    def get_create_sql(self, model):

        fields = [f for f in model.fields().values() if f._data_type is not None]

        # create columns
        output = [self.get_field_sql(f) for f in fields]

        # generate unique constraints
        for item in model._meta.unique:
            output.append('UNIQUE(%s)' % ", ".join(['"%s"' % f.name for f in item]))

        # generate foreign key constraints
        for field in fields:
            if isinstance(field, ManyToOne):
                output.append(self.get_fk_sql(field))

        output = ",\n    ".join(output)
        output = 'CREATE TABLE "%s" (\n    %s\n);' % (model._meta.table, output)
        return self.fix_quote(output)

    def schema_table(self, model):
        return self.get_create_sql(model)

    def create_table(self, model):
        if not self.exists_table(model):
            cursor = self.cursor()
            cursor.execute(self.get_create_sql(model))

    def drop_table(self, model):
        if self.exists_table(model):
            cursor = self.cursor()
            cursor.execute(
                    self.fix_quote('DROP TABLE "%s"' % model._meta.table))

    def alter_table(self, model, name=None):
        cursor = self.cursor()
        if name:
            cursor.execute(
                    self.fix_quote('ALTER TABLE "%s" RENAME TO "%s"' % (
                        name, model._meta.table)))
        #TODO: alter columns if changed

    def lastrowid(self, cursor, model):
        return cursor.lastrowid

    def update_records(self, instance, *args):

        result = []
        instances = [instance] + list(args)

        cursor = self.cursor()

        for obj in instances:

            assert isinstance(obj, Model), 'update_records expects Model instances'

            items = obj._to_database_values(True).items()

            keys = [x[0] for x in items]
            vals = [x[1] for x in items]

            if not obj.is_saved:
                keys = ['"%s"' % k for k in keys]
                sql = 'INSERT INTO "%s" (%s) VALUES (%s)' % (
                        obj._meta.table,
                        ", ".join(keys),
                        ", ".join(['%s'] * len(vals)))
                cursor.execute(self.fix_quote(sql), vals)
                obj._key = self.lastrowid(cursor, obj.__class__)
                result.append(obj.key)
            else:
                keys = ", ".join(['"%s" = %%s' % k for k in keys])
                sql = 'UPDATE "%s" SET %s WHERE "key" = %%s' % (obj._meta.table, keys)

                vals.append(obj.key)
                cursor.execute(self.fix_quote(sql), vals)
                result.append(obj.key)

            obj.set_dirty(False)

        return result

    def delete_records(self, instance, *args):

        assert isinstance(instance, Model), 'delete_records expectes Model instances'

        instances = [instance]
        instances.extend(args)

        keys = [o.key for o in instances]

        sql = 'DELETE FROM "%s" WHERE "key" IN (%s)' % (
                            instance._meta.table, ", ".join(['%s'] * len(keys)))

        cursor = self.cursor()
        cursor.execute(self.fix_quote(sql), keys)

        for obj in instances:
            obj._key = None
            obj.set_dirty(True)

        return keys

    def query_builder(self, qset):
        return QueryBuilder(qset)

    def fetch(self, qset, limit, offset):
        cursor = self.cursor()
        sql, params = self.query_builder(qset).select('*', limit, offset)
        cursor.execute(self.fix_quote(sql), params)
        names = [desc[0] for desc in cursor.description]
        for row in cursor.fetchall():
            yield dict([(name, row[i]) for i, name in enumerate(names)])

    def count(self, qset):
        cursor = self.cursor()
        sql, params = self.query_builder(qset).select('count("key")')
        sql = re.sub(' ORDER BY "\w+" (ASC|DESC)', '', sql)
        cursor.execute(self.fix_quote(sql), params)
        try:
            return cursor.fetchone()[0]
        except:
            return 0


class QueryBuilder(object):
    """The SQL query builder for relational database engines.
    """

    op_alias = {
        '<': 'lt',
        '>': 'gt',
        '>=': 'gte',
        '<=': 'lte',
        '==': 'eq',
        '!=': 'neq',
        '=': 'like',
        'in': 'in',
        'not in': 'not_in',
    }

    def __init__(self, qset):
        self.qset = qset
        self.model = qset.model
        self.order = None
        self.all = []

        try:
            self.order = "ORDER BY \"%s\" %s" % tuple(qset.order)
        except:
            pass

        for q in qset:
            if len(q.items) > 1:
                statements = []
                params = []
                for item in q.items:
                    name, op, val = item
                    s, p = self.parse(name, op, val)
                    statements.append(s)
                    if isinstance(p, (list, tuple)):
                        params.extend(p)
                    else:
                        params.append(p)
                self.all.append((" OR ".join(statements), params))
            else:
                name, op, val = q.items[0]
                self.all.append(self.parse(name, op, val))

    def select(self, what, limit=None, offset=None):
        """Build the select query.
        """
        query = "SELECT %s FROM \"%s\"" % (what, self.model._meta.table)
        if self.all:
            query = "%s WHERE %s" % (query, " AND ".join(["(%s)" % s for s, b in self.all]))
        if self.order:
            query = "%s %s" % (query, self.order)
        if limit > -1:
            query = "%s LIMIT %d" % (query, limit)
            if offset > -1:
                query = "%s OFFSET %d" % (query, offset)

        params = []
        for q, v in self.all:
            if isinstance(v, (list, tuple)):
                params.extend(v)
            else:
                params.append(v)

        return query, params

    def parse(self, name, operator, value):
        """Parse the simple query statement.

        :param name: name of the field
        :param operator: the operator
        :param value: the filter values

        :returns: a tuple `(str, value)`
        :rtype: tuple
        """
        field = self.model._meta.fields[name]

        op = operator.lower()
        op = self.op_alias.get(op, op)

        handler = getattr(self, 'handle_%s' % op)
        validator = getattr(self, 'validate_%s' % op, self.validate)
        value = validator(field, value)

        return handler(name, value), value

    def validate(self, field, value):
        return field.python_to_database(value)

    def validate_in(self, field, value):
        assert isinstance(value, (list, tuple))
        return [field.python_to_database(v) for v in value]

    def validate_not_in(self, field, value):
        return self.validate_in(field, value)

    def handle_in(self, name, value):
        return '"%s" IN (%s)' % (name, ', '.join(['%s'] * len(value)))

    def handle_not_in(self, name, value):
        assert isinstance(value, (list, tuple))
        return '"%s" NOT IN (%s)' % (name, ', '.join(['%s'] * len(value)))

    def handle_like(self, name, value):
        return '"%s" LIKE %%s' % (name)

    def handle_eq(self, name, value):
        return '"%s" = %%s' % (name)

    def handle_neq(self, name, value):
        return '"%s" != %%s' % (name)

    def handle_gt(self, name, value):
        return '"%s" > %%s' % (name)

    def handle_lt(self, name, value):
        return '"%s" < %%s' % (name)

    def handle_gte(self, name, value):
        return '"%s" >= %%s' % (name)

    def handle_lte(self, name, value):
        return '"%s" <= %%s' % (name)
