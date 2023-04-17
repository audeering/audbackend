class BackendError(Exception):
    r"""Wrapper for any error raised on the backend.

    Args:
        exception: exception raised by backend

    """
    def __init__(
            self,
            exception: Exception,
    ):
        self.exception = exception
        r"""Exception raised by backend."""

        super().__init__(
            'An exception was raised by the backend, '
            'please see stack trace for further information.'
        )
