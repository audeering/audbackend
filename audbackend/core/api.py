import typing

from audbackend.core.artifactory import Artifactory
from audbackend.core.backend import Backend
from audbackend.core.filesystem import FileSystem
from audbackend.core import utils


backends = {}
r"""Backend cache."""

backend_registry = {
    'file-system': FileSystem,
    'artifactory': Artifactory,
}
r"""Backend registry."""


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
    r"""Create backend instance.

    Returns a backend instance for the
    ``repository`` on the ``host``.
    The instance is an object of the class
    registered under the alias ``name``
    with :func:`audbackend.register`.

    If the ``repository``
    does not yet exist
    on the ``host``
    it will be created.
    If this is not possible
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
        BackendError: if an error is raised on the backend
        ValueError: if no backend class with alias ``name``
            has been registered

    Examples:
        >>> create('file-system', 'host', 'doctest')
        ('audbackend.core.filesystem.FileSystem', 'host', 'doctest')

    """
    if name not in backend_registry:
        raise ValueError(
            'A backend class with name '
            f"'{name} "
            'does not exist.'
            "Use 'register_backend()' to register one."
        )

    if name not in backends:
        backends[name] = {}
    if host not in backends[name]:
        backends[name][host] = {}
    if repository not in backends[name][host]:
        backend = backend_registry[name]
        backends[name][host][repository] = utils.call_function_on_backend(
            backend,
            host,
            repository,
        )
    return backends[name][host][repository]


def delete(
        name: str,
        host: str,
        repository: str,
):
    r"""Delete repository and remove backend instance.

    .. warning:: Deletes the repository and all its content.

    If an instance of the backend exists,
    it will be removed from the available instances.
    See also :func:`audbackend.available`.

    Args:
        name: alias under which backend class is registered
        host: host address
        repository: repository name

    Raises:
        BackendError: if an error is raised on the backend
        ValueError: if no backend class with alias ``name``
            has been registered

    Examples:
        >>> create('file-system', 'host', 'doctest').ls()
        [('a.zip', '1.0.0'), ('a/b.ext', '1.0.0'), ('name.ext', '1.0.0'), ('name.ext', '2.0.0')]
        >>> delete('file-system', 'host', 'doctest')
        >>> create('file-system', 'host', 'doctest').ls()
        []

    """  # noqa: E501
    backend = create(name, host, repository)
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


register('artifactory', Artifactory)
register('file-system', FileSystem)
