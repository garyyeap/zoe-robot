"""
kalapy.contrib.sessions.flash
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module implements flashing message support via sessions. A message
cab be flashed using `request.flash` function and the flashed messages
can then be accessed using `request.flashes` function. A tipical use case
is to flash a message that a records is saved or deleted.

For example::

    @web.route('/blog', methods=('POST',))
    def save():
        ...
        ...
        request.flash('Blog entry saved.')
        return redirect(url_for('show'))

The flashed messages then can be used during next request, like:

.. sourcecode:: html+jinja

    {% for category, message in request.flashes() %}
        <div class="flash-{{ category }}">{{ message }}</div>
    {% endfor %}

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LINCESE for more details.
"""
from kalapy.web import request


def flash(message, category='message'):
    """Flashes a message to the next request. The flashed messages will
    be stored in session and will be removed from session when consumed
    by accessing `request.flashes`, though the flashes will be available
    throught the request.

    :param message: message to be flashed
    :param category: message category, like `message`, `error`, `info`.
    """
    request.session.setdefault('_flashes', []).append((category, message))


def flashes():
    """Access all the flashed messages and remove them from the session.
    The messages will be available throught the request though.

    Example:

    .. sourcecode:: html+jinja

        {% for category, message in request.flashes() %}
            <div class="flash-{{ category }}">{{ message }}</div>
        {% endfor %}

    """
    flashes = getattr(request, '_flashes', None)
    if flashes is None:
        request._flashes = flashes = request.session.pop('_flashes', [])
    return flashes

