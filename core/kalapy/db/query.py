"""
kalapy.db.query
~~~~~~~~~~~~~~~

This module implements Query class, which can be used to query for records
from the database.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LICENSE for more details.

"""
import re
from copy import deepcopy


__all__ = ('Query', 'Q')

_FILTER_REGEX = re.compile(
    '^\s*([\w]+)\s+(>|<|>=|<=|==|!=|=|in|not in)\s*$', re.I)

class Q(object):
    """Encapsulates query filters as objects that can then be used to perform
    logical ``OR`` operation using ``|`` operator. For example::

        q = Query(User).filter(Q('name =', 'some%')|Q('age >=', 18))

    The ``AND`` operation is not supported as ``AND`` is the default behaviour
    of multiple :func:`Query.filter` calls.
    """
    def __init__(self, query, value):
        try:
            name, op = _FILTER_REGEX.match(query).groups()
        except:
            raise Exception(
                _('Malformed filter string: %(filter)s', filter=query))
        self.items = [(name, op, value)]

    def validate(self, model):
        for i, (name, operator, value) in enumerate(self.items):
            if name not in model._meta.fields:
                raise AttributeError(
                    _('No such field %(name)r in model %(model)r',
                        name=name, model=model._meta.name))

            field = model._meta.fields[name]
            if operator in ('in', 'not in'):
                assert isinstance(value, (list, tuple))
                value = [field.python_to_database(v) for v in value]
            else:
                value = field.python_to_database(value)
            self.items[i] = (name, operator, value)
        return self

    def __deepcopy__(self, meta):
        n, o, v = self.items[0]
        q = Q('%s %s' % (n, o), None)
        q.items = deepcopy(self.items, meta)
        return q

    def __or__(self, other):
        q = deepcopy(self)
        q.items.extend(other.items)
        return q

    def __repr__(self):
        if len(self.items) == 1:
            return str(self.items[0])
        return "(" + " OR ".join(map(str, self.items)) + ")"


class QSet(object):
    """A container of all the :class:`db.Q` instances of a :class:`db.Query`.

    It implements :meth:`fetch` and :meth:`count` which in turns calls database
    engine specific version of ``database.fetch`` and ``database.count`` methods.
    """

    def __init__(self, model):
        self.model = model
        self.items = []
        self.order = None

    def append(self, q):
        self.items.append(q.validate(self.model))

    def fetch(self, limit, offset):
        from kalapy.db.engines import database
        return database.fetch(self, limit, offset)

    def count(self):
        from kalapy.db.engines import database
        return database.count(self)

    def __deepcopy__(self, meta):
        qs = QSet(self.model)
        qs.order = self.order
        qs.items = deepcopy(self.items, meta)
        return qs

    def __iter__(self):
        return iter(self.items)

    def __repr__(self):
        return " AND ".join(map(repr, self.items))


