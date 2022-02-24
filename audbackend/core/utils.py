import hashlib
import re
import typing

import audeer


BACKEND_ALLOWED_CHARS = '[A-Za-z0-9/._-]+'
BACKEND_ALLOWED_CHARS_COMPILED = re.compile(BACKEND_ALLOWED_CHARS)


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


def check_path_for_allowed_chars(path):
    if BACKEND_ALLOWED_CHARS_COMPILED.fullmatch(path) is None:
        raise ValueError(
            f"Invalid path name '{path}', "
            f"allowed characters are '{BACKEND_ALLOWED_CHARS}'."
        )
