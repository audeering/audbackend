import errno
import os
import re
import typing

from audbackend.core.errors import BackendError


BACKEND_ALLOWED_CHARS = '[A-Za-z0-9/._-]+'
BACKEND_ALLOWED_CHARS_COMPILED = re.compile(BACKEND_ALLOWED_CHARS)


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


def check_path(path, sep) -> str:
    r"""Check path."""

    # Assert path starts with sep and does not contain invalid characters.
    if not path.startswith(sep):
        raise ValueError(
            f"Invalid backend path '{path}', "
            f"must start with '{sep}'."
        )
    if path and BACKEND_ALLOWED_CHARS_COMPILED.fullmatch(path) is None:
        raise ValueError(
            f"Invalid backend path '{path}', "
            f"allowed characters are '{BACKEND_ALLOWED_CHARS}'."
        )

    # Remove immediately consecutive seps
    is_sub_path = path.endswith(sep)
    paths = path.split(sep)
    paths = [path for path in paths if path]
    path = sep + sep.join(paths)
    if is_sub_path and not path.endswith(sep):
        path += sep

    return path


def raise_file_exists_error(path: str):
    raise FileExistsError(
        errno.EEXIST,
        os.strerror(errno.EEXIST),
        path,
    )


def raise_file_not_found_error(path: str):
    raise FileNotFoundError(
        errno.ENOENT,
        os.strerror(errno.ENOENT),
        path,
    )
