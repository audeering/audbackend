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

    def __repr__(self) -> str:
        name = f'{self.__class__.__module__}.{self.__class__.__name__}'
        return str((name, self.host, self.repository))

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
            BackendError: if an error is raised on the backend
            ValueError: if ``path`` contains invalid character

        Examples:
            >>> backend.checksum('name.ext', '1.0.0')
            'd41d8cd98f00b204e9800998ecf8427e'

        """
        utils.check_path_for_allowed_chars(path)
        # if not self._exists(path, version):
        #     utils.raise_file_not_found_error(path, version=version)

        return utils.call_function_on_backend(
            self._checksum,
            path,
            version,
        )

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
    ) -> bool:
        r"""Check if file exists on backend.

        Args:
            path: path to file on backend
            version: version string

        Returns:
            ``True`` if file exists

        Raises:
            BackendError: if an error is raised on the backend
            ValueError: if ``path`` contains invalid character

        Examples:
            >>> backend.exists('name.ext', '1.0.0')
            True

        """
        utils.check_path_for_allowed_chars(path)

        return utils.call_function_on_backend(
            self._exists,
            path,
            version,
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
            BackendError: if an error is raised on the backend
            FileNotFoundError: if ``tmp_root`` does not exist
            PermissionError: if the user lacks write permissions
                for ``dst_path``
            RuntimeError: if extension of ``src_path`` is not supported
            RuntimeError: if ``src_path`` is a malformed archive
            ValueError: if ``src_path`` contains invalid character

        Examples:
            >>> dst_root = audeer.path(tmp, 'dst')
            >>> backend.get_archive('a.zip', dst_root, '1.0.0')
            ['src.pth']

        """
        utils.check_path_for_allowed_chars(src_path)

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

        Args:
            src_path: path to file on backend
            dst_path: destination path to local file
            version: version string
            verbose: show debug messages

        Returns:
            full path to local file

        Raises:
            BackendError: if an error is raised on the backend
            PermissionError: if the user lacks write permissions
                for ``dst_path``
            ValueError: if ``src_path`` contains invalid character

        Examples:
            >>> dst_path = audeer.path(tmp, 'dst.pth')
            >>> os.path.exists(dst_path)
            False
            >>> _ = backend.get_file('name.ext', dst_path, '1.0.0')
            >>> os.path.exists(dst_path)
            True

        """
        utils.check_path_for_allowed_chars(src_path)

        dst_path = audeer.safe_path(dst_path)
        dst_root = os.path.dirname(dst_path)

        audeer.mkdir(dst_root)
        if (
                not os.access(dst_root, os.W_OK) or
                (os.path.exists(dst_path) and not os.access(dst_root, os.W_OK))
        ):
            msg = f"Permission denied: '{dst_path}'"
            raise PermissionError(msg)

        utils.call_function_on_backend(
            self._get_file,
            src_path,
            dst_path,
            version,
            verbose,
        )

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
            ValueError: if joined path contains invalid character

        Examples:
            >>> backend.join('folder', 'name.ext')
            'folder/name.ext'

        """
        paths = [path] + [p for p in paths]
        # skip part if '' or None
        paths = [path for path in paths if path]
        path = self.sep.join(paths)

        utils.check_path_for_allowed_chars(path)

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
            RuntimeError: if ``path`` does not exist on backend
            ValueError: if ``path`` contains invalid character

        Examples:
            >>> backend.latest_version('name.ext')
            '2.0.0'

        """
        utils.check_path_for_allowed_chars(path)

        vs = self.versions(path)
        if not vs:
            raise RuntimeError(
                f"Cannot find a version for "
                f"'{path}' in "
                f"'{self.repository}'.",
            )

        return vs[-1]

    def _ls(
            self,
            folder: str,
    ) -> typing.List[typing.Tuple[str, str, str]]:  # pragma: no cover
        r"""List all files under folder."""
        raise NotImplementedError()

    def ls(
            self,
            folder: str = '/',
            *,
            latest_version: bool = False,
            pattern: str = None,
    ) -> typing.List[typing.Tuple[str, str]]:
        r"""List all files under folder.

        Returns a sorted list of tuples
        with path and version.
        When ``folder`` is set to the
        root of the backend (``'/'``)
        a (possibly empty) list with
        all files on the backend is returned.

        Args:
            folder: folder on backend
            latest_version: if multiple versions of a file exist,
                only include the latest
            pattern: if not ``None``,
                return only files matching the pattern string,
                see :func:`fnmatch.fnmatch`

        Returns:
            list of tuples (path, version)

        Raises:
            BackendError: if an error is raised on the backend
            FileNotFoundError: if ``folder`` does not exist
            ValueError: if ``folder`` contains invalid character

        Examples:
            >>> backend.ls()
            [('a.zip', '1.0.0'), ('a/b.ext', '1.0.0'), ('name.ext', '1.0.0'), ('name.ext', '2.0.0')]
            >>> backend.ls(pattern='*.ext')
            [('a/b.ext', '1.0.0'), ('name.ext', '1.0.0'), ('name.ext', '2.0.0')]
            >>> backend.ls(latest_version=True)
            [('a.zip', '1.0.0'), ('a/b.ext', '1.0.0'), ('name.ext', '2.0.0')]
            >>> backend.ls('a')
            [('a/b.ext', '1.0.0')]

        """  # noqa: E501
        utils.check_path_for_allowed_chars(folder)
        if not folder.endswith('/'):
            folder += '/'
        paths = utils.call_function_on_backend(self._ls, folder)
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

    def put_archive(
            self,
            src_root: str,
            files: typing.Union[str, typing.Sequence[str]],
            dst_path: str,
            version: str,
            *,
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
                Only folders and files below ``src_root``
                will be included into the archive
            files: relative path to file(s) from ``src_root``
            dst_path: path to archive on backend
            version: version string
            tmp_root: directory under which archive is temporarily created.
                Defaults to temporary directory of system
            verbose: show debug messages

        Raises:
            BackendError: if an error is raised on the backend
            FileNotFoundError: if one or more files do not exist
            FileNotFoundError: if ``tmp_root`` does not exist
            ValueError: if ``dst_path`` contains invalid character
            RuntimeError: if extension of ``dst_path`` is not supported

        Examples:
            >>> backend.exists('a.tar.gz', '1.0.0')
            False
            >>> files = ['src.pth']
            >>> backend.put_archive(tmp, files, 'name.tar.gz', '1.0.0')
            >>> backend.exists('name.tar.gz', '1.0.0')
            True

        """
        utils.check_path_for_allowed_chars(dst_path)
        src_root = audeer.safe_path(src_root)

        if isinstance(files, str):
            files = [files]

        for file in files:
            path = os.path.join(src_root, file)
            if not os.path.exists(path):
                utils.raise_file_not_found_error(path)

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
            ValueError: if ``dst_path`` contains invalid character

        Examples:
            >>> backend.exists('folder/name.ext', '3.0.0')
            False
            >>> src_path = audeer.path(tmp, 'src.pth')
            >>> backend.put_file(src_path, 'folder/name.ext', '3.0.0')
            >>> backend.exists('folder/name.ext', '3.0.0')
            True

        """
        utils.check_path_for_allowed_chars(dst_path)
        if not os.path.exists(src_path):
            utils.raise_file_not_found_error(src_path)

        # skip if file with same checksum already exists
        if not (
            self.exists(dst_path, version)
            and self.checksum(dst_path, version) == utils.md5(src_path)
        ):
            utils.call_function_on_backend(
                self._put_file,
                src_path,
                dst_path,
                version,
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
            BackendError: if an error is raised on the backend
            ValueError: if ``path`` contains invalid character

        Examples:
            >>> backend.exists('name.ext', '1.0.0')
            True
            >>> backend.remove_file('name.ext', '1.0.0')
            >>> backend.exists('name.ext', '1.0.0')
            False

        """
        utils.check_path_for_allowed_chars(path)

        utils.call_function_on_backend(
            self._remove_file,
            path,
            version,
        )

    @property
    def sep(self) -> str:
        r"""File separator on backend."""
        return '/'

    def split(
            self,
            path: str,
    ) -> typing.Tuple[str, str]:
        r"""Split path on backend into folder and basename.

        Args:
            path: path containing :attr:`Backend.sep` as separator

        Returns:
            tuple containing (folder, basename)

        Raises:
            ValueError: if ``path`` contains invalid character

        Examples:
            >>> backend.split('folder/name.ext')
            ('folder', 'name.ext')

        """
        utils.check_path_for_allowed_chars(path)

        folder = self.sep.join(path.split(self.sep)[:-1])
        basename = path.split(self.sep)[-1]

        return folder, basename

    def _versions(
            self,
            path: str,
    ) -> typing.List[str]:  # pragma: no cover
        r"""Versions of a file."""
        raise NotImplementedError()

    def versions(
            self,
            path: str,
    ) -> typing.List[str]:
        r"""Versions of a file.

        Args:
            path: path to file on backend

        Returns:
            list of versions in ascending order

        Raises:
            BackendError: if an error is raised on the backend
            ValueError: if ``path`` contains invalid character

        Examples:
            >>> backend.versions('name.ext')
            ['1.0.0', '2.0.0']

        """
        utils.check_path_for_allowed_chars(path)

        vs = utils.call_function_on_backend(
            self._versions,
            path,
        )

        return audeer.sort_versions(vs)
