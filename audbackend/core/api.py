import typing
import warnings

import audeer

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
        backend_cls = backend_registry[name]
        backend = backend_cls(host, repository)
        backends[name][host][repository] = backend

    backend = backends[name][host][repository]
    return backend


@audeer.deprecated(
    removal_version="2.2.0",
    alternative="Backend.__init__() of corresponding backend",
)
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

    .. Warning::

        ``audbackend.access()`` is deprecated
        and will be removed in version 2.2.0.
        Repositories on backends are instead accessed
        by instantiating the corresponding backend class,
        and connecting to it using the ``open()`` method,
        e.g.

        .. code-block:: python

            backend = audbackend.backend.FileSystem(host, repo)
            backend.open()

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

    """  # noqa: E501
    backend = _backend(name, host, repository)
    utils.call_function_on_backend(backend._open)
    interface_kwargs = interface_kwargs or {}
    return interface(backend, **interface_kwargs)


@audeer.deprecated(
    removal_version="2.2.0",
    alternative="class method Backend.create() of corresponding backend",
)
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

    .. note:: For legacy reasons the method
        returns an (undocumented) instance of
        :class:`audbackend.interface.Versioned`.
        Since the return value might be removed in
        a future version it is not recommended to use it.

    .. Warning::

        ``audbackend.create()`` is deprecated
        and will be removed in version 2.2.0.
        Repositories on backends are instead created
        by the class method ``create()``
        for the desired backend,
        e.g. :meth:`audbackend.backend.FileSystem.create`.

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

    """  # noqa: E501
    backend = _backend(name, host, repository)
    utils.call_function_on_backend(backend._create)
    # for legacy reasons we return a versioned interface
    return Versioned(backend)


@audeer.deprecated(
    removal_version="2.2.0",
    alternative="class method Backend.delete() of corresponding backend",
)
def delete(
    name: str,
    host: str,
    repository: str,
):
    r"""Delete repository.

    Deletes the repository
    with name ``repository``
    located at ``host``
    on the backend with alias ``name``.

    .. Warning::

        ``audbackend.delete()`` is deprecated
        and will be removed in version 2.2.0.
        Repositories on backends are instead deleted
        by the class method ``delete()``
        for the desired backend,
        e.g. :meth:`audbackend.backend.FileSystem.delete`.

    Args:
        name: backend alias
        host: host address
        repository: repository name

    Raises:
        BackendError: if an error is raised on the backend,
            e.g. repository does not exist
        ValueError: if no backend class with alias ``name``
            has been registered

    """  # noqa: E501
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        interface = access(name, host, repository)
    utils.call_function_on_backend(interface._backend._delete)
    backends[name][host].pop(repository)


@audeer.deprecated(removal_version="2.2.0", alternative="backend classes directly")
def register(
    name: str,
    cls: typing.Type[Base],
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
