import warnings


class Repository:
    r"""Repository object.

    It stores all information
    needed to address a repository:
    the repository name,
    host,
    and backend.

    .. Warning::

        ``audbackend.Repository`` is deprecated
        and will be removed in version 2.2.0.
        If an application requires
        repository objects,
        that assign string names to backends,
        they should be provided by the application.

    Args:
        name: repository name
        host: repository host
        backend: repository backend

    """

    def __init__(
        self,
        name: str,
        host: str,
        backend: str,
    ):
        self.name = name
        r"""Repository name."""
        self.host = host
        r"""Repository host."""
        self.backend = backend
        r"""Repository backend."""

        message = "Repository is deprecated and will be removed with version 2.2.0."
        warnings.warn(message, category=UserWarning, stacklevel=2)

    def __repr__(self):  # noqa: D105
        return f"Repository('{self.name}', '{self.host}', '{self.backend}')"
