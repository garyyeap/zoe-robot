"""
kalapy.db.reference
~~~~~~~~~~~~~~~~~~~

This module implements field classes to define relationship like many-to-one,
one-to-one, many-to-one and many-to-many between models.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LICENSE for more details.
"""
from kalapy.core.pool import pool
from kalapy.db.fields import Field, FieldError
from kalapy.db.model import ModelType, Model


__all__ = ('ManyToOne', 'OneToOne', 'OneToMany', 'ManyToMany')


class IRelation(Field):
    """This class defines an interface method prepare which will called
    once all defined models are loaded. So the field would have chance
    to resolve early lookup references.
    """

    def __init__(self, reference, **kw):
        super(IRelation, self).__init__(**kw)
        self._reference = reference

    def __configure__(self, model_class, name):
        super(IRelation, self).__configure__(model_class, name)

        ref = self._reference
        if isinstance(ref, basestring) and ':' not in ref:
            self._reference = ref = '%s:%s' % (model_class._meta.package, ref)
        try:
            ref = pool.get_model(ref)
        except:
            pool.model_pending.setdefault(ref, []).append(self)
        else:
            self.prepare(model_class)

    def prepare(self, model_class):
        """The relation field should implement this method to implement
        support code as at this point all the models will be resolved.

        :param model_class: a subclass of :class:`Model`
        """
        pass

    @property
    def reference(self):
        """Returns the reference class.
        """
        return pool.get_model(self._reference)

    @property
    def is_virtual(self):
        """Whether this field virtual, a virtual field value is not stored in
        database but is a result of some relationship.

        For example, :class:`OneToMany` is a virtual field linked with a
        corresponding :class:`ManyToOne` in other model class.
        """
        return self._data_type is None


class ManyToOne(IRelation):
    """ManyToOne field represents many-to-one relationship with other :class:`Model`.

    For example, a `ManyToOne` field defined in model `A` that refers to model `B`
    forms a many-to-one relationship from `A` to `B`. Every instance of `B` refers
    to a single instance of `A` and every instance of `A` can have many instances
    of `B` that refer it.

    A reverse lookup field will be automatically created in the reference model.
    In this case, a field `a_set` of type :class:`OneToMany` will be automatically
    created on class `B` referencing class `A`.

    For example::

        class User(db.Model):
            name = db.String(size=100)

        class Address(db.Model):
            name = db.String(size=100)
            ...
            user = db.ManyToOne(User)

    A reverse lookup field of type :class:`OneToMany` named `address_set` will be
    automatically created in class `User`.

    :param reference: reference model class
    :param reverse_name: name of the reverse lookup field in the referenced model
    :param cascade: None = set null, False = restrict and True = cascade
    :param kw: other field params
    """

    _data_type = 'reference'

    def __init__(self, reference, reverse_name=None, cascade=False, **kw):
        """Create a new ManyToOne field referencing the given `reference` model.
        """
        super(ManyToOne, self).__init__(reference, **kw)
        self.reverse_name = reverse_name
        self.cascade = cascade

    def prepare(self, model_class, reverse_name=None, reverse_class=None):

        # check for recursive dependency and update dependency info
        ref_models = model_class._meta.ref_models
        if self.reference not in ref_models:
            if model_class in self.reference._meta.ref_models:
                raise FieldError(
                    _('Recursive dependency, field %(name)r in %(model)r',
                        name=self.name, model=model_class.__name__))
        ref_models.append(self.reference)

        if not self.reverse_name:
            self.reverse_name = reverse_name or ('%s_set' % model_class.__name__.lower())

        if hasattr(self.reference, self.reverse_name):
            try:
                if getattr(self.reference, self.reverse_name).reverse_name == self.name:
                    return
            except:
                pass
            raise FieldError(
                _('Field %(name)r already defined in referenced model %(model)r',
                    name=self.reverse_name, model=self.reference.__name__))

        c = reverse_class or OneToMany
        f = c(model_class, name=self.reverse_name, reverse_name=self.name)
        self.reference.add_field(f)

    def __get__(self, model_instance, model_class):
        return super(ManyToOne, self).__get__(model_instance, model_class)

    def __set__(self, model_instance, value):
        if value is not None and not isinstance(value, self.reference):
            raise ValueError(
                _('ManyToOne field %(name)r value should be an instance of %(model)r',
                    name=self.name, model=self._reference.__name__))
        super(ManyToOne, self).__set__(model_instance, value)

    def python_to_database(self, value):
        if isinstance(value, Model):
            return value.key
        return value

    def database_to_python(self, value):
        if value is None:
            return value
        if not isinstance(value, self.reference):
            return self.reference.get(value)
        return value


