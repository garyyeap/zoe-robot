"""
kalapy.db.model
~~~~~~~~~~~~~~~

This module implements the Model class. It also exposes get_model
and get_models functions.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LICENSE for more details.
"""
import sys, types

from kalapy.core.pool import pool
from kalapy.db.fields import Field, AutoKey, FieldError
from kalapy.db.query import Query
from kalapy.utils.containers import OrderedDict


__all__ = ('Model', 'get_model', 'get_models')


get_model = pool.get_model
get_models = pool.get_models


class Options(object):

    def __init__(self):
        self.package = None
        self.name = None
        self.table = None
        self.fields = OrderedDict()
        self.virtual_fields = OrderedDict()
        self.ref_models = []
        self.unique = []

    @property
    def model(self):
        return get_model(self.name)

    def __setattr__(self, name, value):
        if getattr(self, name, None) is not None:
            raise AttributeError(
                _('Attribute %(name)r is already initialized', name=name))
        super(Options, self).__setattr__(name, value)


RESERVED_NAMES = {
    '_meta'     : '%r is reserved for internal use.',
    '__new__'   : '%r should not be overriden.',
    'key'       : '',
    '_payload'  : '',
}

def check_reserved_names(attrs):
    for name, attr in attrs.items():
        if name in RESERVED_NAMES:
            msg = RESERVED_NAMES[name] or '%r is reserved for internal use.'
            raise AttributeError(msg % name)


class ModelType(type):

    def __new__(cls, name, bases, attrs):

        super_new = super(ModelType, cls).__new__

        parents = [b for b in bases if isinstance(b, ModelType)]
        if not parents:
            # This is not a subclass of Model so do nothing
            return super_new(cls, name, bases, attrs)

        if len(parents) > 1:
            raise TypeError(_('Multiple inheritance is not supported.'))

        check_reserved_names(attrs)

        # always use the last defined base class in the inheritance chain
        # to maintain linear hierarchy.

        meta = getattr(parents[0], '_meta', None) or Options()

        try:
            parent = pool.get_model(meta.name) if meta.name else None
        except KeyError:
            parent = None

        if meta.package is None:
            try:
                meta.package = pool.get_package(attrs['__module__']).package.name
            except:
                meta.package = ''

        if parent:
            bases = list(bases)
            for i, base in enumerate(bases):
                if isinstance(base, ModelType):
                    bases[i] = parent
            bases = tuple(bases)

        cls = super_new(cls, name, bases, {
            '_meta': meta,
            '__module__': attrs.pop('__module__')})

        # update meta information
        unique = attrs.pop('__unique__', [])
        if meta.name is None:
            meta_name = name.lower()
            if meta.package:
                meta_name = '%s:%s' % (meta.package, meta_name)
            meta.name = meta_name
            meta.table = meta_name.replace(':', '_')

        # create primary key field if it is root model
        if not parent:
            cls.add_field(AutoKey())

        # overwrite model class in the pool
        pool.register_model(cls)

        cls._values = None

        # sort fields and set attributes to class
        attributes = attrs.items()
        attributes.sort(lambda a, b: cmp(
            getattr(a[1], '_serial', 0), getattr(b[1], '_serial', 0)))

        for name, attr in attributes:
            if isinstance(attr, Field):
                cls.add_field(attr, name)
                if attr.is_unique:
                    unique.append([attr])
            else:
                setattr(cls, name, attr)

        # prepare validators
        for name, attr in attributes:
            if name.startswith('validate_') and isinstance(attr, types.FunctionType):
                field = getattr(cls, name[9:], None)
                if isinstance(field, Field):
                    field._validator = getattr(cls, name) # use bound method

        # prepare unique constraints
        for item in unique:
            item = list(item) if isinstance(item, (list, tuple)) else [item]
            for i, field in enumerate(item):
                if isinstance(field, basestring):
                    try:
                        item[i] = field = getattr(cls, field)
                    except:
                        raise AttributeError(
                            _('No such field %(name)s.', field))
                assert isinstance(field, Field), 'expected a field'
            meta.unique.append(item)

        return cls

    def add_field(cls, field, name=None):

        name = name or field.name

        if not name:
            raise ValueError('Field has no name')

        if hasattr(cls, name):
            raise FieldError(
                _('Field %(name)r already defined in model %(model)r',
                    name=name, model=cls.__name__))

        setattr(cls, name, field)

        if getattr(field, 'is_virtual', None):
            cls._meta.virtual_fields[name] = field
        else:
            cls._meta.fields[name] = field

        field.__configure__(cls, name)

    def __repr__(cls):
        return "<Model %r: class %s>" % (cls._meta.name, cls.__name__)


