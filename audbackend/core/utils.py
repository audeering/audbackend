from collections.abc import Callable
import datetime
import errno
import os
import re

import audeer

from audbackend.core.errors import BackendError


BACKEND_ALLOWED_CHARS = "[A-Za-z0-9/._-]+"
BACKEND_ALLOWED_CHARS_COMPILED = re.compile(BACKEND_ALLOWED_CHARS)

BACKEND_SEPARATOR = "/"

VERSION_ALLOWED_CHARS = BACKEND_ALLOWED_CHARS.replace(BACKEND_SEPARATOR, "")
VERSION_ALLOWED_CHARS_COMPILED = re.compile(VERSION_ALLOWED_CHARS)


def call_function_on_backend(
    function: Callable,
    *args,
    suppress_backend_errors: bool = False,
    fallback_return_value: object = None,
    **kwargs,
) -> object:
    try:
        return function(*args, **kwargs)
    except Exception as ex:
        if suppress_backend_errors:
            return fallback_return_value
        else:
            raise BackendError(ex)


def check_path(
    path: str,
    *,
    allow_sub_path: bool = False,
) -> str:
    r"""Check path."""
    # Assert path starts with sep and does not contain invalid characters.
    if not path.startswith(BACKEND_SEPARATOR):
        raise ValueError(
            f"Invalid backend path '{path}', must start with '{BACKEND_SEPARATOR}'."
        )
    if not allow_sub_path and path.endswith(BACKEND_SEPARATOR):
        raise ValueError(
            f"Invalid backend path '{path}', must not end on '{BACKEND_SEPARATOR}'."
        )
    if path and BACKEND_ALLOWED_CHARS_COMPILED.fullmatch(path) is None:
        raise ValueError(
            f"Invalid backend path '{path}', "
            f"does not match '{BACKEND_ALLOWED_CHARS}'."
        )

    # Remove immediately consecutive seps
    is_sub_path = path.endswith(BACKEND_SEPARATOR)
    paths = path.split(BACKEND_SEPARATOR)
    paths = [path for path in paths if path]
    path = BACKEND_SEPARATOR + BACKEND_SEPARATOR.join(paths)
    if is_sub_path and not path.endswith(BACKEND_SEPARATOR):
        path += BACKEND_SEPARATOR

    return path


def check_version(version: str) -> str:
    r"""Check version."""
    # Assert version is not empty and does not contain invalid characters.
    if not version:
        raise ValueError("Version must not be empty.")
    if VERSION_ALLOWED_CHARS_COMPILED.fullmatch(version) is None:
        raise ValueError(
            f"Invalid version '{version}', "
            f"does not match '{VERSION_ALLOWED_CHARS}'."
        )

    return version


def checksum(file: str) -> str:
    r"""Checksum of file.

    The checksum is given by the MD5 sum
    as calculated with :func:`audeer.md5`.

    As parquet files are stored non-deterministically,
    we allow to use them with precalculated checksums,
    stored under the key ``b"hash"`` in its metadata.
    To support this feature pyarrow_
    has to be installed.
    A deterministic checksum,
    based on the content of the parquet file,
    can be calculated with :func:`audformat.utils.hash`.
    If the key is not present in the metadata of the parquet file,
    or pyarrow_ is not installed,
    its MD5 sum is calculated instead.

    .. _pyarrow: https://arrow.apache.org/docs/python/index.html

    Args:
        file: file path with extension

    Returns:
        MD5 checksum of file

    Raises:
        FileNotFoundError: if ``file`` does not exist

    Examples:
        >>> checksum("src.txt")
        'd41d8cd98f00b204e9800998ecf8427e'
        >>> import audformat
        >>> import pandas as pd
        >>> import pyarrow as pa
        >>> import pyarrow.parquet as pq
        >>> df = pd.DataFrame([0, 1], columns=["a"])
        >>> hash = audformat.utils.hash(df, strict=True)
        >>> hash
        '9021a9b6e1e696ba9de4fe29346319b2'
        >>> table = pa.Table.from_pandas(df)
        >>> table = table.replace_schema_metadata({"hash": hash})
        >>> pq.write_table(table, "file.parquet", compression="snappy")
        >>> checksum("file.parquet")
        '9021a9b6e1e696ba9de4fe29346319b2'

    """
    ext = audeer.file_extension(file)
    if ext == "parquet":
        try:
            import pyarrow.parquet as parquet

            metadata = parquet.read_schema(file).metadata or {}
            if b"hash" in metadata:
                return metadata[b"hash"].decode()
        except ModuleNotFoundError:
            pass
    return audeer.md5(file)


def date_format(date: datetime.datetime) -> str:
    return date.strftime("%Y-%m-%d")


def file_owner(path: str) -> str:
    r"""Get file owner."""
    if os.name == "nt":  # pragma: no cover
        import win32security

        sd = win32security.GetFileSecurity(
            path,
            win32security.OWNER_SECURITY_INFORMATION,
        )
        owner_sid = sd.GetSecurityDescriptorOwner()
        owner, _, _ = win32security.LookupAccountSid(None, owner_sid)

    else:  # pragma: no Windows cover
        import pwd

        owner = pwd.getpwuid(os.stat(path).st_uid).pw_name

    return owner


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


def raise_is_a_directory(path: str):
    raise IsADirectoryError(
        errno.EISDIR,
        os.strerror(errno.EISDIR),
        path,
    )
