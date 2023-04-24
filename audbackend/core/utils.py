import errno
import hashlib
import os
import re
import typing

import audeer

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


def check_path(path, sep):
    if not path.startswith(sep):
        raise ValueError(
            f"Invalid path '{path}', "
            f"must start with '{sep}'."
        )
    if path and BACKEND_ALLOWED_CHARS_COMPILED.fullmatch(path) is None:
        raise ValueError(
            f"Invalid path '{path}', "
            f"allowed characters are '{BACKEND_ALLOWED_CHARS}'."
        )


def md5(
        file: str,
        chunk_size: int = 8192,
) -> str:
    r"""Calculate MD5 checksum.

    Args:
        file: path to file
        chunk_size: chunk size (does not have an influence on the result)

    Returns:
        checksum

    Examples:
        >>> md5('src.pth')
        'd41d8cd98f00b204e9800998ecf8427e'

    """
    file = audeer.path(file)
    with open(file, 'rb') as fp:
        hasher = hashlib.md5()
        for chunk in md5_read_chunk(fp, chunk_size):
            hasher.update(chunk)
        return hasher.hexdigest()


def md5_read_chunk(
        fp: typing.IO,
        chunk_size: int = 8192,
):
    while True:
        data = fp.read(chunk_size)
        if not data:
            break
        yield data


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
