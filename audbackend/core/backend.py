import errno
import fnmatch
import os
import tempfile
import typing

import audeer

from audbackend.core import utils
from audbackend.core.errors import BackendError


class Base:
    r"""Base class."""

    def __repr__(self) -> str:  # noqa: D105
        name = f'{self.__class__.__module__}.{self.__class__.__name__}'
        return str((name, self.host, self.repository))

    def join(
            self,
            path: str,
            *paths,
    ) -> str:
        r"""Join to path on backend.

        Args:
            path: first part of path
            *paths: additional parts of path

        Returns:
            path joined by :attr:`Backend.sep`

        Raises:
            ValueError: if ``path`` contains invalid character
                or does not start with ``'/'``,
                or if joined path contains invalid character

        Examples:
            >>> backend.join('/', 'f.ext')
            '/f.ext'
            >>> backend.join('/sub', 'f.ext')
            '/sub/f.ext'
            >>> backend.join('//sub//', '/', '', None, '/f.ext')
            '/sub/f.ext'

        """
        path = utils.check_path(path)

        paths = [path] + [p for p in paths]
        paths = [path for path in paths if path]  # remove empty or None
        path = self.sep.join(paths)

        path = utils.check_path(path)

        return path

    @property
    def sep(self) -> str:
        r"""File separator on backend.

        Returns: file separator

        """
        return utils.BACKEND_SEPARATOR

    def split(
            self,
            path: str,
    ) -> typing.Tuple[str, str]:
        r"""Split path on backend into sub-path and basename.

        Args:
            path: path containing :attr:`Backend.sep` as separator

        Returns:
            tuple containing (root, basename)

        Raises:
            ValueError: if ``path`` does not start with ``'/'`` or
                does not match ``'[A-Za-z0-9/._-]+'``

        Examples:
            >>> backend.split('/')
            ('/', '')
            >>> backend.split('/f.ext')
            ('/', 'f.ext')
            >>> backend.split('/sub/')
            ('/sub/', '')
            >>> backend.split('/sub//f.ext')
            ('/sub/', 'f.ext')

        """
        path = utils.check_path(path)

        root = self.sep.join(path.split(self.sep)[:-1]) + self.sep
        basename = path.split(self.sep)[-1]

        return root, basename


