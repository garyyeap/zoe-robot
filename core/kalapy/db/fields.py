"""
kalapy.db.fields
~~~~~~~~~~~~~~~~

This module implements field classes which can be used to define properties
of a data model.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LICENSE for more details.
"""
import decimal, datetime


__all__ = ('FieldError', 'ValidationError', 'Field', 'String', 'Text', 'Integer',
           'Float', 'Decimal', 'Boolean', 'DateTime', 'Date', 'Time', 'Binary')


class FieldError(AttributeError):
    """Base exception class for all field related errors.
    """
    pass


class ValidationError(ValueError):
    """The exception class to be raised if validation of field value fails.
    """
    pass


class Field(object):
    """A Field is an attribute of a :class:`Model`.

    It defines the type of an attribute, which determines how the value could be
    stored in the database. It provides options for validation, default value, type
    conversion etc. Different :class:`Field` type has different options.

    A simplest example::

        class User(db.Model):
            name = db.String(size=100, required=True)

    :param label: field label, a verbose name
    :param name: field name, if not given uses the attribute name
    :param default: default value, can also be a callable
    :param required: whether the field value is required
    :param unique: whether the field value should be unique
    :param indexed: whether this field should be indexed
    :param selection:
        - a list of (value, string) tuple to restrict the input value to be
          one of the key.
        - a callable that returns a list of (value, string) tuple
    :param validator: a validator function to validate the field values
    """

    # for internal use only
    _serial = 0

    _data_type = "char"

    def __init__(self, label=None, name=None, default=None, required=False,
        unique=False, indexed=False, selection=None, validator=None):
        """Create a new instance of this :class:`Field`.
        """

        self._serial = Field._serial = Field._serial + 1

        self._label = label
        self._name = name
        self._default = default

        self._required = required
        self._unique = unique
        self._indexed = indexed

        self._selection = selection() if callable(selection) else selection
        self._selection_list = [x[0] for x in self._selection] if self._selection else []

        self._validator = validator

    def __repr__(self):
        return "<Field %s name='%s'>" % (self.__class__.__name__, self.name)

    def __configure__(self, model_class, name):
        self._name = name
        self.model_class = model_class

        if self._label is None:
            self._label = name.title()

    def __get__(self, model_instance, model_class):
        if model_instance is None:
            return self
        return model_instance._values.get(self.name)

    def __set__(self, model_instance, value):
        value = self._validate(model_instance, value)
        model_instance._values[self.name] = value
        model_instance._dirty[self.name] = True

    def python_to_database(self, value):
        """Database representation of this field value.

        :param value: the value to be converted to database supported type

        :returns: converted value
        """
        return value

    def database_to_python(self, value):
        """Convert the given value to python representation for this field.

        :param value: the value to be converted to python type

        :returns: converted value
        """
        return value

    def _validate(self, model_instance, value):
        """Validate the given value. For internal use only, subclasses should
        override `validate` method instead.

        :param model_instance: an instance of the model to which the field is associated
        :param value: the value to be validated

        :returns: validated value
        :raises: :class:`ValidationError`, :class:`ValueError`
        """
        if self.empty(value) and self.is_required:
            raise ValidationError("Field '%s' is required.", self.name)

        if self._selection and value not in self._selection_list:
            raise ValidationError(
                _("Field '%(name)s' is '%(value)s'; must be one of %(selection)s",
                    name=self.name, value=value, selection=self._selection_list))

        if self._validator:
            self._validator(model_instance, value)

        if value is None:
            return value

        return self.validate(value)

    def validate(self, value):
        """Check whether the given value is compatible with this field.

        Subclasses should override this method to convert provided value
        in compatible form and should raise :class:`ValidationError` if the
        value is not compatible and can't be converted to proper value.

        :param value: the value to be validated

        :returns: validated value
        :raises: :class:`ValidationError`, :class:`ValueError`
        """
        return value

    def empty(self, value):
        """Determine if value is empty in the context of this field.

        In most cases, this is equivalent to "not value" but some fields
        like :class:`Boolean` the test is more subtle, so subclasses should
        override this method if necessary.

        :param value: the value to check

        :returns: True if value is empty in the context of this Field else False
        """
        return not value

    @property
    def data_type(self):
        """Data type of this field. Used by backend database engines to determine
        proper data type for the field to be used to store the value in database.
        """
        return self._data_type

    @property
    def name(self):
        """Name of the field.
        """
        return self._name

    @property
    def label(self):
        """The label of the field, a verbose name, can be used to represent the
        field in views.
        """
        return self._label

    @property
    def default(self):
        """Default value for the field.
        """
        return self.default_value()

    def default_value(self):
        """Get the default value for the field.
        """
        if callable(self._default):
            return self._default()
        return self._default

    @property
    def is_required(self):
        """Whether this field is marked required field or not.
        """
        return self._required

    @property
    def is_unique(self):
        """Whether this field is marked unique field or not.
        """
        return self._unique

    @property
    def is_indexed(self):
        """Whether this field is indexed or not.
        """
        return self._indexed


