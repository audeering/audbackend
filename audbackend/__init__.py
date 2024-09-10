from audbackend.core.base import AbstractBackend
from audbackend.core.errors import BackendError
from audbackend.core.maven import Maven
from audbackend.core.unversioned import Unversioned
from audbackend.core.versioned import Versioned


__all__ = []


# Dynamically get the version of the installed module
try:
    import importlib.metadata

    __version__ = importlib.metadata.version(__name__)
except Exception:  # pragma: no cover
    importlib = None  # pragma: no cover
finally:
    del importlib