class Backend(Base):
    r"""Abstract backend.

    Implement class to create a new backend.

    Args:
        host: host address
        repository: repository name

    """
    def __init__(
            self,
            host: str,
            repository: str,
    ):
        self.host = host
        r"""Host path."""
        self.repository = repository
        r"""Repository name."""

    def _access(
            self,
    ):  # pragma: no cover
        r"""Access existing repository.

        * If repository does not exist an error should be raised

        """
        raise NotImplementedError()

    def _checksum(
            self,
            path: str,
    ) -> str:  # pragma: no cover
        r"""MD5 checksum of file on backend."""
        raise NotImplementedError()

    def checksum(
            self,
            path: str,
    ) -> str:
        r"""MD5 checksum of file on backend."""
        return utils.call_function_on_backend(
            self._checksum,
            path,
        )

    def _create(
            self,
    ):  # pragma: no cover
        r"""Create a new repository.

        * If repository exists already an error should be raised

        """
        raise NotImplementedError()

    def _date(
            self,
            path: str,
    ) -> str:  # pragma: no cover
        r"""Last modification date of file on backend.

        * Return empty string if date cannot be determined
        * Format should be '%Y-%m-%d'

        """
        raise NotImplementedError()

    def date(
            self,
            path: str,
    ) -> str:
        r"""Last modification date of file on backend."""
        return utils.call_function_on_backend(
            self._date,
            path,
        )

    def _delete(
            self,
    ):  # pragma: no cover
        r"""Delete repository and all its content."""
        raise NotImplementedError()

    def _exists(
            self,
            path: str,
    ) -> bool:  # pragma: no cover
        r"""Check if file exists on backend."""
        raise NotImplementedError()

    def exists(
            self,
            path: str,
            *,
            suppress_backend_errors: bool = False,
    ) -> bool:
        r"""Check if file exists on backend."""
        return utils.call_function_on_backend(
            self._exists,
            path,
            suppress_backend_errors=suppress_backend_errors,
            fallback_return_value=False,
        )

    def _get_file(
            self,
            src_path: str,
            dst_path: str,
            verbose: bool,
    ):  # pragma: no cover
        r"""Get file from backend."""
        raise NotImplementedError()

    def get_file(
            self,
            src_path: str,
            dst_path: str,
            *,
            verbose: bool = False,
    ) -> str:
        r"""Get file from backend."""
        dst_path = audeer.path(dst_path)
        if os.path.isdir(dst_path):
            raise utils.raise_is_a_directory(dst_path)

        dst_root = os.path.dirname(dst_path)
        audeer.mkdir(dst_root)

        if (
            not os.access(dst_root, os.W_OK) or
            (os.path.exists(dst_path) and not os.access(dst_path, os.W_OK))
        ):  # pragma: no Windows cover
            msg = f"Permission denied: '{dst_path}'"
            raise PermissionError(msg)

        if (
            not os.path.exists(dst_path)
            or audeer.md5(dst_path) != self.checksum(src_path)
        ):
            # get file to a temporary directory first,
            # only on success move to final destination
            with tempfile.TemporaryDirectory(dir=dst_root) as tmp:
                tmp_path = audeer.path(tmp, '~')
                utils.call_function_on_backend(
                    self._get_file,
                    src_path,
                    tmp_path,
                    verbose,
                )
                audeer.move_file(tmp_path, dst_path)

        return dst_path

    def _ls(
            self,
            path: str,
    ) -> typing.List[str]:  # pragma: no cover
        r"""List all files under sub-path.

        If ``path`` is ``'/'`` and no files exist on the repository,
        an empty list should be returned
        Otherwise,
        if ``path`` does not exist or no files are found under ``path``,
        an error should be raised.

        """
        raise NotImplementedError()

    def ls(
            self,
            path: str = '/',
            *,
            pattern: str = None,
            suppress_backend_errors: bool = False,
    ) -> typing.List[str]:
        r"""List files on backend."""

        path = utils.check_path(path)

        if path.endswith('/'):  # find files under sub-path

            paths = utils.call_function_on_backend(
                self._ls,
                path,
                suppress_backend_errors=suppress_backend_errors,
                fallback_return_value=[],
            )

        else:  # find path

            if self.exists(path):
                paths = [path]
            else:
                if not suppress_backend_errors:
                    # since the backend does no longer raise an error
                    # if the path does not exist
                    # we have to do it
                    ex = FileNotFoundError(
                        errno.ENOENT,
                        os.strerror(errno.ENOENT),
                        path,
                    )
                    raise BackendError(ex)
                paths = []

        if not paths:
            return []

        paths = sorted(paths)

        if pattern:
            paths = [
                p for p in paths if fnmatch.fnmatch(os.path.basename(p), pattern)
            ]

        return paths

    def _owner(
            self,
            path: str,
    ) -> str:  # pragma: no cover
        r"""Owner of file on backend.

        * Return empty string if owner cannot be determined

        """
        raise NotImplementedError()

    def owner(
            self,
            path: str,
    ) -> str:
        r"""Owner of file on backend."""
        return utils.call_function_on_backend(
            self._owner,
            path,
        )

    def _put_file(
            self,
            src_path: str,
            dst_path: str,
            checksum: str,
            verbose: bool,
    ):  # pragma: no cover
        r"""Put file to backend."""
        raise NotImplementedError()

    def put_file(
            self,
            src_path: str,
            dst_path: str,
            *,
            verbose: bool = False,
    ):
        r"""Put file on backend."""
        if not os.path.exists(src_path):
            utils.raise_file_not_found_error(src_path)
        elif os.path.isdir(src_path):
            raise utils.raise_is_a_directory(src_path)

        checksum = audeer.md5(src_path)

        # skip if file with same checksum already exists
        if (
            not self.exists(dst_path)
            or self.checksum(dst_path) != checksum
        ):
            utils.call_function_on_backend(
                self._put_file,
                src_path,
                dst_path,
                checksum,
                verbose,
            )

    def _remove_file(
            self,
            path: str,
    ):  # pragma: no cover
        r"""Remove file from backend."""
        raise NotImplementedError()

    def remove_file(
            self,
            path: str,
    ):
        r"""Remove file from backend."""
        utils.call_function_on_backend(
            self._remove_file,
            path,
        )
