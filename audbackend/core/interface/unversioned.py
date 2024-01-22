import os  # noqa: F401
import typing

from audbackend.core.interface.base import Base


class Unversioned(Base):
    r"""Interface for unversioned file access.

    Use this interface if you don't care about versioning.
    For every backend path exactly one file exists on the backend.

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
            ValueError: if ``path`` does not start with ``'/'`` or
                does not match ``'[A-Za-z0-9/._-]+'``

        Examples:
            >>> unversioned.checksum('/f.ext')
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
              >>> unversioned.date('/f.ext')
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
            >>> unversioned.exists('/f.ext')
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
            >>> unversioned.get_archive('/a.zip', '.')
            ['src.pth']

        """
        return self.backend.get_archive(
            src_path,
            dst_root,
            tmp_root=tmp_root,
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
            >>> _ = unversioned.get_file('/f.ext', 'dst.pth')
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
            >>> unversioned.ls()
            ['/a.zip', '/a/b.ext', '/f.ext']
            >>> unversioned.ls('/f.ext')
            ['/f.ext']
            >>> unversioned.ls(pattern='*.ext')
            ['/a/b.ext', '/f.ext']
            >>> unversioned.ls(pattern='b.*')
            ['/a/b.ext']
            >>> unversioned.ls('/a/')
            ['/a/b.ext']

        """  # noqa: E501
        return self.backend.ls(
            path,
            pattern=pattern,
            suppress_backend_errors=suppress_backend_errors,
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
            ValueError: if ``path`` does not start with ``'/'`` or
                does not match ``'[A-Za-z0-9/._-]+'``

        Examples:
              >>> unversioned.owner('/f.ext')
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
            >>> unversioned.exists('/a.tar.gz')
            False
            >>> unversioned.put_archive('.', '/a.tar.gz')
            >>> unversioned.exists('/a.tar.gz')
            True

        """
        self.backend.put_archive(
            src_root,
            dst_path,
            files=files,
            tmp_root=tmp_root,
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
            >>> unversioned.exists('/sub/f.ext')
            False
            >>> unversioned.put_file('src.pth', '/sub/f.ext')
            >>> unversioned.exists('/sub/f.ext')
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
            >>> unversioned.exists('/f.ext')
            True
            >>> unversioned.remove_file('/f.ext')
            >>> unversioned.exists('/f.ext')
            False

        """
        self.backend.remove_file(path)
