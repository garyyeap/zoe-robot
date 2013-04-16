"""
kalapy.utils.signals
~~~~~~~~~~~~~~~~~~~~

This module implements simple signal/event dispatching.

The signal dispatcher helps to implemented decoupled application packages
which get notified when action occurs elsewhere, in the framework or in
the application packages. Signals allow certain senders to notify a set of
receivers that some action has taken place.

A signal listener can be registered using :func:`connect` decorator. The signal
can be fired with :func:`send` method.

For example::

    from kalapy.core import signals

    @signals.connect('onfinish')
    def on_finish_1(state):
         ...
         ...

    @signals.connect('onfinish')
    def on_finish_2(state):
         ...
         ...

The signal can be fired like this::

    signals.send('onfinish', state=1)

In this case both the handlers connected to the 'onfinish' signal will
be fired.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LICENSE for more details.
"""
import types, weakref


__all__ = ('Signal', 'connect', 'disconnect', 'send')


class SignalType(type):
    """Meta class to ensure singleton instances of :class:`Signal` for the
    given signal name.
    """
    instances = {}

    def __call__(cls, name):
        if name in cls.instances:
            return cls.instances[name]
        return cls.instances.setdefault(name,
            super(SignalType, cls).__call__(name))


class Signal(object):
    """Signal class caches all the registered handlers in `WeakValueDictionary`
    so that handlers can be automatically garbage collected if the reference
    to the handler is the only reference.

    :param name: name for the signal
    """

    __metaclass__ = SignalType

    def __init__(self, name):
        """Create a new Signal instance with the given name.
        """
        self.name = name
        self.registry = weakref.WeakValueDictionary()

    def connect(self, handler):
        """Connect the given handler to the signal. The handler must be a
        function.

        :param handler: a signal handler

        :return: returns the handler itself
        :raises:
            `TypeError`: if handler is not a function
        """
        if not isinstance(handler, types.FunctionType):
            raise TypeError(_('Signal handler must be a function'))
        self.registry.setdefault(id(handler), handler)
        return handler

    def disconnect(self, handler=None):
        """Manually disconnect the given handler if it is registered with
        this signal.

        By default, the handler will be removed automatically from the signal
        registry if it is the only reference remained.

        :param handler: the handler function
        """
        if handler is None:
            self.registry.clear()
        else:
            self.registry.pop(id(handler), None)

    def send(self, *args, **kw):
        """Fire the signal.

        All handlers registered with this signal instance will be called passing
        the given positional and keyword arguments.

        :param args: to be passed to signal handlers
        :param kw: to be passed to signal handlers

        :returns: list of results returned by all the handlers
        """
        result = []
        for handler in self.registry.values():
            result.append(handler(*args, **kw))
        return result

    def __call__(self, *args, **kw):
        return self.send(*args, **kw)


def connect(signal):
    """A decorator to connect a function to the specified signal.

    Example::

        @signals.connect('onfinish')
        def on_finish_1(state):
             pass

    :param signal: name of the signal
    """
    def wrapper(func):
        return Signal(signal).connect(func)
    return wrapper


def disconnect(signal, handler=None):
    """If handler is given then disconnect the handler from the specified
    signal else disconnect all the handlers of the given signal.

    >>> signals.disconnect('onfinish', on_finish_1)
    >>> signals.disconnect('onfinish')

    :param signal: name of the signal
    :param handler: a signal handler
    """
    if signal in Signal.instances:
        Signal(signal).disconnect(handler)


def send(signal, *args, **kw):
    """Fire the specified signal.

    The signal handlers will be called with the given positional and keyword
    arguments.

    >>> signals.send('onfinish', state=1)

    :param args: to be passed to the signal handlers
    :param kw: to be passed to the signal handlers

    :returns: list of the results of all the signal handlers
    """
    if signal in Signal.instances:
        return Signal(signal).send(*args, **kw)
    return []


if __name__ == "__main__":

    @connect('onfoo')
    def foo1(data):
        print "Foo1 %s!" % data

    @connect('onfoo')
    def foo2(data):
        print "Foo2 %s!" % data

    send('onfoo', data=2)
