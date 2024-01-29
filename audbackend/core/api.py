import typing

from audbackend.core import utils
from audbackend.core.backend.base import Base
from audbackend.core.backend.filesystem import FileSystem
from audbackend.core.interface.base import Base as Interface
from audbackend.core.interface.versioned import Versioned


backends = {}
r"""Backend cache."""

backend_registry = {}
r"""Backend registry."""


def _backend(
        name: str,
        host: str,
        repository: str,
) -> Base:
    r"""Get backend instance."""
    if name not in backend_registry:
        raise ValueError(
            f"A backend class with name "
            f"'{name}' "
            f"does not exist. "
            f"Use 'audbackend.register()' to register one."
        )

    if name not in backends:
        backends[name] = {}
    if host not in backends[name]:
        backends[name][host] = {}
    if repository not in backends[name][host]:
        backend = utils.call_function_on_backend(
            backend_registry[name],
            host,
            repository,
        )
        backends[name][host][repository] = backend

    backend = backends[name][host][repository]
    return backend


def access(
        name: str,
        host: str,
        repository: str,
        *,
        interface: typing.Type[Interface] = Versioned,
        interface_kwargs: dict = None,
) -> Interface:
    r"""Access repository.

    Returns an ``interface`` instance
    to access the ``repository``
    located at ``host``
    on the backend with alias ``name``
    (see :func:`audbackend.register`).

    Use :func:`audbackend.available`
    to list available repositories
    or :func:`audbackend.create`
    to create a new repository.

    Args:
        name: backend alias
        host: host address
        repository: repository name
        interface: interface class
        interface_kwargs: keyword arguments for interface class

    Returns:
        interface object

    Raises:
        BackendError: if an error is raised on the backend,
            e.g. repository does not exist
        ValueError: if no backend class with alias ``name``
            has been registered

    Examples:
        >>> access('file-system', 'host', 'repo')
        audbackend.core.interface.versioned.Versioned('audbackend.core.backend.filesystem.FileSystem', 'host', 'repo')

    """  # noqa: E501
    backend = _backend(name, host, repository)
    utils.call_function_on_backend(backend._access)
    interface_kwargs = interface_kwargs or {}
    return interface(backend, **interface_kwargs)


def available() -> typing.Dict[str, typing.List[Base]]:
    r"""List available repositories.

    Returns a dictionary with
    backend alias name as key
    (see :func:`audbackend.register`)
    and a list with repositories
    on that backend as value
    (see :func:`audbackend.create`).

    Returns:
        dictionary with repositories

    Examples:
        >>> list(available())
        ['artifactory', 'file-system']
        >>> available()['file-system'][0]
        ('audbackend.core.backend.filesystem.FileSystem', 'host', 'repo')

    """  # noqa: E501
    result = {}

    for name in sorted(backend_registry):
        result[name] = []
        if name in backends:
            for repository in backends[name].values():
                for backend in repository.values():
                    result[name].append(backend)

    return result


def create(
        name: str,
        host: str,
        repository: str,
):
    r"""Create repository.

    Creates ``repository``
    located at ``host``
    on the backend with alias ``name``
    (see :func:`audbackend.register`).

    Use :func:`audbackend.available`
    to list available repositories
    and :func:`audbackend.access`
    to access the repository.

    .. note:: For legacy reasons the method
        returns an (undocumented) instance of
        :class:`audbackend.interface.Versioned`.
        Since the return value might be removed in
        a future version it is not recommended to use it.

    Args:
        name: backend alias
        host: host address
        repository: repository name

    Raises:
        BackendError: if an error is raised on the backend,
            e.g. repository exists already
            or cannot be created
        ValueError: if no backend class with alias ``name``
            has been registered

    Examples:
        >>> create('file-system', 'host', 'repository')

    """  # noqa: E501
    backend = _backend(name, host, repository)
    utils.call_function_on_backend(backend._create)
    # for legacy reasons we return a versioned interface
    return Versioned(backend)


def delete(
        name: str,
        host: str,
        repository: str,
):
    r"""Delete repository.

    .. warning:: Deletes the repository and all its content.

    Deletes the repository
    with name ``repository``
    located at ``host``
    on the backend with alias ``name``
    and removes it from the
    list of available repositories
    (see :func:`audbackend.available`).

    Args:
        name: backend alias
        host: host address
        repository: repository name

    Raises:
        BackendError: if an error is raised on the backend,
            e.g. repository does not exist
        ValueError: if no backend class with alias ``name``
            has been registered

    Examples:
        >>> access('file-system', 'host', 'repo').ls()
        [('/a.zip', '1.0.0'), ('/a/b.ext', '1.0.0'), ('/f.ext', '1.0.0'), ('/f.ext', '2.0.0')]
        >>> delete('file-system', 'host', 'repo')
        >>> create('file-system', 'host', 'repo')
        >>> access('file-system', 'host', 'repo').ls()
        []

    """  # noqa: E501
    interface = access(name, host, repository)
    utils.call_function_on_backend(interface._backend._delete)
    backends[name][host].pop(repository)


def register(
        name: str,
        cls: typing.Type[Base],
):
    r"""Register backend class.

    If there is already a backend class
    registered under the alias ``name``
    it will be overwritten.

    Args:
        name: backend alias
        cls: backend class

    Examples:
        >>> register('file-system', FileSystem)

    """
    backend_registry[name] = cls


register('file-system', FileSystem)

# Register optional backends
try:
    from audbackend.core.backend.artifactory import Artifactory
    register('artifactory', Artifactory)
except ImportError:  # pragma: no cover
    pass
