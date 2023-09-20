from audbackend.core.api import access
from audbackend.core.api import available
from audbackend.core.api import create
from audbackend.core.api import delete
from audbackend.core.api import register
from audbackend.core.backend import Backend
from audbackend.core.errors import BackendError
from audbackend.core.filesystem import FileSystem
from audbackend.core.repository import Repository

# Import optional backends
try:
    from audbackend.core.artifactory import Artifactory
except ImportError:
    pass


__all__ = []


# Dynamically get the version of the installed module
try:
    import pkg_resources
    __version__ = pkg_resources.get_distribution(__name__).version
except Exception:  # pragma: no cover
    pkg_resources = None  # pragma: no cover
finally:
    del pkg_resources
