"""
kalapy.admin.commands.babel
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module implements `babel` command, which can be used to perform
various message catalogue related tasks.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LINCESE for more details.
"""
import os, sys

from babel.messages.frontend import CommandLineInterface, extract_messages
from babel.support import Translations

from kalapy.conf import settings
from kalapy.admin import ActionCommand


MAPPINGS = dict(
    messages = """
[extractors]
ignore = babel.messages.extract:extract_nothing
python = babel.messages.extract:extract_python
jinja2 = jinja2.ext.babel_extract

# Extraction from Python source files
[python: **.py]

# Extraction from Jinja2 HTML templates
[jinja2: **/templates/**.html]
extensions=jinja2.ext.autoescape,jinja2.ext.with_
""", javascript = """
[extractors]
ignore = babel.messages.extract:extract_nothing
javascript = babel.messages.extract:extract_javascript

# Extraction from JavaScript source files
[javascript: **/javascript/**.js]
""")

class BabelCommand(ActionCommand):
    """Perform i18n message catalog related actions.
    """

    name = 'babel'
    usage = '%name <action> [options] [package [package [...]]]'

    options = (
        ('l', 'locale', '', 'locale (e.g. en_US, fr_FR)'),
        ('d', 'domain', 'messages', 'message catalog domain'),
    )

    def get_packages(self, args):
        for pkg in args or os.listdir('.'):
            if pkg in settings.INSTALLED_PACKAGES:
                yield pkg

    def get_locales(self, pkg):
        for locale in os.listdir(os.path.join(pkg, 'locale')):
            if os.path.isdir(os.path.join(pkg, 'locale', locale, 'LC_MESSAGES')):
                yield locale

    def locale_info(self, options, args):
        for pkg in self.get_packages(args):
            yield pkg, os.path.join(pkg, 'locale'), \
                [options.locale] if options.locale else self.get_locales(pkg)

    def get_files(self, pkg, locale, domain):
        po = ""
        mo = ""
        pot = os.path.join(pkg, 'locale', '%s.pot' % domain)
        if locale:
            lc = os.path.join(pkg, 'locale', locale, 'LC_MESSAGES')
            po = os.path.join(lc, '%s.po' % domain)
            mo = os.path.join(lc, '%s.mo' % domain)
        return pot, po, mo

    def run_babel(self, command, *argv):
        cmd = CommandLineInterface()
        cmd.run(['', '-q', command] + list(argv))

    def action_init(self, options, args):
        """Create new message catalogs from generated POT file.
        """
        for pkg, path, locales in self.locale_info(options, args):
            if not os.path.exists(path):
                continue
            for locale in locales:
                pot, po, mo = self.get_files(pkg, locale, options.domain)
                if not os.path.exists(pot):
                    continue
                if options.verbose:
                    print 'creating catalog %r' % po
                self.run_babel('init', '-i', pot, '-d', path, '-l', locale)

    def action_extract(self, options, args):
        """Extract messages from source files and generate a POT file.
        """
        mapping = None
        if options.domain in MAPPINGS:
            mapping = '%s.cfg' % options.domain
            fo = open(mapping, 'w')
            fo.write(MAPPINGS[options.domain])
            fo.close()

        argv = ['-F', mapping] if mapping else []

        try:
            for pkg, path, locales in self.locale_info(options, args):
                if not os.path.exists(path):
                    os.mkdir(path)
                pot, po, mo = self.get_files(pkg, None, options.domain)
                if options.verbose:
                    print 'creating PO template %r' % pot
                self.run_babel('extract', pkg, '-o', pot, *argv)
        finally:
            if mapping:
                os.remove(mapping)

    def action_update(self, options, args):
        """Update existing message catalogs from the generated POT file.
        """
        for pkg, path, locales in self.locale_info(options, args):
            if not os.path.exists(path):
                continue
            for locale in locales:
                pot, po, mo = self.get_files(pkg, locale, options.domain)
                if not os.path.exists(po):
                    continue
                if options.verbose:
                    print 'updating catelog %r' % po
                self.run_babel('update', '-N', '-i', pot, '-o', po, '-l', locale)

    def action_compile(self, options, args):
        """Compile message catalogs to MO files.
        """
        for pkg, path, locales in self.locale_info(options, args):
            if not os.path.exists(path):
                continue
            for locale in locales:
                pot, po, mo = self.get_files(pkg, locale, options.domain)
                if not os.path.exists(po):
                    continue
                if options.verbose:
                    print 'compiling catelog %r' % po
                self.run_babel('compile', '-i', po, '-o', mo)
