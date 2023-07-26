import fnmatch
import os
import tempfile
import typing

import audeer

from audbackend.core import utils


class Backend:
    r"""Abstract backend.

    A backend stores files and archives.

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

    def __repr__(self) -> str:  # noqa: D105
        name = f'{self.__class__.__module__}.{self.__class__.__name__}'
        return str((name, self.host, self.repository))

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
            version: str,
    ) -> str:  # pragma: no cover
        r"""MD5 checksum of file on backend."""
        raise NotImplementedError()

    def checksum(
            self,
            path: str,
            version: str,
    ) -> str:
        r"""Get MD5 checksum for file on backend.

        Args:
            path: path to file on backend
            version: version string

        Returns:
            MD5 checksum

        Raises:
            BackendError: if an error is raised on the backend,
                e.g. ``path`` does not exist
            ValueError: if ``path`` does not start with ``'/'`` or
                does not match ``'[A-Za-z0-9/._-]+'``
            ValueError: if ``version`` is empty or
                does not match ``'[A-Za-z0-9._-]+'``

        Examples:
            >>> backend.checksum('/f.ext', '1.0.0')
            'd41d8cd98f00b204e9800998ecf8427e'

        """
        path = utils.check_path(path)
        version = utils.check_version(version)

        return utils.call_function_on_backend(
            self._checksum,
            path,
            version,
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
            version: str,
    ) -> str:  # pragma: no cover
        r"""Get date of file on backend.

        * Return empty string if date cannot be determined
        * Format should be '%Y-%m-%d'

        """
        raise NotImplementedError()

    def date(
            self,
            path: str,
            version: str,
    ) -> str:
        r"""Get last modification date of file on backend.

        If the date cannot be determined,
        an empty string is returned.

        Args:
            path: path to file on backend
            version: version string

        Returns:
            date in format ``'yyyy-mm-dd'``

        Raises:
            BackendError: if an error is raised on the backend,
                e.g. ``path`` does not exist
            ValueError: if ``path`` does not start with ``'/'`` or
                does not match ``'[A-Za-z0-9/._-]+'``
            ValueError: if ``version`` is empty or
                does not match ``'[A-Za-z0-9._-]+'``

        Examples:
              >>> backend.date('/f.ext', '1.0.0')
              '1991-02-20'

        """
        path = utils.check_path(path)
        version = utils.check_version(version)

        return utils.call_function_on_backend(
            self._date,
            path,
            version,
        )

    def _delete(
            self,
    ):  # pragma: no cover
        r"""Delete repository and all its content."""
        raise NotImplementedError()

    def _exists(
            self,
            path: str,
            version: str,
    ) -> bool:  # pragma: no cover
        r"""Check if file exists on backend."""
        raise NotImplementedError()

    def exists(
            self,
            path: str,
            version: str,
            *,
            suppress_backend_errors: bool = False,
    ) -> bool:
        r"""Check if file exists on backend.

        Args:
            path: path to file on backend
            version: version string
            suppress_backend_errors: if set to ``True``,
                silently catch errors raised on the backend
                and return ``False``

        Returns:
            ``True`` if file exists

        Raises:
            BackendError: if ``suppress_backend_errors`` is ``False``
                and an error is raised on the backend,
                e.g. ``path`` does not exist
            ValueError: if ``path`` does not start with ``'/'`` or
                does not match ``'[A-Za-z0-9/._-]+'``
            ValueError: if ``version`` is empty or
                does not match ``'[A-Za-z0-9._-]+'``

        Examples:
            >>> backend.exists('/f.ext', '1.0.0')
            True

        """
        path = utils.check_path(path)
        version = utils.check_version(version)

        return utils.call_function_on_backend(
            self._exists,
            path,
            version,
            suppress_backend_errors=suppress_backend_errors,
            fallback_return_value=False,
        )

    def get_archive(
            self,
            src_path: str,
            dst_root: str,
            version: str,
            *,
            tmp_root: str = None,
            verbose: bool = False,
    ) -> typing.List[str]:
        r"""Get archive from backend and extract.

        The archive type is derived from the extension of ``src_path``.
        See :func:`audeer.extract_archive` for supported extensions.

        If ``dst_root`` does not exist,
        it is created.

        Args:
            src_path: path to archive on backend
            dst_root: local destination directory
            version: version string
            tmp_root: directory under which archive is temporarily extracted.
                Defaults to temporary directory of system
            verbose: show debug messages

        Returns:
            extracted files

        Raises:
            BackendError: if an error is raised on the backend,
                e.g. ``src_path`` does not exist
            FileNotFoundError: if ``tmp_root`` does not exist
            NotADirectoryError: if ``dst_root`` is not a directory
            PermissionError: if the user lacks write permissions
                for ``dst_path``
            RuntimeError: if extension of ``src_path`` is not supported
                or ``src_path`` is a malformed archive
            ValueError: if ``src_path`` does not start with ``'/'`` or
                does not match ``'[A-Za-z0-9/._-]+'``
            ValueError: if ``version`` is empty or
                does not match ``'[A-Za-z0-9._-]+'``

        Examples:
            >>> backend.get_archive('/a.zip', '.', '1.0.0')
            ['src.pth']

        """
        src_path = utils.check_path(src_path)
        version = utils.check_version(version)

        with tempfile.TemporaryDirectory(dir=tmp_root) as tmp:

            tmp_root = audeer.path(tmp, os.path.basename(dst_root))
            local_archive = os.path.join(
                tmp_root,
                os.path.basename(src_path),
            )
            self.get_file(
                src_path,
                local_archive,
                version,
                verbose=verbose,
            )

            return audeer.extract_archive(
                local_archive,
                dst_root,
                verbose=verbose,
            )

    def _get_file(
            self,
            src_path: str,
            dst_path: str,
            version: str,
            verbose: bool,
    ):  # pragma: no cover
        r"""Get file from backend."""
        raise NotImplementedError()

    def get_file(
            self,
            src_path: str,
            dst_path: str,
            version: str,
            *,
            verbose: bool = False,
    ) -> str:
        r"""Get file from backend.

        If the folder of
        ``dst_path`` does not exist,
        it is created.

        If ``dst_path`` exists
        with a different checksum,
        it is overwritten,
        or otherwise,
        the operation is silently skipped.

        To ensure the file is completely retrieved,
        it is first stored in a temporary directory
        and afterwards moved to ``dst_path``.

        Args:
            src_path: path to file on backend
            dst_path: destination path to local file
            version: version string
            verbose: show debug messages

        Returns:
            full path to local file

        Raises:
            BackendError: if an error is raised on the backend,
                e.g. ``src_path`` does not exist
            IsADirectoryError: if ``dst_path`` points to an existing folder
            PermissionError: if the user lacks write permissions
                for ``dst_path``
            ValueError: if ``src_path`` does not start with ``'/'`` or
                does not match ``'[A-Za-z0-9/._-]+'``
            ValueError: if ``version`` is empty or
                does not match ``'[A-Za-z0-9._-]+'``

        Examples:
            >>> os.path.exists('dst.pth')
            False
            >>> _ = backend.get_file('/f.ext', 'dst.pth', '1.0.0')
            >>> os.path.exists('dst.pth')
            True

        """
        src_path = utils.check_path(src_path)
        version = utils.check_version(version)

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
            or audeer.md5(dst_path) != self.checksum(src_path, version)
        ):
            # get file to a temporary directory first,
            # only on success move to final destination
            with tempfile.TemporaryDirectory(dir=dst_root) as tmp:
                tmp_path = audeer.path(tmp, '~')
                utils.call_function_on_backend(
                    self._get_file,
                    src_path,
                    tmp_path,
                    version,
                    verbose,
                )
                audeer.move_file(tmp_path, dst_path)

        return dst_path

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

    def latest_version(
            self,
            path: str,
    ) -> str:
        r"""Latest version of a file.

        Args:
            path: path to file on backend

        Returns:
            version string

        Raises:
            BackendError: if an error is raised on the backend,
                e.g. ``path`` does not exist
            ValueError: if ``path`` does not start with ``'/'`` or
                does not match ``'[A-Za-z0-9/._-]+'``

        Examples:
            >>> backend.latest_version('/f.ext')
            '2.0.0'

        """
        path = utils.check_path(path)
        vs = self.versions(path)
        return vs[-1]

    def _ls(
            self,
            path: str,
    ) -> typing.List[typing.Tuple[str, str]]:  # pragma: no cover
        r"""List all files under (sub-)path.

        * If path does not exist an error should be raised
        * If path ends on `/` it is a sub-path

        """
        raise NotImplementedError()

    def ls(
            self,
            path: str = '/',
            *,
            latest_version: bool = False,
            pattern: str = None,
            suppress_backend_errors: bool = False,
    ) -> typing.List[typing.Tuple[str, str]]:
        r"""List files on backend.

        Returns a sorted list of tuples
        with path and version.
        If a full path
        (e.g. ``/sub/file.ext``)
        is provided,
        all versions of the path are returned.
        If a sub-path
        (e.g. ``/sub/``)
        is provided,
        all files that start with
        the sub-path are returned.
        When ``path`` is set to ``'/'``
        a (possibly empty) list with
        all files on the backend is returned.

        Args:
            path: path or sub-path
                (if it ends with ``'/'``)
                on backend
            latest_version: if multiple versions of a file exist,
                only include the latest
            pattern: if not ``None``,
                return only files matching the pattern string,
                see :func:`fnmatch.fnmatch`
            suppress_backend_errors: if set to ``True``,
                silently catch errors raised on the backend
                and return an empty list

        Returns:
            list of tuples (path, version)

        Raises:
            BackendError: if ``suppress_backend_errors`` is ``False``
                and an error is raised on the backend,
                e.g. ``path`` does not exist
            ValueError: if ``path`` does not start with ``'/'`` or
                does not match ``'[A-Za-z0-9/._-]+'``

        Examples:
            >>> backend.ls()
            [('/a.zip', '1.0.0'), ('/a/b.ext', '1.0.0'), ('/f.ext', '1.0.0'), ('/f.ext', '2.0.0')]
            >>> backend.ls(latest_version=True)
            [('/a.zip', '1.0.0'), ('/a/b.ext', '1.0.0'), ('/f.ext', '2.0.0')]
            >>> backend.ls('/f.ext')
            [('/f.ext', '1.0.0'), ('/f.ext', '2.0.0')]
            >>> backend.ls(pattern='*.ext')
            [('/a/b.ext', '1.0.0'), ('/f.ext', '1.0.0'), ('/f.ext', '2.0.0')]
            >>> backend.ls('/a/')
            [('/a/b.ext', '1.0.0')]

        """  # noqa: E501
        path = utils.check_path(path)
        paths = utils.call_function_on_backend(
            self._ls,
            path,
            suppress_backend_errors=suppress_backend_errors,
            fallback_return_value=[],
        )
        if not paths:
            return paths

        paths = sorted(paths)

        if pattern:
            paths = [(p, v) for p, v in paths if fnmatch.fnmatch(p, pattern)]

        if latest_version:
            # d[path] = ['1.0.0', '2.0.0']
            d = {}
            for p, v in paths:
                if p not in d:
                    d[p] = []
                d[p].append(v)
            # d[path] = '2.0.0'
            for p, vs in d.items():
                d[p] = audeer.sort_versions(vs)[-1]
            # [(path, '2.0.0')]
            paths = [(p, v) for p, v in d.items()]

        return paths

    def _owner(
            self,
            path: str,
            version: str,
    ) -> str:  # pragma: no cover
        r"""Get owner of file on backend.

        * Return empty string if owner cannot be determined

        """
        raise NotImplementedError()

    def owner(
            self,
            path: str,
            version: str,
    ) -> str:
        r"""Get owner of file on backend.

        If the owner of the file
        cannot be determined,
        an empty string is returned.

        Args:
            path: path to file on backend
            version: version string

        Returns:
            owner

        Raises:
            BackendError: if an error is raised on the backend,
                e.g. ``path`` does not exist
            ValueError: if ``path`` does not start with ``'/'`` or
                does not match ``'[A-Za-z0-9/._-]+'``
            ValueError: if ``version`` is empty or
                does not match ``'[A-Za-z0-9._-]+'``

        Examples:
              >>> backend.owner('/f.ext', '1.0.0')
              'doctest'

        """
        path = utils.check_path(path)
        version = utils.check_version(version)

        return utils.call_function_on_backend(
            self._owner,
            path,
            version,
        )

    def put_archive(
            self,
            src_root: str,
            dst_path: str,
            version: str,
            *,
            files: typing.Union[str, typing.Sequence[str]] = None,
            tmp_root: str = None,
            verbose: bool = False,
    ):
        r"""Create archive and put on backend.

        The archive type is derived from the extension of ``dst_path``.
        See :func:`audeer.create_archive` for supported extensions.

        The operation is silently skipped,
        if an archive with the same checksum
        already exists on the backend.

        Args:
            src_root: local root directory where files are located.
                By default,
                all files below ``src_root``
                will be included into the archive.
                Use ``files`` to select specific files
            dst_path: path to archive on backend
            version: version string
            files: file(s) to include into the archive.
                Must exist within ``src_root``
            tmp_root: directory under which archive is temporarily created.
                Defaults to temporary directory of system
            verbose: show debug messages

        Raises:
            BackendError: if an error is raised on the backend
            FileNotFoundError: if ``src_root``,
                ``tmp_root``,
                or one or more ``files`` do not exist
            NotADirectoryError: if ``src_root`` is not a folder
            RuntimeError: if ``dst_path`` does not end with
                ``zip`` or ``tar.gz``
                or a file in ``files`` is not below ``root``
            ValueError: if ``dst_path`` does not start with ``'/'`` or
                does not match ``'[A-Za-z0-9/._-]+'``
            ValueError: if ``version`` is empty or
                does not match ``'[A-Za-z0-9._-]+'``

        Examples:
            >>> backend.exists('/a.tar.gz', '1.0.0')
            False
            >>> backend.put_archive('.', '/a.tar.gz', '1.0.0')
            >>> backend.exists('/a.tar.gz', '1.0.0')
            True

        """
        dst_path = utils.check_path(dst_path)
        version = utils.check_version(version)
        src_root = audeer.path(src_root)

        if tmp_root is not None:
            tmp_root = audeer.path(tmp_root)
            if not os.path.exists(tmp_root):
                utils.raise_file_not_found_error(tmp_root)

        with tempfile.TemporaryDirectory(dir=tmp_root) as tmp:

            archive = audeer.path(tmp, os.path.basename(dst_path))
            audeer.create_archive(
                src_root,
                files,
                archive,
                verbose=verbose,
            )

            self.put_file(
                archive,
                dst_path,
                version,
                verbose=verbose,
            )

    def _put_file(
            self,
            src_path: str,
            dst_path: str,
            version: str,
            checksum: str,
            verbose: bool,
    ):  # pragma: no cover
        r"""Put file to backend."""
        raise NotImplementedError()

    def put_file(
            self,
            src_path: str,
            dst_path: str,
            version: str,
            *,
            verbose: bool = False,
    ):
        r"""Put file on backend.

        The operation is silently skipped,
        if a file with the same checksum
        already exists on the backend.

        Args:
            src_path: path to local file
            dst_path: path to file on backend
            version: version string
            verbose: show debug messages

        Returns:
            file path on backend

        Raises:
            BackendError: if an error is raised on the backend
            FileNotFoundError: if ``src_path`` does not exist
            IsADirectoryError: if ``src_path`` is a folder
            ValueError: if ``dst_path`` does not start with ``'/'`` or
                does not match ``'[A-Za-z0-9/._-]+'``
            ValueError: if ``version`` is empty or
                does not match ``'[A-Za-z0-9._-]+'``

        Examples:
            >>> backend.exists('/sub/f.ext', '3.0.0')
            False
            >>> backend.put_file('src.pth', '/sub/f.ext', '3.0.0')
            >>> backend.exists('/sub/f.ext', '3.0.0')
            True

        """
        dst_path = utils.check_path(dst_path)
        version = utils.check_version(version)

        if not os.path.exists(src_path):
            utils.raise_file_not_found_error(src_path)
        elif os.path.isdir(src_path):
            raise utils.raise_is_a_directory(src_path)

        checksum = audeer.md5(src_path)

        # skip if file with same checksum already exists
        if (
            not self.exists(dst_path, version)
            or self.checksum(dst_path, version) != checksum
        ):
            utils.call_function_on_backend(
                self._put_file,
                src_path,
                dst_path,
                version,
                checksum,
                verbose,
            )

    def _remove_file(
            self,
            path: str,
            version: str,
    ):  # pragma: no cover
        r"""Remove file from backend."""
        raise NotImplementedError()

    def remove_file(
            self,
            path: str,
            version: str,
    ):
        r"""Remove file from backend.

        Args:
            path: path to file on backend
            version: version string

        Raises:
            BackendError: if an error is raised on the backend,
                e.g. ``path`` does not exist
            ValueError: if ``path`` does not start with ``'/'`` or
                does not match ``'[A-Za-z0-9/._-]+'``
            ValueError: if ``version`` is empty or
                does not match ``'[A-Za-z0-9._-]+'``

        Examples:
            >>> backend.exists('/f.ext', '1.0.0')
            True
            >>> backend.remove_file('/f.ext', '1.0.0')
            >>> backend.exists('/f.ext', '1.0.0')
            False

        """
        path = utils.check_path(path)
        version = utils.check_version(version)

        utils.call_function_on_backend(
            self._remove_file,
            path,
            version,
        )

    @property
    def sep(self) -> str:
        r"""File separator on backend."""
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

    def versions(
            self,
            path: str,
            *,
            suppress_backend_errors: bool = False,
    ) -> typing.List[str]:
        r"""Versions of a file.

        Args:
            path: path to file on backend
            suppress_backend_errors: if set to ``True``,
                silently catch errors raised on the backend
                and return an empty list

        Returns:
            list of versions in ascending order

        Raises:
            BackendError: if ``suppress_backend_errors`` is ``False``
                and an error is raised on the backend,
                e.g. ``path`` does not exist
            ValueError: if ``path`` does not start with ``'/'`` or
                does not match ``'[A-Za-z0-9/._-]+'``

        Examples:
            >>> backend.versions('/f.ext')
            ['1.0.0', '2.0.0']

        """
        paths = self.ls(path, suppress_backend_errors=suppress_backend_errors)
        vs = [v for _, v in paths]
        return vs
