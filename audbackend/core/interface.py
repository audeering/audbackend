import errno
import os
import re
import tempfile
import typing

import audeer

from audbackend.core import utils
from audbackend.core.backend import Backend
from audbackend.core.backend import Base
from audbackend.core.errors import BackendError


class Interface(Base):
    r"""Backend interface.

    Args:
        backend: backend object

    """
    def __init__(
            self,
            backend: Backend,
    ):
        self._backend = backend

    @property
    def backend(self) -> Backend:
        r"""Backend object.

        Returns: backend object

        """
        return self._backend


class Unversioned(Interface):
    r"""Unversioned backend interface."""

    def checksum(
            self,
            path: str,
    ) -> str:
        r"""Get MD5 checksum for file on backend.

        Args:
            path: path to file on backend

        Returns:
            MD5 checksum

        Raises:
            BackendError: if an error is raised on the backend,
                e.g. ``path`` does not exist
            ValueError: if ``path`` does not start with ``'/'`` or
                does not match ``'[A-Za-z0-9/._-]+'``

        Examples:
            >>> backend.checksum('/f.ext')
            'd41d8cd98f00b204e9800998ecf8427e'

        """
        return self.backend.checksum(path)

    def date(
            self,
            path: str,
    ) -> str:
        r"""Last modification date of file on backend.

        If the date cannot be determined,
        an empty string is returned.

        Args:
            path: path to file on backend

        Returns:
            date in format ``'yyyy-mm-dd'``

        Raises:
            BackendError: if an error is raised on the backend,
                e.g. ``path`` does not exist
            ValueError: if ``path`` does not start with ``'/'`` or
                does not match ``'[A-Za-z0-9/._-]+'``

        Examples:
              >>> backend.date('/f.ext')
              '1991-02-20'

        """
        return self.backend.date(path)

    def exists(
            self,
            path: str,
            *,
            suppress_backend_errors: bool = False,
    ) -> bool:
        r"""Check if file exists on backend.

        Args:
            path: path to file on backend
            suppress_backend_errors: if set to ``True``,
                silently catch errors raised on the backend
                and return ``False``

        Returns:
            ``True`` if file exists

        Raises:
            BackendError: if ``suppress_backend_errors`` is ``False``
                and an error is raised on the backend,
                e.g. due to a connection timeout
            ValueError: if ``path`` does not start with ``'/'`` or
                does not match ``'[A-Za-z0-9/._-]+'``
            ValueError: if ``version`` is empty or
                does not match ``'[A-Za-z0-9._-]+'``

        Examples:
            >>> backend.exists('/f.ext')
            True

        """
        return self.backend.exists(path, suppress_backend_errors=suppress_backend_errors)

    def get_archive(
            self,
            src_path: str,
            dst_root: str,
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

        Examples:
            >>> backend.get_archive('/a.zip', '.')
            ['src.pth']

        """
        src_path = utils.check_path(src_path)

        with tempfile.TemporaryDirectory(dir=tmp_root) as tmp:

            tmp_root = audeer.path(tmp, os.path.basename(dst_root))
            local_archive = os.path.join(
                tmp_root,
                os.path.basename(src_path),
            )
            self.backend.get_file(
                src_path,
                local_archive,
                verbose=verbose,
            )

            return audeer.extract_archive(
                local_archive,
                dst_root,
                verbose=verbose,
            )

    def get_file(
            self,
            src_path: str,
            dst_path: str,
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

        Examples:
            >>> os.path.exists('dst.pth')
            False
            >>> _ = backend.get_file('/f.ext', 'dst.pth')
            >>> os.path.exists('dst.pth')
            True

        """
        return self.backend.get_file(src_path, dst_path, verbose=verbose)

    def ls(
            self,
            path: str = '/',
            *,
            pattern: str = None,
            suppress_backend_errors: bool = False,
    ) -> typing.List[str]:
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
            ['/a.zip', /a/b.ext', '/f.ext']
            >>> backend.ls('/f.ext')
            ['/f.ext']
            >>> backend.ls(pattern='*.ext')
            ['/a/b.ext', '/f.ext', '/f.ext']
            >>> backend.ls(pattern='b.*')
            ['/a/b.ext']
            >>> backend.ls('/a/')
            ['/a/b.ext']

        """  # noqa: E501
        return self.backend.ls(path, pattern=pattern, suppress_backend_errors=suppress_backend_errors)

    def owner(
            self,
            path: str,
    ) -> str:
        r"""Owner of file on backend.

        If the owner of the file
        cannot be determined,
        an empty string is returned.

        Args:
            path: path to file on backend

        Returns:
            owner

        Raises:
            BackendError: if an error is raised on the backend,
                e.g. ``path`` does not exist
            ValueError: if ``path`` does not start with ``'/'`` or
                does not match ``'[A-Za-z0-9/._-]+'``

        Examples:
              >>> backend.owner('/f.ext')
              'doctest'

        """
        return self.backend.owner(path)

    def put_archive(
            self,
            src_root: str,
            dst_path: str,
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

        Examples:
            >>> backend.exists('/a.tar.gz')
            False
            >>> backend.put_archive('.', '/a.tar.gz')
            >>> backend.exists('/a.tar.gz')
            True

        """
        dst_path = utils.check_path(dst_path)
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

            self.backend.put_file(
                archive,
                dst_path,
                verbose=verbose,
            )

    def put_file(
            self,
            src_path: str,
            dst_path: str,
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
            verbose: show debug messages

        Returns:
            file path on backend

        Raises:
            BackendError: if an error is raised on the backend
            FileNotFoundError: if ``src_path`` does not exist
            IsADirectoryError: if ``src_path`` is a folder
            ValueError: if ``dst_path`` does not start with ``'/'`` or
                does not match ``'[A-Za-z0-9/._-]+'``

        Examples:
            >>> backend.exists('/sub/f.ext')
            False
            >>> backend.put_file('src.pth', '/sub/f.ext')
            >>> backend.exists('/sub/f.ext')
            True

        """
        self.backend.put_file(src_path, dst_path, verbose=verbose)

    def remove_file(
            self,
            path: str,
    ):
        r"""Remove file from backend.

        Args:
            path: path to file on backend

        Raises:
            BackendError: if an error is raised on the backend,
                e.g. ``path`` does not exist
            ValueError: if ``path`` does not start with ``'/'`` or
                does not match ``'[A-Za-z0-9/._-]+'``

        Examples:
            >>> backend.exists('/f.ext')
            True
            >>> backend.remove_file('/f.ext')
            >>> backend.exists('/f.ext')
            False

        """
        self.backend.remove_file(path)


class Versioned(Interface):
    r"""Versioned backend interface."""

    def __init__(
            self,
            backend: Backend,
    ):
        super().__init__(backend)

        # to support legacy file structure
        # see _use_legacy_file_structure()
        self._legacy_extensions = []
        self._legacy_file_structure = False
        self._legacy_file_structure_regex = False

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
        path_with_version = self._path_with_version(path, version)

        return self.backend.checksum(path_with_version)

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
        path_with_version = self._path_with_version(path, version)

        return self.backend.date(path_with_version)

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
                e.g. due to a connection timeout
            ValueError: if ``path`` does not start with ``'/'`` or
                does not match ``'[A-Za-z0-9/._-]+'``
            ValueError: if ``version`` is empty or
                does not match ``'[A-Za-z0-9._-]+'``

        Examples:
            >>> backend.exists('/f.ext', '1.0.0')
            True

        """
        path_with_version = self._path_with_version(path, version)

        return self.backend.exists(path_with_version, suppress_backend_errors=suppress_backend_errors)

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
        src_path_with_version = self._path_with_version(src_path, version)

        return self.backend.get_file(src_path_with_version, dst_path, verbose=verbose)

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
        vs = self.versions(path)
        return vs[-1]

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
            >>> backend.ls(pattern='b.*')
            [('/a/b.ext', '1.0.0')]
            >>> backend.ls('/a/')
            [('/a/b.ext', '1.0.0')]

        """  # noqa: E501
        if path.endswith('/'):  # find files under sub-path

            paths = self.backend.ls(path, pattern=pattern, suppress_backend_errors=suppress_backend_errors)

        else:  # find versions of path

            root, file = self.split(path)

            paths = self.backend.ls(root, pattern=pattern, suppress_backend_errors=suppress_backend_errors)

            # filter for '/root/version/file'
            if self._legacy_file_structure:
                depth = root.count('/') + 2
                name, ext = self._legacy_split_ext(file)
                match = re.compile(rf'{name}-\d+\.\d+.\d+{ext}')
                paths = [
                    p for p in paths
                    if (
                            p.count('/') == depth and
                            match.match(os.path.basename(p))
                    )
                ]
            else:
                depth = root.count('/') + 1
                paths = [
                    p for p in paths
                    if (
                            p.count('/') == depth and
                            os.path.basename(p) == file
                    )
                ]

            if not paths and not suppress_backend_errors:
                # since the backend does no longer raise an error
                # if the path does not exist
                # we have to do it
                ex = FileNotFoundError(
                    errno.ENOENT,
                    os.strerror(errno.ENOENT),
                    path,
                )
                raise BackendError(ex)

        if not paths:
            return []

        paths_and_versions = []
        for p in paths:

            tokens = p.split(self.sep)

            name = tokens[-1]
            version = tokens[-2]

            if not version:
                continue

            if self._legacy_file_structure:
                base = tokens[-3]
                ext = name[len(base) + len(version) + 1:]
                name = f'{base}{ext}'
                path = self.sep.join(tokens[:-3])
            else:
                path = self.sep.join(tokens[:-2])

            path = self.sep + path
            path = self.join(path, name)

            paths_and_versions.append((path, version))

        paths_and_versions = sorted(paths_and_versions)

        if latest_version:
            # d[path] = ['1.0.0', '2.0.0']
            d = {}
            for p, v in paths_and_versions:
                if p not in d:
                    d[p] = []
                d[p].append(v)
            # d[path] = '2.0.0'
            for p, vs in d.items():
                d[p] = audeer.sort_versions(vs)[-1]
            # [(path, '2.0.0')]
            paths_and_versions = [(p, v) for p, v in d.items()]

        return paths_and_versions

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
        path_with_version = self._path_with_version(path, version)

        return self.backend.owner(path_with_version)

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
        dst_path_with_version = self._path_with_version(dst_path, version)

        return self.backend.put_file(src_path, dst_path_with_version, verbose=verbose)

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
        path_with_version = self._path_with_version(path, version)

        self.backend.remove_file(path_with_version)

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

    def _legacy_split_ext(
            self,
            name: str,
    ) -> typing.Tuple[str, str]:
        r"""Split name into basename and extension."""
        ext = None
        for custom_ext in self._legacy_extensions:
            # check for custom extension
            # ensure basename is not empty
            if self._legacy_file_structure_regex:
                pattern = rf'\.({custom_ext})$'
                match = re.search(pattern, name[1:])
                if match:
                    ext = match.group(1)
            elif name[1:].endswith(f'.{custom_ext}'):
                ext = custom_ext
        if ext is None:
            # if no custom extension is found
            # use last string after dot
            ext = audeer.file_extension(name)

        base = audeer.replace_file_extension(name, '', ext=ext)

        if ext:
            ext = f'.{ext}'

        return base, ext

    def _path_with_version(
            self,
            path: str,
            version: str,
    ) -> str:
        r"""Convert to versioned path.

        <root>/<base><ext>
        ->
        <root>/<version>/<base><ext>

        or legacy:

        <root>/<base><ext>
        ->
        <root>/<base>/<version>/<base>-<version><ext>

        """
        path = utils.check_path(path)
        version = utils.check_version(version)

        root, name = self.split(path)

        if self._legacy_file_structure:
            base, ext = self._legacy_split_ext(name)
            path = self.join(root, base, version, f'{base}-{version}{ext}')
        else:
            path = self.join(root, version, name)

        return path

    def _use_legacy_file_structure(
            self,
            *,
            extensions: typing.List[str] = None,
            regex: bool = False,
    ):
        r"""Use legacy file structure.

        Stores files under
        ``'.../<name-wo-ext>/<version>/<name-wo-ext>-<version>.<ext>'``
        instead of
        ``'.../<version>/<name>'``.
        By default,
        the extension
        ``<ext>``
        is set to the string after the last dot.
        I.e.,
        the backend path
        ``'.../file.tar.gz'``
        will translate into
        ``'.../file.tar/1.0.0/file.tar-1.0.0.gz'``.
        However,
        by passing a list with custom extensions
        it is possible to overwrite
        the default behavior
        for certain extensions.
        E.g.,
        with
        ``backend._use_legacy_file_structure(extensions=['tar.gz'])``
        it is ensured that
        ``'tar.gz'``
        will be recognized as an extension
        and the backend path
        ``'.../file.tar.gz'``
        will then translate into
        ``'.../file/1.0.0/file-1.0.0.tar.gz'``.
        If ``regex`` is set to ``True``,
        the extensions are treated as regular expressions.
        E.g.
        with
        ``backend._use_legacy_file_structure(extensions=['\d+.tar.gz'],
        regex=True)``
        the backend path
        ``'.../file.99.tar.gz'``
        will translate into
        ``'.../file/1.0.0/file-1.0.0.99.tar.gz'``.

        """
        self._legacy_file_structure = True
        self._legacy_extensions = extensions or []
        self._legacy_file_structure_regex = regex
