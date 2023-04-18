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
        **kwargs,
) -> typing.Any:
    try:
        return function(*args, **kwargs)
    except Exception as ex:
        raise BackendError(ex)


def check_path_for_allowed_chars(path):
    if path and BACKEND_ALLOWED_CHARS_COMPILED.fullmatch(path) is None:
        raise ValueError(
            f"Invalid path name '{path}', "
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
        >>> path = audeer.path(tmp, 'src.pth')
        >>> md5(path)
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


def raise_file_not_found_error(path: str):
    raise FileNotFoundError(
        errno.ENOENT,
        os.strerror(errno.ENOENT),
        path,
    )
