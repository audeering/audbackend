import datetime
import errno
import os
import re
import typing

from audbackend.core.errors import BackendError


BACKEND_ALLOWED_CHARS = '[A-Za-z0-9/._-]+'
BACKEND_ALLOWED_CHARS_COMPILED = re.compile(BACKEND_ALLOWED_CHARS)

BACKEND_SEPARATOR = '/'

VERSION_ALLOWED_CHARS = BACKEND_ALLOWED_CHARS.replace(BACKEND_SEPARATOR, '')
VERSION_ALLOWED_CHARS_COMPILED = re.compile(VERSION_ALLOWED_CHARS)


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


def check_path(path: str) -> str:
    r"""Check path."""
    # Assert path starts with sep and does not contain invalid characters.
    if not path.startswith(BACKEND_SEPARATOR):
        raise ValueError(
            f"Invalid backend path '{path}', "
            f"must start with '{BACKEND_SEPARATOR}'."
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
        raise ValueError('Version must not be empty.')
    if VERSION_ALLOWED_CHARS_COMPILED.fullmatch(version) is None:
        raise ValueError(
            f"Invalid version '{version}', "
            f"does not match '{VERSION_ALLOWED_CHARS}'."
        )

    return version


def date_format(date: datetime.datetime) -> str:
    return date.strftime('%Y-%m-%d')


def file_owner(path: str) -> str:
    r"""Get file owner."""
    if os.name == 'nt':  # pragma: no cover

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
