import warnings

import audeer

from audbackend.core.backend.base import Base
from audbackend.core.backend.filesystem import FileSystem


backends = {}
r"""Backend cache."""

backend_registry = {}
r"""Backend registry."""


@audeer.deprecated(removal_version="2.2.0", alternative="backend classes directly")
def register(
    name: str,
    cls: type[Base],
):
    r"""Register backend class.

    If there is already a backend class
    registered under the alias ``name``
    it will be overwritten.

    .. Warning::

        ``audbackend.register()`` is deprecated
        and will be removed in version 2.2.0.
        Instead of backend names
        we now use backend classes,
        such as :class:`audbackend.backend.FileSystem`.

    Args:
        name: backend alias
        cls: backend class

    """
    backend_registry[name] = cls


with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    register("file-system", FileSystem)

    # Register optional backends
    try:
        from audbackend.core.backend.artifactory import Artifactory

        register("artifactory", Artifactory)
    except ImportError:  # pragma: no cover
        pass

    # Register optional backends
    try:
        from audbackend.core.backend.minio import Minio

        register("minio", Minio)
    except ImportError:  # pragma: no cover
        pass
