"""
kalapy.utils.containers
~~~~~~~~~~~~~~~~~~~~~~~

This module implements few container datastructures like :class:`OrderedDict`.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LICENSE for more details.
"""
class OrderedDict(dict):
    """A :class:`dict` class that keeps its keys in the order in which
    they're inserted.
    """

    def __init__(self, *args, **kw):
        dict.__init__(self, *args, **kw)
        self._keys = []

        for arg in args:
            self.update(arg)

        for k in kw.keys():
            if k not in self._keys:
                self._keys.append(k)

    def __setitem__(self, key, value):
        super(OrderedDict, self).__setitem__(key, value)
        if key not in self._keys:
            self._keys.append(key)

    def __delitem__(self, key):
        super(OrderedDict, self).__delitem__(key)
        self._keys.remove(key)

    def update(self, data):
        if not isinstance(data, (list, tuple, set, OrderedDict)):
            raise ValueError("Only accepts ordered list of items or OrderedDict")

        items = data.items() if isinstance(data, OrderedDict) else data
        for k, v in items:
            self.__setitem__(k, v)

    def keys(self):
        return self._keys[:]

    def values(self):
        return [v for __k, v in self.items()]

    def items(self):
        return [(k, self[k]) for k in self._keys]

    def __iter__(self):
        for k in self._keys:
            yield k

    def iteritems(self):
        for k in self:
            yield self[k]

    def iterkeys(self):
        return iter(self._keys)

    def itervalues(self):
        for k in self:
            yield self[k]

    def pop(self, key, *args):
        value = super(OrderedDict, self).pop(key, *args)
        try:
            self._keys.remove(key)
        except:
            pass
        return value

    def popitem(self):
        item = super(OrderedDict, self).popitem()
        self._keys.remove(item[0])
        return item

    def setdefault(self, key, default):
        if key not in self._keys:
            self._keys.append(key)
        return super(OrderedDict, self).setdefault(key, default)

    def copy(self):
        obj = OrderedDict(self)
        obj._keys = self._keys[:]
        return obj

    def __deepcopy__(self, memo):
        from copy import deepcopy
        return OrderedDict([(k, deepcopy(v, memo)) for k, v in self.items()])

    def __repr__(self):
        return '{%s}' % ', '.join(['%r: %r' % (k, v) for k, v in self.items()])
