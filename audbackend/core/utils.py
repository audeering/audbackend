import errno
import hashlib
import os
import re
import typing

import audeer


BACKEND_ALLOWED_CHARS = '[A-Za-z0-9/._-]+'
BACKEND_ALLOWED_CHARS_COMPILED = re.compile(BACKEND_ALLOWED_CHARS)


def check_path_and_ext(
        path: str,
        ext: typing.Optional[str],
) -> typing.Tuple[str, typing.Optional[str]]:
    r"""Check path and extension.

    1. assert path contains only allowed chars
    2. if extension is None, split string after last dot
    3. if extension is not empty, make sure it starts with a dot
    4. assert path ends on extension

    """

    check_path_for_allowed_chars(path)

    if ext is None:
        _, ext = os.path.splitext(path)

    if ext and not ext.startswith('.'):
        ext = '.' + ext

    if ext and not path.endswith(ext):
        raise ValueError(
            f"Invalid path name '{path}', "
            f"does not end on '{ext}'."
        )

    return path, ext


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
    r"""Create MD5 checksum."""
    file = audeer.safe_path(file)
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


def raise_file_not_found_error(
        path: str,
        *,
        version: str = None,
):
    if version:
        path = f'{path} with version {version}'

    raise FileNotFoundError(
        errno.ENOENT,
        os.strerror(errno.ENOENT),
        path,
    )


def splitext(
        path: str,
        ext: str,
) -> typing.Tuple[str, str]:
    r"""Split path into basename and ext."""
    if ext:
        path = path[:-len(ext)]
    return path, ext