class OneToOne(ManyToOne):
    """OneToOne is basically ManyToOne with unique constraint.

    A reverse lookup field of type :class:`OneToOne` will be created in the
    referenced model.

    For example::

        class Car(db.Model):
            name = db.String(size=100)

        class Engine(db.Model):
            name = db.String(size=100)
            car = db.OneToOne(Car)

    The class `Car` will get an `OneToOne` field named `engine` referencing the
    `Engine` class and can be accessed like this::

        >>> car = Car(name='nano')
        >>> car.engine = Engine(name='micro')
        >>> car.save()
        >>> print car.engine.name
        ... 'micro'
        >>> print car.engine.car.name
        ... 'nano'
    """
    def __init__(self, reference, reverse_name=None, cascade=False, **kw):
        kw['unique'] = True
        super(OneToOne, self).__init__(reference, reverse_name, cascade, **kw)

    def __set__(self, model_instance, value):
        super(OneToOne, self).__set__(model_instance, value)
        setattr(value, self.reverse_name, model_instance)

    def prepare(self, model_class):
        super(OneToOne, self).prepare(model_class,
                reverse_name=model_class.__name__.lower(),
                reverse_class=O2ORel)

class O2ORel(IRelation):
    """OneToOne reverse lookup field to prevent recursive dependencies.
    """

    _data_type = None

    def __init__(self, reference, reverse_name, **kw):
        super(O2ORel, self).__init__(reference, **kw)
        self.reverse_name = reverse_name

    def __get__(self, model_instance, model_class):

        if model_instance is None:
            return self

        try: # if already fetched
            return model_instance._values[self.name]
        except:
            pass

        if model_instance.is_saved:
            value = self.reference.all().filter(
                '%s ==' % self.reverse_name, model_instance.key).fetch(1)[0]
            model_instance._values[self.name] = value
            return value

        return None

    def __set__(self, model_instance, value):

        if model_instance is None:
            raise AttributeError('%r must be accessed with model instance' % (self.name))

        if not isinstance(value, self.reference):
            raise TypeError(
                _('Expected %(model)r instance', model=self.reference._meta.name))

        super(O2ORel, self).__set__(model_instance, value)

        # this is virtual field, so mark it clean
        del model_instance._dirty[self.name]

        if getattr(value, self.reverse_name, None) != model_instance:
            setattr(value, self.reverse_name, model_instance)
            if not model_instance.is_saved:
                model_instance.save()
            value.save()

    def prepare(self, model_class):
        pass


class O2MSet(object):
    """A descriptor class to access OneToMany fields.
    """

    def __init__(self, field, instance):
        self.__field = field
        self.__obj = instance
        self.__ref = field.reference
        self.__ref_field = getattr(field.reference, field.reverse_name)

    def __check(self, *objs):
        for obj in objs:
            if not isinstance(obj, self.__ref):
                raise TypeError(
                    _('%(model)r instances required', model=self.__ref._meta.name))
        if not self.__obj.is_saved:
            self.__obj.save()
        return objs

    def all(self):
        """Returns a :class:`Query` object pre-filtered to return related objects.
        """
        self.__check()
        return self.__ref.all().filter('%s ==' % (self.__field.reverse_name),
                self.__obj.key)

    def add(self, *objs):
        """Add new instances to the reference set.

        :raises:
            TypeError: if any given object is not an instance of referenced model
        """
        for obj in self.__check(*objs):
            setattr(obj, self.__field.reverse_name, self.__obj)
            obj.save()

    def remove(self, *objs):
        """Removes the provided instances from the reference set.

        :raises:
            - `FieldError`: if referenced instance field is required field.
            - `TypeError`: if any given object is not an instance of referenced model
        """
        if self.__ref_field.is_required:
            raise FieldError(
                _("objects can't be removed from %(name)r, delete the objects instead.",
                    name=self.__field.name))

        self.__check(*objs)

        from kalapy.db.engines import database
        database.delete_records(*objs)

    def clear(self):
        """Removes all referenced instances from the reference set.

        :raises:
            - `FieldError`: if referenced instance field is required field.
            - `TypeError`: if any given object is not an instance of referenced model
        """
        if not self.__obj.is_saved:
            return

        if self.__ref_field.is_required:
            raise FieldError(
                _("objects can't be removed from %(name)r, delete the objects instead.",
                    name=self.__field.name))

        from kalapy.db.engines import database

        # instead of removing records at once remove them in bunches
        l = 100
        q = self.all()
        result = q.fetch(l)
        while result:
            database.delete_records(*result)
            result = q.fetch(l)


