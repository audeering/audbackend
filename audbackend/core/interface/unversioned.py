import fnmatch
import os
import tempfile
import typing

import fsspec
import tqdm

import audeer

from audbackend.core import utils
from audbackend.core.interface.base import Base


class Unversioned(Base):
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
        self.backend.makedirs(os.path.dirname(dst_path), exist_ok=True)
        self.backend.copy(
            src_path,
            dst_path,
            callback=_progress_bar("Copy file", verbose),
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
            >>> fs = fsspec.filesystem("dir", path="./host/repo")
            >>> interface = Unversioned(fs)

        Examples:
            >>> file = "src.txt"
            >>> interface.put_file(file, "/file.txt")
            >>> interface.date("/file.txt")
            '1991-02-20'

        """
        return self.backend.modified(path)

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
        utils.call_function_on_backend(
            self.backend.exists,
            path,
            suppress_backend_errors=suppress_backend_errors,
            fallback_return_value=False,
        )

    def get_archive(
        self,
        src_path: str,
        dst_root: str,
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
            >>> fs = fsspec.filesystem("dir", path="./host/repo")
            >>> interface = Unversioned(fs)

        Examples:
            >>> file = "src.txt"
            >>> interface.put_archive(".", "/sub/archive.zip", files=[file])
            >>> os.remove(file)
            >>> interface.get_archive("/sub/archive.zip", ".")
            ['src.txt']

        """
        with tempfile.TemporaryDirectory(dir=tmp_root) as tmp:
            local_archive = os.path.join(
                audeer.path(tmp, os.path.basename(dst_root)),
                os.path.basename(src_path),
            )
            self.get_file(
                src_path,
                local_archive,
                validate=validate,
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
        return self.backend.get_file(
            src_path,
            dst_path,
            callback=_progress_bar("Get file", verbose),
        )

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
        paths = utils.call_function_on_backend(
            self.backend.find,
            path,
            suppress_backend_errors=suppress_backend_errors,
            fallback_return_value=[],
        )
        paths = sorted([self.sep + path for path in paths])

        # if not paths:
        #     if path != "/" and not suppress_backend_errors:
        #         # if the path does not exist
        #         # we raise an error
        #         try:
        #             raise utils.raise_file_not_found_error(path)
        #         except FileNotFoundError as ex:
        #             raise BackendError(ex)

        #     return []

        if pattern:
            paths = [p for p in paths if fnmatch.fnmatch(os.path.basename(p), pattern)]

        return paths

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
        self.backend.move(
            src_path,
            dst_path,
            callback=_progress_bar("Move file", verbose),
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
            >>> fs = fsspec.filesystem("dir", path="./host/repo")
            >>> interface = Unversioned(fs)

        Examples:
            >>> file = "src.txt"
            >>> interface.put_file(file, "/file.txt")
            >>> interface.owner("/file.txt")
            'doctest'

        """
        return None  # there exists no equivalent in fsspec

    def put_archive(
        self,
        src_root: str,
        dst_path: str,
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
            >>> fs = fsspec.filesystem("dir", path="./host/repo")
            >>> interface = Unversioned(fs)

        Examples:
            >>> file = "src.txt"
            >>> interface.exists("/sub/archive.tar.gz")
            False
            >>> interface.put_archive(".", "/sub/archive.tar.gz")
            >>> interface.exists("/sub/archive.tar.gz")
            True

        """
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
        self.backend.put_file(
            src_path,
            dst_path,
            callback=_progress_bar("Put file", verbose),
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
        self.backend.rm_file(path)


def _progress_bar(desc: str, verbose: bool) -> tqdm.tqdm:
    return fsspec.callbacks.TqdmCallback(
        tqdm_kwargs={
            "desc": desc,
            "disable": not verbose,
        },
        tqdm_cls=audeer.progress_bar,
    )
