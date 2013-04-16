"""
kalapy.contrib.sessions.engines.memcached
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Memcached based storage backend for the sessions.

:copyright: (c) 2010 Amit Mendapara.
:license: BSD, see LINCESE for more details.
"""
from werkzeug.contrib.sessions import SessionStore
from werkzeug.contrib.cache import MemcachedCache, GAEMemcachedCache

from kalapy.conf import settings


class Store(SessionStore):

    def __init__(self, session_class=None):
        super(Store, self).__init__(session_class)
        if settings.DATABASE_ENGINE == 'gae':
            self.cache = GAEMemcachedCache(default_timeout=0)
        else:
            server = settings.SESSION_OPTIONS.get('memcached_servers', [])
            self.cache = MemcachedCache(servers, default_timeout=0)

    def save(self, session):
        self.cache.set(session.sid, dict(session))

    def delete(self, session):
        self.cache.delete(session.sid)

    def get(self, sid):
        if not self.is_valid_key(sid):
            return self.session_class.new()
        try:
            data = self.cache.get(sid)
        except:
            data = {}
        return self.session_class(data, sid, False)

    def list(self):
        return self.cache.get_dict().keys()