class Query(object):
    """The `Query` class provides methods to filter and fetch records from the
    database with simple pythonic statements.

    >>> users = Query(User).filter('name =', 'some%') \
    ...                    .filter('age >', 18)
    >>> users.order('-age')
    >>> first_ten = users.fetch(10, offset=0)
    >>> for user in first_ten:
    >>>     print 'Name:', user.name

    The format of the query string should be ``field_name operator``, where
    ``field_name`` is any field defined in the current model and `openrator` can
    be one of ``=, ==, !=, <, >, <=, >=, in, not in``.

    Also, ``=`` operator has special meaning, it stands for case-insensitive
    match (LIKE in some DBMS). You should use ``==`` for exact match.

    An instance of :class:`Query` can be constructed by passing :class:`Model`
    subclass as first argument. The contructor also accept a callable as a second
    argument to apply map on the result set.

    >>> names = Query(User, lambda obj: obj.name).filter('name =', 'some%').fetch(-1)
    >>> print names
    ['some', 'someone', 'some1']

    :param model: a model, subclass of :class:`Model`
    :param mapper: a `callback` function to map query result
    """

    def __init__(self, model, mapper=None):
        """Create a new instance of :class:`Query` for the given `model`. The result
        set will be mapped with the given mapper.
        """
        if mapper and not callable(mapper):
            raise TypeError('mapper should be callable')

        self.__model = model
        self.__mapper = mapper
        self.__qset = QSet(model)

    def filter(self, *args):
        """Return a new :class:`Query` instance with the given query ANDed with
        current query set.

        For example::

            q = Query(User).filter('name =', 'some%').filter('age >=', 20)
            q1 = q.filter('dob >=', '2001-01-01')
            q2 = q.filter('dob <', '2001-01-01')

        The ``OR`` operation can be performed using :class:`db.Q` like::

            from kalapy.db import Query, Q

            q = Query(User).filter(Q('name =', 'some%') | Q('age >=', 20))
            q.fetchall()

        :param query: The query string or an instance of :class:`db.Q`
        :param value: The filter value, ignored if query is :class:`db.Q`

        :raises: :class:`DatabaseError`, :class:`FieldError`
        :returns: A new instance of :class:`Query`
        """
        assert 0 < len(args) < 3, 'invalid number of arguments'
        if not isinstance(args[0], Q):
            assert len(args) == 2, 'value argument missing'
            q = Q(*args)
        else:
            q = args[0]
        query = deepcopy(self)
        query.__qset.append(q)
        return query

    def order(self, spec):
        """Order the query result with given spec.

        >>> q = Query(User).filter("name =", "some%").filter("age >=", 20)
        >>> q.order("-age")

        :param spec: field name, if prefixed with `-` order by DESC else ASC
        """
        assert isinstance(spec, basestring)
        self.__qset.order = (spec, 'ASC')
        if spec.startswith('-'):
            self.__qset.order = (spec[1:], 'DESC')
        return self

    def fetch(self, limit, offset=0):
        """Fetch the given number of records from the query object from the given offset.

        If limit is `-1` fetch all records.

        >>> q = Query(User).filter("name =", "some%").filter("age >=", 20)
        >>> for obj in q.fetch(20):
        >>>     print obj.name

        :param limit: number of records to be fetch, if -1 fetch all
        :param offset: offset from where to fetch records should be >= 0
        :type limit: integer
        :type offset: integer or None

        :returns: list of model instances or content if mapper is applied
        :rtype: list
        """
        result = map(self.__model._from_database_values,
                        self.__qset.fetch(limit, offset))
        if self.__mapper:
            return map(self.__mapper, result)
        return result

    def fetchone(self, offset=0):
        """Fetch a single record from the query object with given offset.

        :returns: model instance or None
        """
        res = self.fetch(1, offset)
        return res[0] if res else None

    def fetchall(self):
        """Fetch all records. An alias to :meth:`fetch` with limit as -1.
        """
        return self.fetch(-1)

    def first(self):
        """Fetch the first record from the query object.
        """
        return self.fetchone()

    def count(self):
        """Return the number of records in the query object.
        """
        return self.__qset.count()

    def delete(self):
        """Delete all records matched by this query.

        For example:

        >>> Query(User).filter('name =', 'some%').delete()

        will delete all the User records by matching name starting with 'some'.
        """
        for obj in self.fetch(-1):
            obj.delete()

    def update(self, **kw):
        """Update all the matched records with the given keywords mapping to
        the field properties of the model of this query.

        For example:

        >>> Query(User).filter('name =', 'some%').update(lang='en_EN')

        will update all the User records by matching name starting with 'some'
        by updating `lang` to `en_EN`.

        :keyword kw: keyword args mapping to the field properties
        """
        for obj in self.fetch(-1):
            for k, v in kw.items():
                if k in obj._meta.fields:
                    setattr(obj, k, v)
            obj.save()

    def __getitem__(self, arg):
        if isinstance(arg, (int, long)):
            try:
                return self.fetch(1, arg)[0]
            except IndexError:
                raise IndexError(
                    _('The query returned fewer then %(num)r results', num=arg))
        else:
            raise ValueError(
                _('Only integer indices are supported.'))

    def __iter__(self):
        offset = -1
        try:
            while True:
                offset += 1
                yield self.fetch(1, offset)[0]
        except Exception:
            pass

    def __deepcopy__(self, meta):
        q = Query(self.__model, self.__mapper)
        q.__qset = deepcopy(self.__qset, meta)
        return q

    def __repr__(self):
        return repr(self.__qset)
