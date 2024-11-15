class BackendError(Exception):
    r"""Wrapper for any error raised on the backend.

    Args:
        exception: exception raised by backend

    .. Prepare backend and interface for docstring examples

        >>> import audeer
        >>> import audbackend

    Examples:
        >>> host = audeer.mkdir("host")
        >>> audbackend.backend.FileSystem.create(host, "repo")
        >>> backend = audbackend.backend.FileSystem(host, "repo")
        >>> backend.open()
        >>> try:
        ...     interface = audbackend.interface.Unversioned(backend)
        ...     interface.checksum("/does/not/exist")
        ... except BackendError as ex:
        ...     ex.exception
        FileNotFoundError(2, 'No such file or directory')
        >>> try:
        ...     interface = audbackend.interface.Versioned(backend)
        ...     interface.checksum("/does/not/exist", "1.0.0")
        ... except BackendError as ex:
        ...     ex.exception
        FileNotFoundError(2, 'No such file or directory')

    """

    def __init__(
        self,
        exception: Exception,
    ):
        self.exception = exception
        r"""Exception raised by backend."""

        super().__init__(
            "An exception was raised by the backend, "
            "please see stack trace for further information."
        )