class Model(object):
    """Model is the super class of all the objects of data entities in
    the database.

    Database tables declared as subclasses of :class:`Model` defines table
    properties as class members of type :class:`Field`. So if you want to
    publish an article with title, text, and publishing date, you would do
    it like this::

        class Article(db.Model):
            title = db.String(size=100, required=True)
            pubdate = db.DateTime(default_now=True)
            text = db.Text(required=True)

    You can extend a model by creating subclasses of that model but you
    can't inherit from more then one models. For example::

        class A(Model):
            a = String()

        class B(Model):
            b = String()

    You can extend `A` like this::

        class C(A):
            c = String()

    but not like this::

        class C(A, B):
            c = String()

    Another interesting behavior is that no matter which class it inherits
    from, it always inherits from the last class defined of that base model
    class. Let's see what does it means::

        class D(C):
            d = String()

        class E(C):
            e = String()

    Here even though `E` is extending `C` it is actually extending `D`, the
    last defined class of `A`. So `E` will have access to all the members
    of `D` not just from `C`. In other words the inheritance hierarchy will
    be forcefully maintained in linear fashion.

    Also whatever class you use of the hierarchy to instantiate you will
    always get an instance of the last defined class. For example:

    >>> obj = D()

    The `obj` will be a direct instance of `E` other then `D`.

    This way you can easily change the behavior of existing data models
    by simply creating subclasses without modifying existing code.

    Let's see an use case::

        class User(Model):
            name = String(size=100, required=True)
            lang = String(size=6, selection=[('en_EN', 'English'),
                                             ('fr_FR', 'French')])

            def do_something(self):
                ...
                ...

    Your application is using this class like this:

    >>> user = User(**kwargs)
    >>> user.do_something()
    >>> user.save()

    Where `kwargs` are `dict` of form variables coming from an http post request.

    Now if you think that `User` should have one more property `age` but you
    don't want to change your running system by modifying the source code,
    you simply create a subclass of `User` and all the members defined in that
    subclass will be available to the application.

    For example::

        class UserEx(User):
            age = db.Integer()

            def do_something(self):
                super(UserEx, self).do_something()
                ...
                ...

    So now if the html form has `age` field, the above code will work without any
    change and still saving `age` value. You can also change the behavior of the
    base class by overriding methods.

    Properties can also be initialized by providing keyword arguments to the
    constructor as keyword arguments.

    >>> u = User(name="some")
    >>> u.save()

    `key`

        Represents the key field for the data model (primary key).

    :param kw: keyword arguments mapping to instance properties.
    """

    __metaclass__ = ModelType

    def __new__(cls, **kw):
        if cls is Model:
            raise TypeError(_("You can't create instance of Model class"))
        klass = pool.get_model(cls)
        return super(Model, cls).__new__(klass)

    def __init__(self, **kw):
        """Create a new instance of this model.
        """

        #: stores record id
        self._key = None

        #: stores database specific information
        self._payload = None

        #: stores record values
        self._values = {}

        #: stores dirty information
        self._dirty = {}

        for field in self.fields().values():
            if field.name in kw and not field.empty(kw[field.name]):
                value = kw[field.name]
            elif field.default is not None:
                value = field.default
            else:
                continue
            field.__set__(self, value)

    @property
    def is_saved(self):
        """Whether the model is saved in database or not.
        """
        return  self._key is not None

    @property
    def is_dirty(self):
        """Check if the instance is dirty. An instance is dirty if it's
        properties are changed since it is saved last time.

        :returns: True if dirty, else False
        """
        return not self.is_saved or self._dirty

    def set_dirty(self, dirty=True):
        """Set the instance as dirty or clean.

        :param dirty: if True set dirty else set clean
        """
        self._dirty = dict.fromkeys(self._values, True) if dirty else {}

    def _to_database_values(self, dirty=False, conv=None):
        """Return values to be stored in database table for this model instance.

        If ``dirty`` is True only return field values marked as dirty else returns
        all values.

        The ``conv`` is a dict of data_type and custom convertors that can be
        used to convert the field values.

        :param dirty: if True only return values of fields marked dirty
        :param conv: convertors for specific types

        :returns: a dict, key-value maping of this model's fields.
        """
        fields = self.fields().values()
        if dirty:
            fields = [f for f in fields if f.name in self._dirty]

        result = {}
        for field in fields:
            if field.name == 'key': continue
            value = field.python_to_database(self._values[field.name])
            if conv and field.data_type in conv:
                value = conv[field.data_type](value)
            result[field.name] = value
        return result

    @classmethod
    def _from_database_values(cls, values):
        """Create an instance of this model which properties initialized with
        the given values fetched from database.

        :param values: mapping of name, value to instance properties

        :returns: an instance of this model
        """
        values = dict(values)

        obj = cls()
        obj._key = values.pop('key', None)
        obj._payload = values.pop('_payload', None)

        fields = obj.fields()
        for k, v in values.items():
            values[k] = fields[k].database_to_python(v)

        obj._values.update(values)
        obj._dirty = {}
        return obj

    def _get_related(self):
        """Get the list of all related model instances associated with this
        model instance. Used to get all dirty instances of related model
        instances referenced by ManyToOne and OneToOne properties.

        .. notes::

            For internal use only.

        :returns: list of related model instances
        """
        from reference import IRelation

        related = []
        for field in self._meta.fields.values():
            if isinstance(field, IRelation) and field.name in self._values:
                value = self._values[field.name]
                if isinstance(value, Model) and value.is_dirty:
                    related.append(value)
        return related

    def save(self):
        """Writes the instance to the database.

        If the instance is created, a new record will be added to the database
        else if it is loaded from database, the record will be updated.

        It also saves all dirty instances of related model instances referenced
        by :class:`ManyToOne` properties.

        :returns: an unique key id
        :raises: :class:`DatabaseError` if instance could not be commited.
        """
        if self.is_saved and not self.is_dirty:
            return self.key

        from kalapy.db.engines import database

        objects = self._get_related() + [self] # first save all related records
        database.update_records(*objects)

        return self.key

    def delete(self):
        """Deletes the instance from the database.

        :raises:
            - :class:`TypeError`: if instance is not saved
            - :class:`DatabaseError`: if instance could not be deleted.
        """
        if not self.is_saved:
            raise TypeError(_("Can't delete, instance doesn't exists."))
        from kalapy.db.engines import database
        database.delete_records(self)
        self._key = None

    @classmethod
    def get(cls, keys):
        """Fetch the instance(s) from the database using the provided keys.

        If `keys` is a single value it will return an instance else if `keys`
        is a list of `key` then returns list of instances.

        >>> user = User.get(123)
        >>> isinstance(user, User)
        True
        >>> users = User.get([123, 456, 789])
        >>> isinstance(users, list):
        True

        :param keys: an key or list of keys

        :returns:
            If `keys` is single value it will return and instance of the model
            else returns list of instances.

        :raises: :class:`DatabaseError` if instances can't be retrieved.
        """
        single = False
        if not isinstance(keys, (list, tuple)):
            keys = [keys]
            single = True
        result = cls.all().filter('key in', keys).fetch(-1)

        if single:
            return result[0] if result else None
        return result

    @classmethod
    def all(cls):
        """Returns a :class:`Query` object over all instances of this model from
        the database.

        :returns: an :class:`Query` instance
        """
        return Query(cls)

    @classmethod
    def select(cls, *fields):
        """Mimics `SELECT` column query. If fields are not given it is equivalent
        to :meth:`all()`.

        >>> names = User.select('name').fetch(-1)
        >>> print names
        ['a', 'b', 'c', ...]
        >>> name_dob = User.select('name', 'dob').fetch(-1)
        >>> print name_dob
        [('a', '01-11-2001'), ...]
        >>> users = User.select().fetch(-1)
        >>> print users
        [<Object ...> ...]

        :arg fields: sequence of fields

        :returns: an :class:`Query` instance
        """
        def mapper(obj):
            if not fields:
                return obj
            if len(fields) > 1:
                return tuple([getattr(obj, name) for name in fields])
            return getattr(obj, fields[0])

        return Query(cls, mapper)

    @classmethod
    def fields(cls):
        """Return the defined fields.
        """
        return OrderedDict(cls._meta.fields)

    def __repr__(self):
        return "<Model %r: %s object at %s>" % (self._meta.name,
                                          self.__class__.__name__, hex(id(self)))
