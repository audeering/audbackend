from audbackend.core.backend.base import Base
from audbackend.core.backend.filesystem import FileSystem

# Import optional backends
try:
    from audbackend.core.backend.artifactory import Artifactory
except ImportError:  # pragma: no cover
    pass
try:
    from audbackend.core.backend.minio import Minio
except ImportError:  # pragma: no cover
    pass