class M2MSet(object):
    """A descriptor class to access ManyToMany field.
    """

    def __init__(self, field, instance):
        self.__field = field
        self.__obj = instance
        self.__ref = field.reference
        self.__m2m = field.m2m

        self.__source_in = '%s in' % field.source
        self.__target_in = '%s in' % field.target
        self.__source_eq = '%s ==' % field.source

    def __check(self, *objs):
        for obj in objs:
            if not isinstance(obj, self.__ref):
                raise TypeError(
                    _('%(model)r instances required', model=self.__ref._meta.name))
        if not self.__obj.is_saved:
            self.__obj.save()
        return objs

    def all(self):
        """Returns a :class:`Query` object pre-filtered to return related objects.
        """
        self.__check()
        #XXX: think about a better solution
        # Use nested SELECT or JOIN, but some backends might not support that
        keys = self.__m2m.select(self.__field.target) \
                         .filter(self.__source_eq, self.__obj.key) \
                         .fetch(-1)
        keys = [o.key for o in keys]
        return self.__ref.all().filter('key in', keys)

    def add(self, *objs):
        """Add new instances to the reference set.

        :raises:
            - `TypeError`: if any given object is not an instance of referenced model
            - `ValueError`: if any of the given object is not saved
        """
        keys = [obj.key for obj in self.__check(*objs) if obj.key]

        if keys:
            existing = self.__m2m.select(self.__field.target) \
                                 .filter(self.__source_eq, self.__obj.key) \
                                 .fetch(-1)
            existing = [o.key for o in existing]
            objs = [o for o in objs if o.key not in existing]

        for obj in objs:
            if not obj.is_saved:
                obj.save()
            m2m = self.__m2m()
            setattr(m2m, self.__field.source, self.__obj)
            setattr(m2m, self.__field.target, obj)
            m2m.save()

    def remove(self, *objs):
        """Removes the provided instances from the reference set.

        :raises:
            - `TypeError`: if any given object is not an instance of referenced model
        """
        self.__check(*objs)

        from kalapy.db.engines import database
        database.delete_records(*objs)

    def clear(self):
        """Removes all referenced instances from the reference set.
        """
        if not self.__obj.is_saved:
            return

        from kalapy.db.engines import database

        # instead of removing records at once remove them in bunches
        l = 100
        q = self.all()
        result = q.fetch(l)
        while result:
            database.delete_records(*result)
            result = q.fetch(l)


