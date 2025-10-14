from collections.abc import Sequence
import fnmatch
import os

import audeer

from audbackend.core import utils
from audbackend.core.backend.base import Base as Backend
from audbackend.core.errors import BackendError
from audbackend.core.interface.base import Base


class Versioned(Base):
    r"""Interface for versioned file access.

    Use this interface if you care about versioning.
    For each file on the backend path one or more versions may exist.

    Args:
        backend: backend object

    ..
        >>> import audbackend
        >>> import audeer

    Examples:
        >>> host = audeer.mkdir("host")
        >>> audbackend.backend.FileSystem.create(host, "repo")
        >>> backend = audbackend.backend.FileSystem(host, "repo")
        >>> backend.open()
        >>> interface = Versioned(backend)
        >>> file = "src.txt"
        >>> interface.put_archive(".", "/sub/archive.zip", "1.0.0", files=[file])
        >>> for version in ["1.0.0", "2.0.0"]:
        ...     interface.put_file(file, "/file.txt", version)
        >>> interface.ls()
        [('/file.txt', '1.0.0'), ('/file.txt', '2.0.0'), ('/sub/archive.zip', '1.0.0')]
        >>> interface.get_file("/file.txt", "dst.txt", "2.0.0")
        '...dst.txt'

    """

    def __init__(
        self,
        backend: Backend,
    ):
        super().__init__(backend)

    def checksum(
        self,
        path: str,
        version: str,
    ) -> str:
        r"""MD5 checksum for file on backend.

        Args:
            path: path to file on backend
            version: version string

        Returns:
            MD5 checksum

        Raises:
            BackendError: if an error is raised on the backend,
                e.g. ``path`` does not exist
            ValueError: if ``path`` does not start with ``'/'``,
                ends on ``'/'``,
                or does not match ``'[A-Za-z0-9/._-]+'``
            ValueError: if ``version`` is empty or
                does not match ``'[A-Za-z0-9._-]+'``
            RuntimeError: if backend was not opened

        ..
            >>> interface = Versioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> import audeer
            >>> audeer.md5(file)
            'd41d8cd98f00b204e9800998ecf8427e'
            >>> interface.put_file(file, "/file.txt", "1.0.0")
            >>> interface.checksum("/file.txt", "1.0.0")
            'd41d8cd98f00b204e9800998ecf8427e'

        """
        path_with_version = self._path_with_version(path, version)
        return self.backend.checksum(path_with_version)

    def copy_file(
        self,
        src_path: str,
        dst_path: str,
        *,
        version: str = None,
        validate: bool = False,
        verbose: bool = False,
    ):
        r"""Copy file on backend.

        If ``version`` is ``None``
        all versions of ``src_path``
        will be copied.

        If ``dst_path`` exists
        and has a different checksum,
        it is overwritten.
        Otherwise,
        the operation is silently skipped.

        If ``validate`` is set to ``True``,
        a final check is performed to assert that
        ``src_path`` and ``dst_path``
        have the same checksum.
        If it fails,
        ``dst_path`` is removed and
        an :class:`InterruptedError` is raised.

        Args:
            src_path: source path to file on backend
            dst_path: destination path to file on backend
            validate: verify file was successfully copied
            version: version string
            verbose: show debug messages

        Raises:
            BackendError: if an error is raised on the backend
            InterruptedError: if validation fails
            ValueError: if ``src_path`` or ``dst_path``
                does not start with ``'/'``,
                ends on ``'/'``,
                or does not match ``'[A-Za-z0-9/._-]+'``
            ValueError: if ``version`` is empty or
                does not match ``'[A-Za-z0-9._-]+'``
            RuntimeError: if backend was not opened

        ..
            >>> interface = Versioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> interface.put_file(file, "/file.txt", "1.0.0")
            >>> interface.exists("/copy.txt", "1.0.0")
            False
            >>> interface.copy_file("/file.txt", "/copy.txt", version="1.0.0")
            >>> interface.exists("/copy.txt", "1.0.0")
            True

        """
        if version is None:
            versions = self.versions(src_path)
        else:
            versions = [version]

        for version in versions:
            src_path_with_version = self._path_with_version(src_path, version)
            dst_path_with_version = self._path_with_version(dst_path, version)
            self.backend.copy_file(
                src_path_with_version,
                dst_path_with_version,
                validate=validate,
                verbose=verbose,
            )

    def date(
        self,
        path: str,
        version: str,
    ) -> str:
        r"""Last modification date of file on backend.

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
            ValueError: if ``path`` does not start with ``'/'``,
                ends on ``'/'``,
                or does not match ``'[A-Za-z0-9/._-]+'``
            ValueError: if ``version`` is empty or
                does not match ``'[A-Za-z0-9._-]+'``
            RuntimeError: if backend was not opened

        ..
            >>> interface = Versioned(filesystem)
            >>> interface.date = mock_date

        Examples:
            >>> file = "src.txt"
            >>> interface.put_file(file, "/file.txt", "1.0.0")
            >>> interface.date("/file.txt", "1.0.0")
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
            ValueError: if ``path`` does not start with ``'/'``,
                ends on ``'/'``,
                or does not match ``'[A-Za-z0-9/._-]+'``
            ValueError: if ``version`` is empty or
                does not match ``'[A-Za-z0-9._-]+'``
            RuntimeError: if backend was not opened

        ..
            >>> interface = Versioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> interface.exists("/file.txt", "1.0.0")
            False
            >>> interface.put_file(file, "/file.txt", "1.0.0")
            >>> interface.exists("/file.txt", "1.0.0")
            True

        """
        path_with_version = self._path_with_version(path, version)
        return self.backend.exists(
            path_with_version,
            suppress_backend_errors=suppress_backend_errors,
        )

    def get_archive(
        self,
        src_path: str,
        dst_root: str,
        version: str,
        *,
        tmp_root: str = None,
        validate: bool = False,
        verbose: bool = False,
    ) -> list[str]:
        r"""Get archive from backend and extract.

        The archive type is derived from the extension of ``src_path``.
        See :func:`audeer.extract_archive` for supported extensions.

        If ``dst_root`` does not exist,
        it is created.

        If ``validate`` is set to ``True``,
        a final check is performed to assert that
        ``src_path`` and the retrieved archive
        have the same checksum.
        If it fails,
        the retrieved archive is removed and
        an :class:`InterruptedError` is raised.

        Args:
            src_path: path to archive on backend
            dst_root: local destination directory
            version: version string
            tmp_root: directory under which archive is temporarily extracted.
                Defaults to temporary directory of system
            validate: verify archive was successfully
                retrieved from the backend
            verbose: show debug messages

        Returns:
            extracted files

        Raises:
            BackendError: if an error is raised on the backend,
                e.g. ``src_path`` does not exist
            FileNotFoundError: if ``tmp_root`` does not exist
            InterruptedError: if validation fails
            NotADirectoryError: if ``dst_root`` is not a directory
            PermissionError: if the user lacks write permissions
                for ``dst_path``
            RuntimeError: if extension of ``src_path`` is not supported
                or ``src_path`` is a malformed archive
            ValueError: if ``src_path`` does not start with ``'/'``,
                ends on ``'/'``,
                or does not match ``'[A-Za-z0-9/._-]+'``
            ValueError: if ``version`` is empty or
                does not match ``'[A-Za-z0-9._-]+'``
            RuntimeError: if backend was not opened

        ..
            >>> interface = Versioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> interface.put_archive(".", "/sub/archive.zip", "1.0.0", files=[file])
            >>> os.remove(file)
            >>> interface.get_archive("/sub/archive.zip", ".", "1.0.0")
            ['src.txt']

        """
        src_path_with_version = self._path_with_version(src_path, version)
        return self.backend.get_archive(
            src_path_with_version,
            dst_root,
            tmp_root=tmp_root,
            validate=validate,
            verbose=verbose,
        )

    def get_file(
        self,
        src_path: str,
        dst_path: str,
        version: str,
        *,
        validate: bool = False,
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

        If ``validate`` is set to ``True``,
        a final check is performed to assert that
        ``src_path`` and ``dst_path``
        have the same checksum.
        If it fails,
        ``dst_path`` is removed and
        an :class:`InterruptedError` is raised.

        Args:
            src_path: path to file on backend
            dst_path: destination path to local file
            version: version string
            validate: verify file was successfully
                retrieved from the backend
            verbose: show debug messages

        Returns:
            full path to local file

        Raises:
            BackendError: if an error is raised on the backend,
                e.g. ``src_path`` does not exist
            InterruptedError: if validation fails
            IsADirectoryError: if ``dst_path`` points to an existing folder
            PermissionError: if the user lacks write permissions
                for ``dst_path``
            ValueError: if ``src_path`` does not start with ``'/'``,
                ends on ``'/'``,
                or does not match ``'[A-Za-z0-9/._-]+'``
            ValueError: if ``version`` is empty or
                does not match ``'[A-Za-z0-9._-]+'``
            RuntimeError: if backend was not opened

        ..
            >>> interface = Versioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> interface.put_file(file, "/file.txt", "1.0.0")
            >>> interface.get_file("/file.txt", "dst.txt", "1.0.0")
            '...dst.txt'

        """
        src_path_with_version = self._path_with_version(src_path, version)
        return self.backend.get_file(
            src_path_with_version,
            dst_path,
            validate=validate,
            verbose=verbose,
        )

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
            ValueError: if ``path`` does not start with ``'/'``,
                ends on ``'/'``,
                or does not match ``'[A-Za-z0-9/._-]+'``
            RuntimeError: if backend was not opened

         ..
            >>> interface = Versioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> interface.put_file(file, "/file.txt", "1.0.0")
            >>> interface.put_file(file, "/file.txt", "2.0.0")
            >>> interface.latest_version("/file.txt")
            '2.0.0'

        """
        vs = self.versions(path)
        return vs[-1]

    def ls(
        self,
        path: str = "/",
        *,
        latest_version: bool = False,
        pattern: str = None,
        suppress_backend_errors: bool = False,
    ) -> list[tuple[str, str]]:
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
            RuntimeError: if backend was not opened

        ..
            >>> interface = Versioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> interface.put_file(file, "/file.txt", "1.0.0")
            >>> interface.put_file(file, "/file.txt", "2.0.0")
            >>> interface.put_archive(".", "/sub/archive.zip", "1.0.0", files=[file])
            >>> interface.ls()
            [('/file.txt', '1.0.0'), ('/file.txt', '2.0.0'), ('/sub/archive.zip', '1.0.0')]
            >>> interface.ls(latest_version=True)
            [('/file.txt', '2.0.0'), ('/sub/archive.zip', '1.0.0')]
            >>> interface.ls("/file.txt")
            [('/file.txt', '1.0.0'), ('/file.txt', '2.0.0')]
            >>> interface.ls(pattern="*.txt")
            [('/file.txt', '1.0.0'), ('/file.txt', '2.0.0')]
            >>> interface.ls(pattern="archive.*")
            [('/sub/archive.zip', '1.0.0')]
            >>> interface.ls("/sub/")
            [('/sub/archive.zip', '1.0.0')]

        """  # noqa: E501
        if path.endswith("/"):  # find files under sub-path
            paths = self.backend.ls(
                path,
                suppress_backend_errors=suppress_backend_errors,
            )

        else:  # find versions of path
            root, file = self.split(path)

            paths = self.backend.ls(
                root,
                suppress_backend_errors=suppress_backend_errors,
            )

            # filter for '/root/version/file'
            depth = root.count("/") + 1
            paths = [
                p
                for p in paths
                if (p.count("/") == depth and os.path.basename(p) == file)
            ]

            if not paths and not suppress_backend_errors:
                # since the backend does no longer raise an error
                # if the path does not exist
                # we have to do it
                try:
                    utils.raise_file_not_found_error(path)
                except FileNotFoundError as ex:
                    raise BackendError(ex)

        if pattern:
            paths = [p for p in paths if fnmatch.fnmatch(os.path.basename(p), pattern)]

        if not paths:
            return []

        paths_and_versions = []
        for p in paths:
            tokens = p.split(self.sep)

            name = tokens[-1]
            version = tokens[-2]

            if version:
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

    def move_file(
        self,
        src_path: str,
        dst_path: str,
        *,
        version: str = None,
        validate: bool = False,
        verbose: bool = False,
    ):
        r"""Move file on backend.

        If ``version`` is ``None``
        all versions of ``src_path``
        will be moved.

        If ``dst_path`` exists
        and has a different checksum,
        it is overwritten.
        Otherwise,
        ``src_path``
        is removed and the operation silently skipped.

        If ``validate`` is set to ``True``,
        a final check is performed to assert that
        ``src_path`` and ``dst_path``
        have the same checksum.
        If it fails,
        ``dst_path`` is removed and
        an :class:`InterruptedError` is raised.
        To ensure ``src_path`` still exists in this case
        it is first copied and only removed
        when the check has successfully passed.

        Args:
            src_path: source path to file on backend
            dst_path: destination path to file on backend
            version: version string
            validate: verify file was successfully moved
            verbose: show debug messages

        Raises:
            BackendError: if an error is raised on the backend
            InterruptedError: if validation fails
            ValueError: if ``src_path`` or ``dst_path``
                does not start with ``'/'``,
                ends on ``'/'``,
                or does not match ``'[A-Za-z0-9/._-]+'``
            ValueError: if ``version`` is empty or
                does not match ``'[A-Za-z0-9._-]+'``
            RuntimeError: if backend was not opened

        ..
            >>> interface = Versioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> interface.put_file(file, "/file.txt", "1.0.0")
            >>> interface.exists("/move.txt", "1.0.0")
            False
            >>> interface.move_file("/file.txt", "/move.txt", version="1.0.0")
            >>> interface.exists("/move.txt", "1.0.0")
            True
            >>> interface.exists("/file.txt", "1.0.0")
            False

        """
        if version is None:
            versions = self.versions(src_path)
        else:
            versions = [version]

        for version in versions:
            src_path_with_version = self._path_with_version(src_path, version)
            dst_path_with_version = self._path_with_version(dst_path, version)
            self.backend.move_file(
                src_path_with_version,
                dst_path_with_version,
                validate=validate,
                verbose=verbose,
            )

    def owner(
        self,
        path: str,
        version: str,
    ) -> str:
        r"""Owner of file on backend.

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
            ValueError: if ``path`` does not start with ``'/'``,
                ends on ``'/'``,
                or does not match ``'[A-Za-z0-9/._-]+'``
            ValueError: if ``version`` is empty or
                does not match ``'[A-Za-z0-9._-]+'``
            RuntimeError: if backend was not opened

        ..
            >>> interface = Versioned(filesystem)
            >>> interface.owner = mock_owner

        Examples:
            >>> file = "src.txt"
            >>> interface.put_file(file, "/file.txt", "1.0.0")
            >>> interface.owner("/file.txt", "1.0.0")
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
        files: str | Sequence[str] = None,
        tmp_root: str = None,
        validate: bool = False,
        verbose: bool = False,
    ):
        r"""Create archive and put on backend.

        The archive type is derived from the extension of ``dst_path``.
        See :func:`audeer.create_archive` for supported extensions.

        The operation is silently skipped,
        if an archive with the same checksum
        already exists on the backend.

        If ``validate`` is set to ``True``,
        a final check is performed to assert that
        the local archive and ``dst_path``
        have the same checksum.
        If it fails,
        ``dst_path`` is removed and
        an :class:`InterruptedError` is raised.

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
            validate: verify archive was successfully
                put on the backend
            verbose: show debug messages

        Raises:
            BackendError: if an error is raised on the backend
            FileNotFoundError: if ``src_root``,
                ``tmp_root``,
                or one or more ``files`` do not exist
            InterruptedError: if validation fails
            NotADirectoryError: if ``src_root`` is not a folder
            RuntimeError: if ``dst_path`` does not end with
                ``zip`` or ``tar.gz``
                or a file in ``files`` is not below ``root``
            ValueError: if ``dst_path`` does not start with ``'/'``,
                ends on ``'/'``,
                or does not match ``'[A-Za-z0-9/._-]+'``
            ValueError: if ``version`` is empty or
                does not match ``'[A-Za-z0-9._-]+'``
            RuntimeError: if backend was not opened

        ..
            >>> interface = Versioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> interface.exists("/sub/archive.tar.gz", "1.0.0")
            False
            >>> interface.put_archive(".", "/sub/archive.tar.gz", "1.0.0")
            >>> interface.exists("/sub/archive.tar.gz", "1.0.0")
            True

        """
        dst_path_with_version = self._path_with_version(dst_path, version)
        self.backend.put_archive(
            src_root,
            dst_path_with_version,
            files=files,
            tmp_root=tmp_root,
            validate=validate,
            verbose=verbose,
        )

    def put_file(
        self,
        src_path: str,
        dst_path: str,
        version: str,
        *,
        validate: bool = False,
        verbose: bool = False,
    ):
        r"""Put file on backend.

        The operation is silently skipped,
        if a file with the same checksum
        already exists on the backend.

        If ``validate`` is set to ``True``,
        a final check is performed to assert that
        ``src_path`` and ``dst_path``
        have the same checksum.
        If it fails,
        ``dst_path`` is removed and
        an :class:`InterruptedError` is raised.

        Args:
            src_path: path to local file
            dst_path: path to file on backend
            version: version string
            validate: verify file was successfully
                put on the backend
            verbose: show debug messages

        Returns:
            file path on backend

        Raises:
            BackendError: if an error is raised on the backend
            FileNotFoundError: if ``src_path`` does not exist
            InterruptedError: if validation fails
            IsADirectoryError: if ``src_path`` is a folder
            ValueError: if ``dst_path`` does not start with ``'/'``,
                ends on ``'/'``,
                or does not match ``'[A-Za-z0-9/._-]+'``
            ValueError: if ``version`` is empty or
                does not match ``'[A-Za-z0-9._-]+'``
            RuntimeError: if backend was not opened

        ..
            >>> interface = Versioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> interface.exists("/file.txt", "3.0.0")
            False
            >>> interface.put_file(file, "/file.txt", "3.0.0")
            >>> interface.exists("/file.txt", "3.0.0")
            True

        """
        dst_path_with_version = self._path_with_version(dst_path, version)
        return self.backend.put_file(
            src_path,
            dst_path_with_version,
            validate=validate,
            verbose=verbose,
        )

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
            ValueError: if ``path`` does not start with ``'/'``,
                ends on ``'/'``,
                or does not match ``'[A-Za-z0-9/._-]+'``
            ValueError: if ``version`` is empty or
                does not match ``'[A-Za-z0-9._-]+'``
            RuntimeError: if backend was not opened

        ..
            >>> interface = Versioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> interface.put_file(file, "/file.txt", "1.0.0")
            >>> interface.exists("/file.txt", "1.0.0")
            True
            >>> interface.remove_file("/file.txt", "1.0.0")
            >>> interface.exists("/file.txt", "1.0.0")
            False

        """
        path_with_version = self._path_with_version(path, version)
        self.backend.remove_file(path_with_version)

    def versions(
        self,
        path: str,
        *,
        suppress_backend_errors: bool = False,
    ) -> list[str]:
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
            ValueError: if ``path`` does not start with ``'/'``,
                ends on ``'/'``,
                or does not match ``'[A-Za-z0-9/._-]+'``
            RuntimeError: if backend was not opened

        ..
            >>> interface = Versioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> interface.put_file(file, "/file.txt", "1.0.0")
            >>> interface.put_file(file, "/file.txt", "2.0.0")
            >>> interface.versions("/file.txt")
            ['1.0.0', '2.0.0']

        """
        utils.check_path(path)

        paths = self.ls(path, suppress_backend_errors=suppress_backend_errors)
        vs = [v for _, v in paths]

        return vs

    def _path_with_version(
        self,
        path: str,
        version: str,
    ) -> str:
        r"""Convert to versioned path.

        <root>/<base><ext>
        ->
        <root>/<version>/<base><ext>

        """
        path = utils.check_path(path)
        version = utils.check_version(version)
        root, name = self.split(path)
        path = self.join(root, version, name)
        return path
