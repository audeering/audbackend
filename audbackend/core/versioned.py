import fnmatch
import os
import re
import typing

import audeer

from audbackend.core import utils
from audbackend.core.base import AbstractBackend
from audbackend.core.errors import BackendError


class Versioned(AbstractBackend):
    r"""Interface for versioned file access.

    Use this backend if you care about versioning.
    For each file on the backend path one or more versions may exist.

    Args:
        backend: backend object

    .. Prepare backend for docstring examples

    Examples:
        >>> file = "src.txt"
        >>> backend = Versioned(filesystem)
        >>> backend.put_archive(".", "/sub/archive.zip", "1.0.0", files=[file])
        >>> for version in ["1.0.0", "2.0.0"]:
        ...     backend.put_file(file, "/file.txt", version)
        >>> backend.ls()
        [('/file.txt', '1.0.0'), ('/file.txt', '2.0.0'), ('/sub/archive.zip', '1.0.0')]
        >>> backend.get_file("/file.txt", "dst.txt", "2.0.0")
        '...dst.txt'

    """

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
            >>> backend = Versioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> import audeer
            >>> audeer.md5(file)
            'd41d8cd98f00b204e9800998ecf8427e'
            >>> backend.put_file(file, "/file.txt", "1.0.0")
            >>> backend.checksum("/file.txt", "1.0.0")
            'd41d8cd98f00b204e9800998ecf8427e'

        """
        path = self.path(path, version)
        return self._checksum(path)

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
            >>> backend = Versioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> backend.put_file(file, "/file.txt", "1.0.0")
            >>> backend.exists("/copy.txt", "1.0.0")
            False
            >>> backend.copy_file("/file.txt", "/copy.txt", version="1.0.0")
            >>> backend.exists("/copy.txt", "1.0.0")
            True

        """
        if version is None:
            versions = self.versions(src_path)
        else:
            versions = [version]

        for version in versions:
            self._copy_file(
                self.path(src_path, version),
                self.path(dst_path, version),
                validate,
                verbose,
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
            >>> backend = Versioned(filesystem)
            >>> backend._date = mock_date

        Examples:
            >>> file = "src.txt"
            >>> backend.put_file(file, "/file.txt", "1.0.0")
            >>> backend.date("/file.txt", "1.0.0")
            '1991-02-20'

        """
        path = self.path(path, version)
        return self._date(path)

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
            >>> backend = Versioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> backend.exists("/file.txt", "1.0.0")
            False
            >>> backend.put_file(file, "/file.txt", "1.0.0")
            >>> backend.exists("/file.txt", "1.0.0")
            True

        """
        path = self.path(path, version)
        return self._exists(path, suppress_backend_errors)

    def get_archive(
        self,
        src_path: str,
        dst_root: str,
        version: str,
        *,
        tmp_root: str = None,
        validate: bool = False,
        verbose: bool = False,
    ) -> typing.List[str]:
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
            >>> backend = Versioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> backend.put_archive(".", "/sub/archive.zip", "1.0.0", files=[file])
            >>> os.remove(file)
            >>> backend.get_archive("/sub/archive.zip", ".", "1.0.0")
            ['src.txt']

        """
        src_path = self.path(src_path, version)
        return self._get_archive(src_path, dst_root, tmp_root, validate, verbose)

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
            >>> backend = Versioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> backend.put_file(file, "/file.txt", "1.0.0")
            >>> os.path.exists("dst.txt")
            False
            >>> backend.get_file("/file.txt", "dst.txt", "1.0.0")
            '...dst.txt'

        """
        src_path = self.path(src_path, version)
        return self._get_file(src_path, dst_path, validate, verbose)

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
            >>> backend = Versioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> backend.put_file(file, "/file.txt", "1.0.0")
            >>> backend.put_file(file, "/file.txt", "2.0.0")
            >>> backend.latest_version("/file.txt")
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
            RuntimeError: if backend was not opened

        ..
            >>> backend = Versioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> backend.put_file(file, "/file.txt", "1.0.0")
            >>> backend.put_file(file, "/file.txt", "2.0.0")
            >>> backend.put_archive(".", "/sub/archive.zip", "1.0.0", files=[file])
            >>> backend.ls()
            [('/file.txt', '1.0.0'), ('/file.txt', '2.0.0'), ('/sub/archive.zip', '1.0.0')]
            >>> backend.ls(latest_version=True)
            [('/file.txt', '2.0.0'), ('/sub/archive.zip', '1.0.0')]
            >>> backend.ls("/file.txt")
            [('/file.txt', '1.0.0'), ('/file.txt', '2.0.0')]
            >>> backend.ls(pattern="*.txt")
            [('/file.txt', '1.0.0'), ('/file.txt', '2.0.0')]
            >>> backend.ls(pattern="archive.*")
            [('/sub/archive.zip', '1.0.0')]
            >>> backend.ls("/sub/")
            [('/sub/archive.zip', '1.0.0')]

        """  # noqa: E501
        if path.endswith("/"):  # find files under sub-path
            paths = self._ls(path, suppress_backend_errors)

        else:  # find versions of path
            root, file = self.split(path)

            paths = self._ls(root, suppress_backend_errors)

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
            >>> backend = Versioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> backend.put_file(file, "/file.txt", "1.0.0")
            >>> backend.exists("/move.txt", "1.0.0")
            False
            >>> backend.move_file("/file.txt", "/move.txt", version="1.0.0")
            >>> backend.exists("/move.txt", "1.0.0")
            True
            >>> backend.exists("/file.txt", "1.0.0")
            False

        """
        if version is None:
            versions = self.versions(src_path)
        else:
            versions = [version]

        for version in versions:
            self._move_file(
                self.path(src_path, version),
                self.path(dst_path, version),
                validate,
                verbose,
            )

    def path(
        self,
        path: str,
        version: str,
        *,
        allow_sub_path: bool = False,
    ) -> str:
        r"""Resolved backend path.

        Resolved path as handed to the filesystem object.

        <root>/<base><ext>
        ->
        <root>/<version>/<base><ext>

        Args:
            path: path on backend
            version: version string
            allow_sub_path: if ``path`` is allowed
                to point to a sub-path
                instead of a file

        Returns:
            path as handed to the filesystem object

        Raises:
            ValueError: if ``path`` does not start with ``'/'``,
                ends on ``'/'`` when ``allow_sub_path`` is ``False``,
                or does not match ``'[A-Za-z0-9/._-]+'``

        """
        path = self._path(path, allow_sub_path)

        # Assert version is not empty and does not contain invalid characters.
        version_allowed_chars = "[A-Za-z0-9._-]+"
        if not version:
            raise ValueError("Version must not be empty.")
        if re.compile(version_allowed_chars).fullmatch(version) is None:
            raise ValueError(
                f"Invalid version '{version}', "
                f"does not match '{version_allowed_chars}'."
            )

        root, name = self.split(path)
        path = self.join(root, version, name)
        return path

    def put_archive(
        self,
        src_root: str,
        dst_path: str,
        version: str,
        *,
        files: typing.Union[str, typing.Sequence[str]] = None,
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
            >>> backend = Versioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> backend.exists("/sub/archive.tar.gz", "1.0.0")
            False
            >>> backend.put_archive(".", "/sub/archive.tar.gz", "1.0.0")
            >>> backend.exists("/sub/archive.tar.gz", "1.0.0")
            True

        """
        dst_path = self.path(dst_path, version)
        self._put_archive(src_root, dst_path, files, tmp_root, validate, verbose)

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
            >>> backend = Versioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> backend.exists("/file.txt", "3.0.0")
            False
            >>> backend.put_file(file, "/file.txt", "3.0.0")
            >>> backend.exists("/file.txt", "3.0.0")
            True

        """
        dst_path = self.path(dst_path, version)
        return self._put_file(src_path, dst_path, validate, verbose)

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
            >>> backend = Versioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> backend.put_file(file, "/file.txt", "1.0.0")
            >>> backend.exists("/file.txt", "1.0.0")
            True
            >>> backend.remove_file("/file.txt", "1.0.0")
            >>> backend.exists("/file.txt", "1.0.0")
            False

        """
        path = self.path(path, version)
        self._remove_file(path)

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
            ValueError: if ``path`` does not start with ``'/'``,
                ends on ``'/'``,
                or does not match ``'[A-Za-z0-9/._-]+'``
            RuntimeError: if backend was not opened

        ..
            >>> backend = Versioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> backend.put_file(file, "/file.txt", "1.0.0")
            >>> backend.put_file(file, "/file.txt", "2.0.0")
            >>> backend.versions("/file.txt")
            ['1.0.0', '2.0.0']

        """
        path = self._path(path)
        paths = self.ls(path, suppress_backend_errors=suppress_backend_errors)
        vs = [v for _, v in paths]
        return vs
