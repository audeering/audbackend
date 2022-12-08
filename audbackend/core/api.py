import typing

from audbackend.core.artifactory import Artifactory
from audbackend.core.backend import Backend
from audbackend.core.filesystem import FileSystem


backends = {}
r"""Backend cache."""

backend_registry = {
    'file-system': FileSystem,
    'artifactory': Artifactory,
}
r"""Backend registry."""


def available() -> typing.Dict[str, typing.List[Backend]]:
    r"""List available backends.

    Returns:
        sorted dictionary with backends

    Examples:
        >>> list(available())
        ['artifactory', 'file-system']
        >>> available()['artifactory']
        [('Artifactory', 'https://audeering.jfrog.io/artifactory', 'repo')]

    """
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
    r"""Create backend.

    Args:
        name: backend registry name
        host: host address
        repository: repository name

    Returns:
        backend object

    Raises:
        ValueError: if registry name does not exist

    Example:
        >>> create(
        ...     'artifactory',
        ...     'https://audeering.jfrog.io/artifactory',
        ...     'repo',
        ... )
        ('Artifactory', 'https://audeering.jfrog.io/artifactory', 'repo')

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
        backends[name][host][repository] = backend(host, repository)
    return backends[name][host][repository]


def register(
        name: str,
        cls: typing.Type[Backend],
):
    r"""Register backend.

    If a backend with this name already exists,
    it will be overwritten.

    Args:
        name: backend registry name
        cls: backend class

    Example:
        >>> register('file-system', FileSystem)

    """
    backend_registry[name] = cls


register('artifactory', Artifactory)
register('file-system', FileSystem)