class OneToMany(IRelation):
    """OneToMany field represents one-to-many relationship with other model.

    For example, a `OneToMany` field defined in model `A` that refers to model `B`
    forms a one-to-many relationship from `A` to `B`. Every instance of `B` refers
    to a single instance of `A` and every instance of `A` can have many instances
    of `B` that refer it.

    A reverse lookup field will be automatically created in the reference model.
    In this case, a field `a` of type `ManyToOne` will be automatically created
    on class B referencing class `A`.

    For example::

        class User(db.Model):
            name = db.String(size=100)
            ...
            contacts = db.OneToMany('Address')

        class Address(db.Model):
            name = db.String(size=100)
            ...

    A reverse lookup field of type :class:`ManyToOne` named `user` will be
    automatically created in class `Address`.

    :param reference: reference model class
    :param reverse_name: name of the reverse lookup field in the referenced model
    :param kw: other field params
    """

    _data_type = None

    def __init__(self, reference, reverse_name=None, **kw):
        super(OneToMany, self).__init__(reference, **kw)
        self.reverse_name = reverse_name

    def prepare(self, model_class):

        if not self.reverse_name:
            self.reverse_name = model_class.__name__.lower()

        if hasattr(self.reference, self.reverse_name):
            try:
                if getattr(self.reference, self.reverse_name).reverse_name == self.name:
                    return
            except:
                pass
            raise FieldError(
                _('Field %(name)r already defined in referenced model %(model)r',
                    name=self.reverse_name, model=self.reference.__name__))

        f = ManyToOne(model_class, self.name, name=self.reverse_name)
        self.reference.add_field(f)

    def __get__(self, model_instance, model_class):
        if model_instance is None:
            return self
        return O2MSet(self, model_instance)

    def __set__(self, model_instance, value):
        raise ValueError(
            _('Field %(name)r is readonly.', name=self.name))


class ManyToMany(IRelation):
    """ManyToMany field represents many-to-many relationship with other model.

    For example, a `ManyToMany` field defined in model `A` that refers to model
    `B` forms a many-to-many relationship from `A` to `B`. Every instance of `A`
    can have many instances of `B` referenced by an intermediary model that also
    refers model `A`.

    Removing an instance of `B` from `M2MSet` will delete instances of the
    intermediary model and thus breaking the many-to-many relationship.

    For example::

        class User(db.Model):
            name = db.String(size=100)
            ...
            groups = db.ManyToMany('Group')

        class Group(db.Model):
            name = db.String(size=100)
            ...

    A reverse lookup field of type :class:`ManyToMany` named `users` will be
    automatically created in class `Group`.

    :param reference: reference model class
    :param reverse_name: name of the reverse lookup field in the referenced model
    :param cascade: True or False, if True all the related entries from the
                    intermediate table will be dropped.
    :param kw: other field params

    """

    _data_type = None

    def __init__(self, reference, reverse_name=None, cascade=False, **kw):
        assert cascade in (True, False), 'cascade should be True or False'
        super(ManyToMany, self).__init__(reference, **kw)
        self.reverse_name = reverse_name
        self.cascade = cascade

    def get_reverse_field(self):

        if self.reverse_name is None:
            self.reverse_name = '%s_set' % (self.model_class.__name__.lower())

        if not self.reverse_name:
            return None

        reverse_field = getattr(self.reference, self.reverse_name, None)

        if reverse_field and reverse_field.reverse_name != self.name:
            raise FieldError(
                _('Field %(name)r already defined in referenced model %(model)r',
                    name=self.reverse_name, model=self.reference.__name__))

        return reverse_field

    def prepare(self, model_class):

        reverse_field = self.get_reverse_field()

        if not reverse_field: #create intermediary model

            self.source = '%s' % model_class._meta.name.split(':')[-1]
            self.target = '%s' % self.reference._meta.name.split(':')[-1]

            name = '%s_%s' % (self.source, self.name)

            cls = ModelType(name, (Model,), {
                '__module__': model_class.__module__
            })

            kw = dict(required=True, indexed=True, cascade=self.cascade)
            cls.add_field(ManyToOne(model_class, name=self.source, **kw))
            cls.add_field(ManyToOne(self.reference, name=self.target, **kw))

            cls._meta.ref_models.extend([model_class, self.reference])

            self.m2m = cls
        else:
            self.m2m = reverse_field.m2m
            self.source = reverse_field.target
            self.target = reverse_field.source

        if not reverse_field and self.reverse_name:
            # create reverse lookup field
            f = ManyToMany(model_class, reverse_name=self.name, name=self.reverse_name)
            self.reference.add_field(f)
            f.prepare(self.reference)

    def __get__(self, model_instance, model_class):

        if model_instance is None:
            return self

        return M2MSet(self, model_instance)

    def __set__(self, model_instance, value):
        raise ValueError(
            _('Field %(name)r is readonly.', name=self.name))
