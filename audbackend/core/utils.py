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
