"""
kalapy.db.engines.gae
~~~~~~~~~~~~~~~~~~~~~

Implementes Google AppEngine backend.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LICENSE for more details.
"""
import re
from itertools import chain

try:
    from google.appengine.api import datastore
except ImportError:
    from _utils import setup_stubs
    setup_stubs()
    from google.appengine.api import datastore

from google.appengine.api import datastore_errors, datastore_types

from kalapy.db.engines.interface import IDatabase
from kalapy.db.model import Model
from kalapy.conf import settings

__all__ = ('DatabaseError', 'IntegrityError', 'Database')


CONV = {
    'text': datastore_types.Text,
}


class DatabaseError(Exception):
    pass


class IntegrityError(DatabaseError):
    pass


class Database(IDatabase):

    schema_mime = 'text/x-python'

    def __init__(self, name, host=None, port=None, user=None, password=None):
        super(Database, self).__init__(name, host, port, user, password)
        self.check_unique = settings.DATABASE_OPTIONS.get('check_unique', True)
        self.check_reference = settings.DATABASE_OPTIONS.get('check_reference', True)

    def connect(self):
        pass

    def close(self):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass

    def run_in_transaction(self, func, *args, **kw):
        return datastore.RunInTransaction(func, *args, **kw)

    def schema_table(self, model):
        result = "class %s(db.Model):" % model.__name__
        for name, field in model.fields().items():
            result += "\n    %s = db.%s(...)" % (name, field.__class__.__name__)
        return result

    def exists_table(self, model):
        pass

    def create_table(self, model):
        pass

    def alter_table(self, model, name=None):
        pass

    def drop_table(self, model):
        model.all().delete()

    def update_records(self, instance, *args):

        result = []
        instances = [instance]
        instances.extend(args)

        for obj in instances:
            if not isinstance(instance, Model):
                raise TypeError('update_records expects Model instances')
            items = obj._to_database_values(True, conv=CONV)

            if not obj.is_saved:
                obj._payload = datastore.Entity(obj._meta.table)

            # test unique contraints
            if self.check_unique:
                check_unique(obj, items)

            obj._payload.update(items)
            obj._key = str(datastore.Put(obj._payload))

            result.append(obj.key)
            obj.set_dirty(False)

        return result

    def delete_records(self, instance, *args):

        instances = [instance]
        instances.extend(args)

        for obj in instances:
            if not isinstance(instance, Model):
                raise TypeError('delete_records expectes Model instances')

            # check referential integrity and then delete
            if self.check_reference:
                check_integrity(obj)

        keys = [obj.key for obj in instances]
        datastore.Delete(keys)

        for obj in instances:
            obj._key = None
            obj.set_dirty(True)

        return keys

    def fetch(self, qset, limit, offset):
        limit = datastore.MAXIMUM_RESULTS if limit == -1 else limit
        orderings = []
        try:
            name, how = qset.order
            how = Query.ASCENDING if how == 'ASC' else Query.DESCENDING
            orderings = [(name, how)]
        except:
            pass

        keys = self._keys(qset)
        result = []

        if keys: # if only key filter
            result = [e for e in datastore.Get(keys) if e]
        else: # else build query, the results should be ANDed
            query_set = self._build_query_set(qset, orderings)
            result_set = [[e for e in q.Get(limit, offset) if e] for q in query_set]
            keys = [set([e.key() for e in result]) for result in result_set]
            keys = reduce(lambda a, b: a & b, keys)

            result = {}
            for e in chain(*tuple(result_set)):
                if e.key() in keys:
                    result.setdefault(e.key(), e)
            result = result.values()

        for e in sort_result(result, orderings)[:limit]:
            yield dict(e, key=str(e.key()), _payload=e)

    def count(self, qset):
        return len(list(self.fetch(qset, -1, 0)))

    def _keys(self, qset):
        if len(qset.items) == 1:
            q = qset.items[0]
            if len(q.items) == 1 and q.items[0][0] == 'key':
                keys = q.items[0][2]
                if not isinstance(keys, (list, tuple)):
                    return [keys]
                return keys
        return []

    def _build_query_set(self, qset, orderings):

        kind = qset.model._meta.table

        def _query(item):
            name, op, value = item
            if op == '=':
                return LikeQuery(kind, name, value, orderings)
            elif op == 'not in':
                return NotInQuery(kind, name, value, orderings)
            elif op == 'in':
                return MultiQuery(
                    [Query(kind, {'%s =' % name: v}, orderings) for v in value], orderings)
            elif op == '!=':
                return MultiQuery(
                    [Query(kind, {'%s <' % name: value}, orderings),
                     Query(kind, {'%s >' % name: value}, orderings)], orderings)
            else:
                return Query(kind, {'%s %s' % (name, op): value}, orderings)

        result = []
        for q in qset:
            if len(q.items) > 1:
                result.append(
                    MultiQuery([_query(item) for item in q.items], orderings))
            else:
                result.append(_query(q.items[0]))

        if not result:
            return [Query(kind, {}, orderings)]

        return result


