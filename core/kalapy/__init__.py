
# import i18n so that `_` is available as builtin
import i18n

from kalapy.release import version as __version__

def get_version():
    """Get the version number string of the project.

    The sequance based version number scheme is being followed. The version
    number represents three identifiers major, minor and revision.

    __version__ = "major.minor.revision"

    The major number is increased when there are significant jumps in features and
    functionality, the minor number is incremented when only minor features or
    significant fixes have been added, and the revision number is incremented when
    minor bugs are fixed.

    0.x.x series will be used during first alpha developement stage
    0.9.x series will be used during first beta development stage

    1.x.x series will be used during first public release.
    """
    return __version__
