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
except ImportError:  # pragma: no cover
    pass


__all__ = []


# Dynamically get the version of the installed module
try:
    import importlib.metadata
    __version__ = importlib.metadata.version(__name__)
except Exception:  # pragma: no cover
    importlib = None  # pragma: no cover
finally:
    del importlib
