import datetime
import errno
import os
import typing

from audbackend.core.errors import BackendError


def call_function_on_backend(
    function: typing.Callable,
    *args,
    suppress_backend_errors: bool = False,
    fallback_return_value: typing.Any = None,
    **kwargs,
) -> typing.Any:
    try:
        return function(*args, **kwargs)
    except Exception as ex:
        if suppress_backend_errors:
            return fallback_return_value
        else:
            raise BackendError(ex)


def date_format(date: datetime.datetime) -> str:
    return date.strftime("%Y-%m-%d")


def raise_file_not_found_error(path: str):
    raise FileNotFoundError(
        errno.ENOENT,
        os.strerror(errno.ENOENT),
        path,
    )


def raise_is_a_directory(path: str):
    raise IsADirectoryError(
        errno.EISDIR,
        os.strerror(errno.EISDIR),
        path,
    )
