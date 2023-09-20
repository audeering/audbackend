import typing

from audbackend.core import utils
from audbackend.core.backend import Backend
from audbackend.core.filesystem import FileSystem


backends = {}
r"""Backend cache."""

backend_registry = {}
r"""Backend registry."""


def _backend(
        name: str,
        host: str,
        repository: str,
) -> Backend:
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
        backends[name][host][repository] = utils.call_function_on_backend(
            backend_registry[name],
            host,
            repository,
        )

    return backends[name][host][repository]


def access(
        name: str,
        host: str,
        repository: str,
) -> Backend:
    r"""Access repository.

    Returns a backend instance
    for the ``repository``
    on the ``host``.
    The instance is an object of the class
    registered under the alias ``name``
    with :func:`audbackend.register`.

    If the repository does not exist
    or cannot be accessed for other reasons
    (e.g. user lacks permission)
    an error of type
    :class:`audbackend.BackendError`
    is raised.

    Use :func:`audbackend.available`
    to list available backend instances.

    Args:
        name: alias under which backend class is registered
        host: host address
        repository: repository name

    Returns:
        backend object

    Raises:
        BackendError: if an error is raised on the backend,
            e.g. repository does not exist
        ValueError: if no backend class with alias ``name``
            has been registered

    Examples:
        >>> access('file-system', 'host', 'doctest')
        ('audbackend.core.filesystem.FileSystem', 'host', 'doctest')

    """
    backend = _backend(name, host, repository)
    utils.call_function_on_backend(backend._access)
    return backend


def available() -> typing.Dict[str, typing.List[Backend]]:
    r"""List available backend instances.

    Returns a dictionary with
    registered backend aliases as keys
    (see :func:`audbackend.register`)
    and a list with backend instances as values
    (see :func:`audbackend.create`).

    Returns:
        dictionary with backend instances

    Examples:
        >>> list(available())
        ['artifactory', 'file-system']
        >>> available()['file-system']
        [('audbackend.core.filesystem.FileSystem', 'host', 'doctest')]

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
) -> Backend:
    r"""Create repository.

    Creates the ``repository``
    on the ``host``
    and returns a backend instance for it.
    The instance is an object of the class
    registered under the alias ``name``
    with :func:`audbackend.register`.

    If the repository cannot be created
    (e.g. user lacks permission)
    or if it exists already,
    an error of type
    :class:`audbackend.BackendError`
    is raised.

    Use :func:`audbackend.available`
    to list available backend instances.

    Args:
        name: alias under which backend class is registered
        host: host address
        repository: repository name

    Returns:
        backend object

    Raises:
        BackendError: if an error is raised on the backend,
            e.g. repository exists already
            or cannot be created
        ValueError: if no backend class with alias ``name``
            has been registered

    Examples:
        >>> create('file-system', 'host', 'repository')
        ('audbackend.core.filesystem.FileSystem', 'host', 'repository')

    """
    backend = _backend(name, host, repository)
    utils.call_function_on_backend(backend._create)
    return backend


def delete(
        name: str,
        host: str,
        repository: str,
):
    r"""Delete repository.

    .. warning:: Deletes the repository and all its content.

    If an instance of the backend exists,
    it will be removed from the available instances.
    See also :func:`audbackend.available`.

    Args:
        name: alias under which backend class is registered
        host: host address
        repository: repository name

    Raises:
        BackendError: if an error is raised on the backend,
            e.g. repository does not exist
        ValueError: if no backend class with alias ``name``
            has been registered

    Examples:
        >>> access('file-system', 'host', 'doctest').ls()
        [('/a.zip', '1.0.0'), ('/a/b.ext', '1.0.0'), ('/f.ext', '1.0.0'), ('/f.ext', '2.0.0')]
        >>> delete('file-system', 'host', 'doctest')
        >>> create('file-system', 'host', 'doctest').ls()
        []

    """  # noqa: E501
    backend = access(name, host, repository)
    utils.call_function_on_backend(backend._delete)
    backends[name][host].pop(repository)


def register(
        name: str,
        cls: typing.Type[Backend],
):
    r"""Register backend class.

    If there is already a backend class
    registered under the alias ``name``
    it will be overwritten.

    Args:
        name: alias under which backend class is registered
        cls: backend class

    Examples:
        >>> register('file-system', FileSystem)

    """
    backend_registry[name] = cls


register('file-system', FileSystem)

# Register optional backends
try:
    from audbackend.core.artifactory import Artifactory
    register('artifactory', Artifactory)
except ImportError:  # pragma: no cover
    pass