class AutoKey(Field):
    """AutoKey field is used to define primary key of Model classes.
    """
    _data_type = 'key'

    def __init__(self):
        super(AutoKey, self).__init__(name="key", required=True)
        # negative serial id so that it become first field in the model
        self._serial = - self._serial

    def __get__(self, model_instance, model_class):
        if model_instance is None:
            return self
        return model_instance._key

    def __set__(self, model_instance, value):
        raise AttributeError(
            _('%(name)r is a read-only primary key field.', name=self.name))


def _validate_string(name, value, size=None):
    if not isinstance(value, basestring):
        raise ValidationError(
            _('Field %(name)r must be a str or unicode instance, not %(type)r',
                name=name, type=type(value).__name__))
    if size is not None and len(value) > size:
        raise ValidationError(
            _('Field %(name)s is %(length)d bytes long; it must be %(size)d or less.',
                name=name, length=len(value), size=size))
    return value


class String(Field):
    """String field stores textual data, especially short string values like
    name, title etc.

    For example::

        class Article(db.Model):
            title = db.String(size=100)

    :param label: field's label (verbose name)
    :param size: maximux string size
    :keyword kw: other :class:`Field` params
    """
    _data_type = "char"

    def __init__(self, label=None, size=None, **kw):
        super(String, self).__init__(label=label, **kw)
        self._size = size or 250

    @property
    def size(self):
        return self._size

    def validate(self, value):
        _validate_string(self.name, value, self.size)
        return value


class Text(Field):
    """Text field can hold longer textual data.

    For example::

        class Article(db.Model):
            title = db.String(size=100)
            content = db.Text()

    """

    _data_type = "text"

    def validate(self, value):
        _validate_string(self.name, value)
        return value


class Integer(Field):
    """Integer field stores integer value.
    """
    _data_type = "integer"

    def validate(self, value):
        if isinstance(value, basestring):
            try:
                return int(value)
            except:
                raise ValidationError('Invalid value: %r' % value)
        if not isinstance(value, (int, long)) or isinstance(value, bool):
            raise ValidationError(
                _('Field %(name)r must be an int or long, not a %(type)r',
                    name=self.name, type=type(value).__name__))
        return value

    def empty(self, value):
        """Is integer property empty?

        0 is not an empty value.

        :returns: True if value is None, else False
        """
        return value is None


class Float(Field):
    """Float field stores float value.
    """
    _data_type = "float"

    def validate(self, value):
        if isinstance(value, basestring):
            try:
                return float(value)
            except:
                raise ValidationError(
                    _('Invalid value: %(value)s', value=value))
        if not isinstance(value, float):
            raise ValidationError(
                _('Field %(name)r must be a float, not a %(type)r',
                    name=self.name, type=type(value).__name__))
        return value

    def empty(self, value):
        """Is Float property empty?

        0.0 is not an empty value.

        :returns: True if value is None, else False
        """
        return value is None


class Decimal(Float):
    """Decimal field stores decimal value, useful for monatory calulations.

    The precision and scale can be specified by `max_digits` and `decimal_places`
    respectively. For example::

        salary = db.Decimal(max_digits=10, decimal_places=2)

    """
    _data_type = "decimal"

    def __init__(self, label=None, max_digits=None, decimal_places=None, **kw):
        super(Decimal, self).__init__(label=label, **kw)
        self.max_digits = max_digits or 65
        self.decimal_places = decimal_places or 30

    def validate(self, value):
        if isinstance(value, basestring):
            try:
                return decimal.Decimal(value)
            except:
                raise ValidationError(
                    _('Invalid decimal value: %(value)s', value=value))
        if not isinstance(value, decimal.Decimal):
            raise ValidationError(
                _('Field %(name)s must be a decimal.Decimal value, not a %(type)r',
                    name=self.name, type=type(value).__name__))
        return value

    def empty(self, value):
        """Is Decimal property empty?

        Decimal('0.0') is not an empty value.

        :returns: True if value is None, else False
        """
        return value is None

    def python_to_database(self, value):
        return str(value) if value else value

    def database_to_python(self, value):
        return decimal.Decimal(value) if value else value


class Boolean(Field):
    """Boolean field stores either True or False value.
    """
    _data_type = "boolean"

    def validate(self, value):
        if isinstance(value, int):
            return bool(value)
        if value in (True, False): return value
        if value in ('t', 'True', 'y', 'Yes', '1'): return True
        if value in ('f', 'False', 'n', 'No', '0'): return False
        raise ValidationError(
            _('Expected either %(true)s or %(false)s',
                true='True', false='False'))

    def empty(self, value):
        """Is Boolean property empty?

        False is not an empty value.

        :returns: True if value is None, else False
        """
        return value is None


