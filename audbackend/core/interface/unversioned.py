import fnmatch
import hashlib
import os
import tempfile
import typing

import fsspec
import tqdm

import audeer

from audbackend.core import utils
from audbackend.core.errors import BackendError
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
        path = utils.check_path(path)

        # Most filesystem object do not implement MD5 checksum,
        # but use the standard implementation based on the info dict
        # (https://github.com/fsspec/filesystem_spec/blob/76ca4a68885d572880ac6800f079738df562f02c/fsspec/spec.py#L692C16-L692C50):
        # int(tokenize(self.info(path)), 16)
        #
        # We rely on the MD5 checksum
        # to decide if a local file is identical to one on the backend.
        # This information is then used to decide if `put_file()`
        # has to overwrite a file on the backend or not.

        # Implementation compatible with audeer.md5()
        def md5sum(path: str) -> str:
            """Implementation compatible with audeer.md5().

            Args:
                path: path on backend

            Returns:
                MD5 sum

            """
            hasher = hashlib.md5()
            chunk_size = 8192
            with self.fs.open(path) as fp:
                while True:
                    data = fp.read(chunk_size)
                    if not data:
                        break
                    hasher.update(data)
            return hasher.hexdigest()

        info = utils.call_function_on_backend(self.fs.info, path)
        if "ETag" in info:
            md5 = ["ETag"][1:-1]
        else:
            md5 = utils.call_function_on_backend(md5sum, path)

        return md5

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
        src_path = utils.check_path(src_path)
        dst_path = utils.check_path(dst_path)

        def copy(src_path, dst_path):
            if not self.exists(dst_path) or self.checksum(src_path) != self.checksum(
                dst_path
            ):
                if self.exists(dst_path):
                    self.remove_file(dst_path)
                # Ensure sub-paths exist
                self.fs.makedirs(os.path.dirname(dst_path), exist_ok=True)
            self.fs.copy(
                src_path,
                dst_path,
                callback=_progress_bar("Copy file", verbose),
            )

        if src_path != dst_path:
            utils.call_function_on_backend(copy, src_path, dst_path)

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
        path = utils.check_path(path)
        date = utils.call_function_on_backend(self.fs.modified, path)
        date = utils.date_format(date)
        return date

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
        return utils.call_function_on_backend(
            self.fs.exists,
            utils.check_path(path),
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
                # audeer.path(tmp, os.path.basename(dst_root)),
                tmp,
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
        src_path = utils.check_path(src_path)
        dst_path = audeer.path(dst_path)
        if os.path.isdir(dst_path):
            raise utils.raise_is_a_directory(dst_path)

        dst_root = os.path.dirname(dst_path)
        audeer.mkdir(dst_root)

        if not os.access(dst_root, os.W_OK) or (
            os.path.exists(dst_path) and not os.access(dst_path, os.W_OK)
        ):  # pragma: no Windows cover
            msg = f"Permission denied: '{dst_path}'"
            raise PermissionError(msg)

        if not os.path.exists(dst_path) or audeer.md5(dst_path) != self.checksum(
            src_path
        ):
            # get file to a temporary directory first,
            # only on success move to final destination
            with tempfile.TemporaryDirectory(dir=dst_root) as tmp:
                tmp_path = audeer.path(tmp, "~")
                utils.call_function_on_backend(
                    self.fs.get_file,
                    src_path,
                    tmp_path,
                    callback=_progress_bar("Get file", verbose),
                )
                audeer.move_file(tmp_path, dst_path)

        return dst_path

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
        path = utils.check_path(path, allow_sub_path=True)
        paths = utils.call_function_on_backend(
            self.fs.find,
            path,
            suppress_backend_errors=suppress_backend_errors,
            fallback_return_value=[],
        )
        paths = sorted(
            [path if path.startswith(self.sep) else self.sep + path for path in paths]
        )

        if not paths:
            if path != self.sep and not suppress_backend_errors:
                # if the path does not exist
                # we raise an error
                try:
                    raise utils.raise_file_not_found_error(path)
                except FileNotFoundError as ex:
                    raise BackendError(ex)

            return []

        if pattern:
            paths = [
                path
                for path in paths
                if fnmatch.fnmatch(os.path.basename(path), pattern)
            ]

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
        src_path = utils.check_path(src_path)
        dst_path = utils.check_path(dst_path)

        if src_path == dst_path:
            return

        def move(src_path, dst_path):
            if not self.exists(dst_path) or self.checksum(src_path) != self.checksum(
                dst_path
            ):
                if self.exists(dst_path):
                    self.remove_file(dst_path)
                # Ensure sub-paths exist
                self.fs.makedirs(os.path.dirname(dst_path), exist_ok=True)
            self.fs.move(
                src_path,
                dst_path,
                callback=_progress_bar("Move file", verbose),
            )

        utils.call_function_on_backend(move, src_path, dst_path)

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
        dst_path = utils.check_path(dst_path)

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
        if not os.path.exists(src_path):
            utils.raise_file_not_found_error(src_path)
        elif os.path.isdir(src_path):
            raise utils.raise_is_a_directory(src_path)
        dst_path = utils.check_path(dst_path)

        def put(src_path, dst_path):
            # skip if file with same checksum already exists
            src_checksum = audeer.md5(src_path)
            if not self.exists(dst_path) or src_checksum != self.checksum(dst_path):
                if self.exists(dst_path):
                    self.remove_file(dst_path)
                # Ensure sub-paths exist
                self.fs.makedirs(os.path.dirname(dst_path), exist_ok=True)
                self.fs.put_file(
                    src_path,
                    dst_path,
                    callback=_progress_bar("Put file", verbose),
                )

        utils.call_function_on_backend(put, src_path, dst_path)

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
        path = utils.check_path(path)
        utils.call_function_on_backend(self.fs.rm_file, path)


def _progress_bar(desc: str, verbose: bool) -> tqdm.tqdm:
    return fsspec.callbacks.TqdmCallback(
        tqdm_kwargs={
            "desc": desc,
            "disable": not verbose,
        },
        tqdm_cls=audeer.progress_bar,
    )
