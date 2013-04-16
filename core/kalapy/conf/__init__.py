"""
kalapy.conf
~~~~~~~~~~~

Configurations and application package loading.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LINCESE for more details.
"""
import os, types

from kalapy.conf import global_settings


class ConfigError(Exception):
    """Exception class for invalid configuration settings.
    """
    pass


class Settings(object):
    """Settings class holds package settings.
    """

    __freezed = False

    def __init__(self, settings_module, **options):
        self.__update(settings_module, **options)
        self.__freezed = False

    def __update(self, settings_module, **options):
        """Update the settings with provided settings_module.
        """
        if settings_module:
            if not isinstance(settings_module, types.ModuleType):
                raise ValueError("setting_module should be a module type.")
            for setting in dir(settings_module):
                if setting == setting.upper():
                    setattr(self, setting, getattr(settings_module, setting))
        for option, value in options.items():
            if not option.startswith('_'):
                setattr(self, option.upper(), value)

    def update(self, settings_module, **options):
        """Update the settings with provided settings_module and options.
        """
        if not options:
            assert settings_module is not None, \
                "provide settings via settings module or options keywords"
        self.__update(settings_module, **options)
        self.__freezed = True

    def __setattr__(self, name, value):
        if self.__freezed:
            raise AttributeError('Can not change settings.')
        else:
            super(Settings, self).__setattr__(name, value)


settings = Settings(global_settings)
