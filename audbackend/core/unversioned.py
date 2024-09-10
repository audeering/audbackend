import typing

from audbackend.core.base import AbstractBackend


class Unversioned(AbstractBackend):
    r"""Interface for unversioned file access.

    Use this interface if you don't care about versioning.
    For every backend path exactly one file exists on the backend.

    Args:
        backend: backend object

    Examples:
        >>> file = "src.txt"
        >>> fs = fsspec.filesystem("dir", path="./host/repo")
        >>> interface = Unversioned(fs)
        >>> interface.put_file(file, "/file.txt")
        >>> interface.put_archive(".", "/sub/archive.zip", files=[file])
        >>> interface.ls()
        ['/file.txt', '/sub/archive.zip']
        >>> interface.get_file("/file.txt", "dst.txt")
        '...dst.txt'

    """

    def checksum(
        self,
        path: str,
    ) -> str:
        r"""MD5 checksum for file on backend.

        Args:
            path: path to file on backend

        Returns:
            MD5 checksum

        Raises:
            BackendError: if an error is raised on the backend,
                e.g. ``path`` does not exist
            ValueError: if ``path`` does not start with ``'/'``,
                ends on ``'/'``,
                or does not match ``'[A-Za-z0-9/._-]+'``
            RuntimeError: if backend was not opened

        ..
            >>> fs = fsspec.filesystem("dir", path="./host/repo")
            >>> interface = Unversioned(fs)

        Examples:
            >>> file = "src.txt"
            >>> import audeer
            >>> audeer.md5(file)
            'd41d8cd98f00b204e9800998ecf8427e'
            >>> interface.put_file(file, "/file.txt")
            >>> interface.checksum("/file.txt")
            'd41d8cd98f00b204e9800998ecf8427e'

        """
        path = self.path(path)
        return self._checksum(path)

    def copy_file(
        self,
        src_path: str,
        dst_path: str,
        *,
        validate: bool = False,
        verbose: bool = False,
    ):
        r"""Copy file on backend.

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
            verbose: show debug messages

        Raises:
            BackendError: if an error is raised on the backend
            InterruptedError: if validation fails
            ValueError: if ``src_path`` or ``dst_path``
                does not start with ``'/'``,
                ends on ``'/'``,
                or does not match ``'[A-Za-z0-9/._-]+'``
            RuntimeError: if backend was not opened

        ..
            >>> fs = fsspec.filesystem("dir", path="./host/repo")
            >>> interface = Unversioned(fs)

        Examples:
            >>> file = "src.txt"
            >>> interface.put_file(file, "/file.txt")
            >>> interface.exists("/copy.txt")
            False
            >>> interface.copy_file("/file.txt", "/copy.txt")
            >>> interface.exists("/copy.txt")
            True

        """
        src_path = self.path(src_path)
        dst_path = self.path(dst_path)
        self._copy_file(src_path, dst_path, validate, verbose)

    def date(self, path: str) -> str:
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
            ValueError: if ``path`` does not start with ``'/'``,
                ends on ``'/'``,
                or does not match ``'[A-Za-z0-9/._-]+'``
            RuntimeError: if backend was not opened

        ..
            >>> fs = fsspec.filesystem("dir", path="./host/repo")
            >>> interface = Unversioned(fs)

        Examples:
            >>> file = "src.txt"
            >>> interface.put_file(file, "/file.txt")
            >>> interface.date("/file.txt")
            '1991-02-20'

        """
        path = self.path(path)
        return self._date(path)

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
            ValueError: if ``path`` does not start with ``'/'``,
                ends on ``'/'``,
                or does not match ``'[A-Za-z0-9/._-]+'``
            ValueError: if ``version`` is empty or
                does not match ``'[A-Za-z0-9._-]+'``
            RuntimeError: if backend was not opened

        ..
            >>> fs = fsspec.filesystem("dir", path="./host/repo")
            >>> interface = Unversioned(fs)

        Examples:
            >>> file = "src.txt"
            >>> interface.exists("/file.txt")
            False
            >>> interface.put_file(file, "/file.txt")
            >>> interface.exists("/file.txt")
            True

        """
        path = self.path(path)
        return self._exists(path, suppress_backend_errors)

    def get_file(
        self,
        src_path: str,
        dst_path: str,
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
            src_path: path to file on backend
            dst_path: destination path to local file
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
            RuntimeError: if backend was not opened

        ..
            >>> fs = fsspec.filesystem("dir", path="./host/repo")
            >>> interface = Unversioned(fs)

        Examples:
            >>> file = "src.txt"
            >>> interface.put_file(file, "/file.txt")
            >>> os.path.exists("dst.txt")
            False
            >>> _ = interface.get_file("/file.txt", "dst.txt")
            >>> os.path.exists("dst.txt")
            True

        """
        src_path = self.path(src_path)
        return self._get_file(src_path, dst_path, validate, verbose)

    def ls(
        self,
        path: str = "/",
        *,
        pattern: str = None,
        suppress_backend_errors: bool = False,
    ) -> typing.List[str]:
        r"""List files on backend.

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
            list of files

        Raises:
            BackendError: if ``suppress_backend_errors`` is ``False``
                and an error is raised on the backend,
                e.g. ``path`` does not exist
            ValueError: if ``path`` does not start with ``'/'`` or
                does not match ``'[A-Za-z0-9/._-]+'``
            RuntimeError: if backend was not opened

        ..
            >>> fs = fsspec.filesystem("dir", path="./host/repo")
            >>> interface = Unversioned(fs)

        Examples:
            >>> file = "src.txt"
            >>> interface.put_file(file, "/file.txt")
            >>> interface.put_archive(".", "/sub/archive.zip", files=[file])
            >>> interface.ls()
            ['/file.txt', '/sub/archive.zip']
            >>> interface.ls("/file.txt")
            ['/file.txt']
            >>> interface.ls(pattern="*.txt")
            ['/file.txt']
            >>> interface.ls(pattern="archive.*")
            ['/sub/archive.zip']
            >>> interface.ls("/sub/")
            ['/sub/archive.zip']

        """  # noqa: E501
        path = self.path(path, allow_sub_path=True)
        return self._ls(path, pattern, suppress_backend_errors)

    def move_file(
        self,
        src_path: str,
        dst_path: str,
        *,
        validate: bool = False,
        verbose: bool = False,
    ):
        r"""Move file on backend.

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
            validate: verify file was successfully moved
            verbose: show debug messages

        Raises:
            BackendError: if an error is raised on the backend
            InterruptedError: if validation fails
            ValueError: if ``src_path`` or ``dst_path``
                does not start with ``'/'``,
                ends on ``'/'``,
                or does not match ``'[A-Za-z0-9/._-]+'``
            RuntimeError: if backend was not opened

        ..
            >>> fs = fsspec.filesystem("dir", path="./host/repo")
            >>> interface = Unversioned(fs)

        Examples:
            >>> file = "src.txt"
            >>> interface.put_file(file, "/file.txt")
            >>> interface.exists("/move.txt")
            False
            >>> interface.move_file("/file.txt", "/move.txt")
            >>> interface.exists("/move.txt")
            True
            >>> interface.exists("/file.txt")
            False

        """
        src_path = self.path(src_path)
        dst_path = self.path(dst_path)
        self._move_file(src_path, dst_path, validate, verbose)

    def path(
        self,
        path: str,
        *,
        allow_sub_path: bool = False,
    ) -> str:
        r"""Resolved backend path.

        Resolved path as handed to the filesystem object.

        Args:
            path: path on backend
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
        return self._path(path, allow_sub_path)

    def put_file(
        self,
        src_path: str,
        dst_path: str,
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
            validate: verify file was successfully
                put on the backend
            verbose: show debug messages

        Raises:
            BackendError: if an error is raised on the backend
            FileNotFoundError: if ``src_path`` does not exist
            InterruptedError: if validation fails
            IsADirectoryError: if ``src_path`` is a folder
            ValueError: if ``dst_path`` does not start with ``'/'``,
                ends on ``'/'``,
                or does not match ``'[A-Za-z0-9/._-]+'``
            RuntimeError: if backend was not opened

        ..
            >>> fs = fsspec.filesystem("dir", path="./host/repo")
            >>> interface = Unversioned(fs)

        Examples:
            >>> file = "src.txt"
            >>> interface.exists("/file.txt")
            False
            >>> interface.put_file(file, "/file.txt")
            >>> interface.exists("/file.txt")
            True

        """
        dst_path = self.path(dst_path)
        self._put_file(src_path, dst_path, validate, verbose)

    def remove_file(self, path: str):
        r"""Remove file from backend.

        Args:
            path: path to file on backend

        Raises:
            BackendError: if an error is raised on the backend,
                e.g. ``path`` does not exist
            ValueError: if ``path`` does not start with ``'/'``,
                ends on ``'/'``,
                or does not match ``'[A-Za-z0-9/._-]+'``

        ..
            >>> fs = fsspec.filesystem("dir", path="./host/repo")
            >>> interface = Unversioned(fs)

        Examples:
            >>> file = "src.txt"
            >>> interface.put_file(file, "/file.txt")
            >>> interface.exists("/file.txt")
            True
            >>> interface.remove_file("/file.txt")
            >>> interface.exists("/file.txt")
            False

        """
        path = self.path(path)
        self._remove_file(path)
