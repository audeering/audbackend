from audbackend import backend
from audbackend import interface
from audbackend.core.backend.base import Base as Backend  # legacy
from audbackend.core.backend.filesystem import FileSystem  # legacy
from audbackend.core.errors import BackendError
from audbackend.core.repository import Repository

# Import optional backends (legacy)
try:
    from audbackend.core.backend.artifactory import Artifactory
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
