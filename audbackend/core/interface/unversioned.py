from collections.abc import Sequence
import os  # noqa: F401

from audbackend.core.interface.base import Base


class Unversioned(Base):
    r"""Interface for unversioned file access.

    Use this interface if you don't care about versioning.
    For every backend path exactly one file exists on the backend.

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
        >>> interface = Unversioned(backend)
        >>> file = "src.txt"
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
            >>> interface = Unversioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> import audeer
            >>> audeer.md5(file)
            'd41d8cd98f00b204e9800998ecf8427e'
            >>> interface.put_file(file, "/file.txt")
            >>> interface.checksum("/file.txt")
            'd41d8cd98f00b204e9800998ecf8427e'

        """
        return self.backend.checksum(path)

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
            >>> interface = Unversioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> interface.put_file(file, "/file.txt")
            >>> interface.exists("/copy.txt")
            False
            >>> interface.copy_file("/file.txt", "/copy.txt")
            >>> interface.exists("/copy.txt")
            True

        """
        self.backend.copy_file(
            src_path,
            dst_path,
            validate=validate,
            verbose=verbose,
        )

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
            ValueError: if ``path`` does not start with ``'/'``,
                ends on ``'/'``,
                or does not match ``'[A-Za-z0-9/._-]+'``
            RuntimeError: if backend was not opened

        ..
            >>> interface = Unversioned(filesystem)
            >>> interface.date = mock_date

        Examples:
            >>> file = "src.txt"
            >>> interface.put_file(file, "/file.txt")
            >>> interface.date("/file.txt")
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
            ValueError: if ``path`` does not start with ``'/'``,
                ends on ``'/'``,
                or does not match ``'[A-Za-z0-9/._-]+'``
            ValueError: if ``version`` is empty or
                does not match ``'[A-Za-z0-9._-]+'``
            RuntimeError: if backend was not opened

        ..
            >>> interface = Unversioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> interface.exists("/file.txt")
            False
            >>> interface.put_file(file, "/file.txt")
            >>> interface.exists("/file.txt")
            True

        """
        return self.backend.exists(
            path,
            suppress_backend_errors=suppress_backend_errors,
        )

    def get_archive(
        self,
        src_path: str,
        dst_root: str,
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
            RuntimeError: if backend was not opened

        ..
            >>> interface = Unversioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> interface.put_archive(".", "/sub/archive.zip", files=[file])
            >>> os.remove(file)
            >>> interface.get_archive("/sub/archive.zip", ".")
            ['src.txt']

        """
        return self.backend.get_archive(
            src_path,
            dst_root,
            tmp_root=tmp_root,
            validate=validate,
            verbose=verbose,
        )

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
            >>> interface = Unversioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> interface.put_file(file, "/file.txt")
            >>> interface.get_file("/file.txt", "dst.txt")
            '...dst.txt'

        """
        return self.backend.get_file(
            src_path,
            dst_path,
            validate=validate,
            verbose=verbose,
        )

    def ls(
        self,
        path: str = "/",
        *,
        pattern: str = None,
        suppress_backend_errors: bool = False,
    ) -> list[str]:
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
            RuntimeError: if backend was not opened

        ..
            >>> interface = Unversioned(filesystem)

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
        return self.backend.ls(
            path,
            pattern=pattern,
            suppress_backend_errors=suppress_backend_errors,
        )

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
            >>> interface = Unversioned(filesystem)

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
        self.backend.move_file(
            src_path,
            dst_path,
            validate=validate,
            verbose=verbose,
        )

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
            ValueError: if ``path`` does not start with ``'/'``,
                ends on ``'/'``,
                or does not match ``'[A-Za-z0-9/._-]+'``
            RuntimeError: if backend was not opened

        ..
            >>> interface = Unversioned(filesystem)
            >>> interface.owner = mock_owner

        Examples:
            >>> file = "src.txt"
            >>> interface.put_file(file, "/file.txt")
            >>> interface.owner("/file.txt")
            'doctest'

        """
        return self.backend.owner(path)

    def put_archive(
        self,
        src_root: str,
        dst_path: str,
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
            RuntimeError: if backend was not opened

        ..
            >>> interface = Unversioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> interface.exists("/sub/archive.tar.gz")
            False
            >>> interface.put_archive(".", "/sub/archive.tar.gz")
            >>> interface.exists("/sub/archive.tar.gz")
            True

        """
        self.backend.put_archive(
            src_root,
            dst_path,
            files=files,
            tmp_root=tmp_root,
            validate=validate,
            verbose=verbose,
        )

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
            >>> interface = Unversioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> interface.exists("/file.txt")
            False
            >>> interface.put_file(file, "/file.txt")
            >>> interface.exists("/file.txt")
            True

        """
        self.backend.put_file(
            src_path,
            dst_path,
            validate=validate,
            verbose=verbose,
        )

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
            ValueError: if ``path`` does not start with ``'/'``,
                ends on ``'/'``,
                or does not match ``'[A-Za-z0-9/._-]+'``

        ..
            >>> interface = Unversioned(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> interface.put_file(file, "/file.txt")
            >>> interface.exists("/file.txt")
            True
            >>> interface.remove_file("/file.txt")
            >>> interface.exists("/file.txt")
            False

        """
        self.backend.remove_file(path)
