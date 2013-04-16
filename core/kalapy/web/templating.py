# -*- coding: utf-8 -*-
"""
kalapy.web.templating
~~~~~~~~~~~~~~~~~~~~~

Implements templating support using Jinja2.

This module provides :func:`render_template` function that can be used to
render jinja2 templates. It also provides special version of `gettext` and
`ngettext` implementation to allow `rst` style syntax to apply jinja2 macro
to the strings.

For example, we want to translate following template:

.. sourcecode:: html+jinja

    Click <a href="{{ url_for('some.endpoint') }}">here</a> for more information.

As the embedded url markup is dynamically generated, it is hard to translate the
entire sentence. Also, translating the sentence into pieces might result in
wrong translation in some languages. This can be solved like:

.. sourcecode:: html+jinja

    {% macro here_link(val) %}
        <a href="{{ url_for('some.endpoint') }}">{{ val }}</a>
    {% endmacro %}

    {{ _('Click :here_link:`here` for more information.', here_link=here_link)|safe }}

You can see, rst like construct has been embedded into the string. Now, the
translator can correctly translate the sentence without loosing the context.

The gettext function ``_()`` will then apply the macro to the translated string
resulting correct translation.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LICENSE for more details.
"""
import re

from jinja2 import Environment

from kalapy.i18n.utils import get_translations
from kalapy.web.local import _request_context


__all__ = ('render_template',)


class JinjaEnvironment(Environment):
    """Custom Jinja environment, makes sure that template is correctly resolved.
    """
    def join_path(self, template, parent):
        if ':' not in template:
            package = parent.split(':',1)[0]
            return '%s:%s' % (package, template)
        return template


__macro_re = re.compile(':(\w+):`(.*?)`')


def apply_macro(string, **kw):
    """Apply a macro to the given string provided through the keywork
    arguments.
    """
    def replace(match):
        func, val = match.groups()
        try:
            func = kw[func]
        except KeyError:
            return match.group(0)
        else:
            return func(val)
    return string if not kw else __macro_re.sub(replace, string) % kw


def gettext(string, **kw):
    """Same as :func:`kalapy.i18n.gettext` but will expand the translated
    string with macros. Useful to translate strings in Jinja2 template with
    embedded markup.
    """
    return apply_macro(get_translations().ugettext(string), **kw)


def ngettext(string, plural, num, **kw):
    """Same as :func:`kalapy.i18n.ngettext` but will expand the translated
    string with macros. Useful to translate strings in Jinja2 template with
    embedded markup.
    """
    return apply_macro(
        get_translations().ungettext(string, plural, num), **kw)


def render_template(template, **context):
    """Render the template of the current package with the given context.

    The template loader will try to load the template from the `templates`
    folder of the current package. If there are any addon packages activated
    for the current package, the loader will give prefences to the `templates`
    provided with the addon packages.

    :param template: the name of the template to be rendered.
    :param context: the variables that should be available in the context
                    of the template.

    :returns: string generated after rendering the template
    :raises: :class:`TemplateNotFound` or any other exceptions thrown during
             rendering process
    """
    ctx = _request_context
    template = '%s:%s' % (ctx.request.package, template)
    return ctx.current_app.jinja_env.get_template(template).render(context)

def render_template_string(template, **context):
    """Render the template string with the the given context.

    :param template: the jinj2 template as string.
    :param context: the variables that should be available in the context
                    of the template.

    :returns: string generated after rendering the template
    """
    return ctx.current_app.jinja_env.from_string(template).render(context)