class Query(datastore.Query):
    """This class extends ``datastore.Query`` class to handles `key` filters.
    """
    def __init__(self, kind, filters, orderings=None):
        super(Query, self).__init__(kind, filters)
        if orderings:
            self.Order(*orderings)

    def IsKeysOnly(self):
        return False

    def Run(self, **kwargs):
        try:
            try:
                return iter([datastore.Get(self['key ='])])
            except KeyError:
                return iter([datastore.Get(self['key =='])])
        except datastore_errors.EntityNotFoundError:
            return iter([None])
        except KeyError:
            return super(Query, self).Run(**kwargs)


class CustomQuery(Query):
    """This call is used to implement custom query classes to handle
    filters not supported by appengine datastore api.

    The subclasses should override :meth:`validate` method to filter
    the final result.

    :param kind: entity type
    :param find: name of the entity property on which filter it applied.
    :param value: the value passed to the filter.
    :param orderings: order specs
    """

    def __init__(self, kind, field, value, orderings=None):
        super(CustomQuery, self).__init__(kind, {}, orderings)
        self.field = field
        self.value = value

    def validate(self, value):
        """Validate the value and return True or False.
        """
        raise NotImplementedError

    def Get(self, limit, offset):
        final = []
        while len(final) < limit:
            result = super(CustomQuery, self).Get(limit, offset)
            if not result:
                break
            for item in result:
                if self.validate(item[self.field]):
                    final.append(item)
            offset += limit
        return final


class NotInQuery(CustomQuery):
    """Implements ``not in`` filter.
    """
    def __init__(self, kind, field, value, orderings=None):
        super(NotInQuery, self).__init__(kind, field, value, orderings)

    def validate(self, value):
        return value not in self.value


class MatchQuery(CustomQuery):
    """Implementes ``match`` filter.
    """
    def __init__(self, kind, field, value, orderings=None):
        super(MatchQuery, self).__init__(kind, field, value, orderings)
        if not isinstance(value, basestring):
            value = str(value)
        self.regex = re.compile(value, re.I|re.M)

    def validate(self, value):
        return self.regex.match(value) is not None


class LikeQuery(MatchQuery):
    """Implementes ``like`` filter.
    """
    def __init__(self, kind, field, value, orderings=None):
        if not isinstance(value, basestring):
            value = str(value)
        if value.startswith('%') and not value.endswith('%'):
            value = '.*(%s)$' % value[1:]
        elif value.endswith('%') and not value.startswith('%'):
            value = '^(%s).*' % value[:-1]
        elif value.startswith('%') and value.endswith('%'):
            value = '.*(%s).*' % value[1:-1]
        else:
            value = '^(%s)$' % value
        super(LikeQuery, self).__init__(kind, field, value, orderings)


class MultiQuery(datastore.MultiQuery):

    def IsKeysOnly(self):
        return False


def sort_result(result, orderings):
    """A helper function to sort the final result.
    """
    try:
        name, how = orderings[0]
    except:
        return result

    def compare(a, b):
        if how == 2:
            return -cmp(a[name], b[name])
        return cmp(a[name], b[name])

    result.sort(compare)
    return result


def check_unique(model_instance, values):
    """A helper function to check unique contraints.
    """
    from kalapy.i18n import ngettext
    for items in model_instance._meta.unique:
        if [n for n in items if n.name in values]:
            q = model_instance.all()
            for field in items:
                q = q.filter('%s ==' % field.name, values.get(field.name, ''))
            if q.fetchone():
                msg = ngettext('column %(name)s is not unique',
                               'columns %(name)s are not unique',
                               len(items),
                               name=", ".join([f.name for f in items]))
                raise IntegrityError(msg)
    return model_instance


def check_integrity(model_instance):
    """A helper function to check referential integrity.
    """
    from kalapy.db.reference import OneToMany, ManyToMany
    for field in model_instance._meta.virtual_fields.values():
        if isinstance(field, OneToMany):
            o2m = getattr(model_instance, field.name)
            if not o2m.all().count():
                continue
            reverse = getattr(field.reference, field.reverse_name)
            if reverse.cascade is None:
                o2m.all().update(**dict([(reverse.name, None)]))
            elif reverse.cascade:
                o2m.clear()
            else:
                raise IntegrityError(
                    _('Key %(key)r is still referenced from table %(name)r',
                        key=model_instance.key, name=field.reference._meta.table))
        if isinstance(field, ManyToMany):
            if not field.m2m.all().count():
                continue
            if field.cascade:
                q = field.m2m.all().filter('%s ==' % field.source, model_instance.key)
                q.delete()
            else:
                raise IntegrityError(
                    _('Key %(key)r is still referenced from table %(name)r',
                        key=model_instance.key, name=field.m2m._meta.table))

    return model_instance