class DateTime(Field):
    """DateTime defines a :class:`Model` property of type `datetime`.

    For example::

        class Article(db.Model):
            pub_date = db.DateTime(default_now=True)

    >>> a = Article()
    >>> print a.pub_date
    2010-05-16 23:52:21.539322
    >>> print type(a.pub_date)
    <type 'datetime.datetime'>
    >>> a.pub_date = '2010-05-16 12:00:00'
    >>> print a.pub_date
    2010-05-16 12:00:00
    >>> print type(a.pub_date)
    <type 'datetime.datetime'>

    You can see that the input value in string is converted to python `datetime.datetime`
    object.

    :param label: verbose label
    :param auto_now:
        If True the value will be updated with current time every time it is saved
        to database. Useful to create a property to track object update time.
    :param default_now: If True, use current time as default value
    """

    _data_type = "datetime"

    def __init__(self, label=None, auto_now=False, default_now=False, **kw):
        """Create a new instance of DateTime.
        """
        super(DateTime, self).__init__(label=label, **kw)
        self.auto_now = auto_now
        self.default_now = default_now

    def validate(self, value):
        value = _parse_datetime(value, datetime.datetime)
        if not isinstance(value, datetime.datetime):
            raise ValidationError(
                _('Field %(name)r must be a datetime', name=self.name))
        return value

    def default_value(self):
        if self.auto_now or self.default_now:
            return self.now()
        return super(DateTime, self).default_value()

    def python_to_database(self, value):
        if self.auto_now:
            return self.now()
        return super(DateTime, self).python_to_database(value)

    @staticmethod
    def now():
        """Returns current (now) datetime.
        """
        return datetime.datetime.now()

    def empty(self, value):
        """Is Time property empty?

        "0:0" (midnight) time is not empty

        :returns: True if value is None
        """
        return value is None


def _date_to_datetime(value):
    """Convert a date to a datetime for datastore storage.

    :param value: A datetime.date object.
    :returns: A datetime object with time set to 0:00.
    """
    assert isinstance(value, datetime.date)
    return datetime.datetime(value.year, value.month, value.day)


def _time_to_datetime(value):
    """Convert a time to a datetime for datastore storage.

    :param value: A datetime.time object.
    :returns: A datetime object with date set to 1970-01-01.
    """
    assert isinstance(value, datetime.time)
    return datetime.datetime(1970, 1, 1,
                             value.hour, value.minute, value.second,
                             value.microsecond)


def _parse_datetime(value, type=datetime.datetime):
    """Convert a string value in to given type, type can be one of
    datetime.datetime, datetime.date and datetime.time.

    Uses current locale and timezone settings to convert the value.

    :param value: string value
    :param type: one of datetime, date or time

    :returns: an instance of provided type
    :raises: :class:`ValidationError`
    """
    assert type in (datetime.datetime, datetime.date, datetime.time)
    if not isinstance(value, basestring):
        return value
    #TODO: use current locale and timezone info to parse to value
    formats = {
        datetime.datetime: '%Y-%m-%d %H:%M:%S',
        datetime.date: '%Y-%m-%d',
        datetime.time: '%H:%M:%S'
    }
    format = formats[type]
    try:
        value = datetime.datetime.strptime(value, format)
    except ValueError, e:
        raise ValidationError(e)
    try:
        return getattr(value, type.__name__)()
    except:
        return value


class Date(DateTime):
    """Date field stores a date without time.
    """

    def validate(self, value):
        value = _parse_datetime(value, datetime.date)
        if not isinstance(value, datetime.date):
            raise ValidationError(
                _('Field %(name)r must be a date', name=self.name))
        return value

    def python_to_database(self, value):
        value = super(Date, self).python_to_database(value)
        if value is not None:
            assert isinstance(value, datetime.date)
            value = _date_to_datetime(value)
        return value

    def database_to_python(self, value):
        if value is not None:
            assert isinstance(value, datetime.datetime)
            value = value.date()
        return value

    @staticmethod
    def now():
        return datetime.datetime.now().date()


class Time(DateTime):
    """Time field stores a time without date.
    """

    def validate(self, value):
        value = _parse_datetime(value, datetime.time)
        if not isinstance(value, datetime.time):
            raise ValidationError(
                _('Field %(name)r must be a time', name=self.name))
        return value

    def python_to_database(self, value):
        value = super(Time, self).python_to_database(value)
        if value is not None:
            assert isinstance(value, datetime.time), repr(value)
            value = _time_to_datetime(value)
        return value

    def database_to_python(self, value):
        if value is not None:
            assert isinstance(value, datetime.datetime)
            value = value.time()
        return value

    @staticmethod
    def now():
        return datetime.datetime.now().time()


class Binary(Field):
    """Binary field stores BLOB (binary large objects) like files, images etc.
    """
    _data_type = "blob"

