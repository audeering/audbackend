class BackendError(Exception):
    r"""Wrapper for any error raised on the backend.

    Args:
        exception: exception raised by backend

    Examples:
        >>> import audbackend
        >>> try:
        ...     backend = audbackend.Unversioned(filesystem)
        ...     backend.checksum("/does/not/exist")
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
