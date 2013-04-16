
# Export some useful names from Werkzeug and Jinja2
from werkzeug import abort, redirect
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.contrib.securecookie import SecureCookie
from jinja2 import Markup, escape

from kalapy.web.local import *
from kalapy.web.helpers import *
from kalapy.web.wrappers import *
from kalapy.web.templating import *
from kalapy.web.package import *
from kalapy.web.app import *

# remove module references to hide them from direct outside access
map(lambda n: globals().pop(n), [
    'local', 'helpers', 'wrappers', 'templating', 'package', 'app'])

