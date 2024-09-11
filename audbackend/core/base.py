import abc
import fnmatch
import hashlib
import os
import re
import tempfile
import typing

import fsspec
import tqdm

import audeer

from audbackend.core import utils
from audbackend.core.errors import BackendError


class AbstractBackend(metaclass=abc.ABCMeta):
    r"""Abstract superclass for backends.

    Backend implementations are expected to be compatible with or,
    better,
    subclass from here.

    Args:
        fs: filesystem object
            following :mod:`fsspec` specifications

    """

    def __init__(
        self,
        fs: fsspec.AbstractFileSystem,
        **kwargs,
    ):
        self.fs = fs
        """Filesystem object."""

    def __repr__(
        self,
    ) -> str:
        r"""String representation.

        ..
            >>> fs = fsspec.filesystem("dir", path="./host/repo")
            >>> interface = Base(fs)

        Examples:
            >>> interface
            'audbackend.interface.Base(DirFileSystem)'

        """
        name = self.__class__.__name__
        return f"audbackend.{name}({self.fs.__class__.__name__})"

    def _assert_equal_checksum(
        self,
        *,
        path: str,
        path_is_local: bool,
        expected_checksum: str,
    ):
        r"""Assert checksums are equal.

        If check fails,
        ``path`` is removed
        and an error is raised.

        Args:
            path: path to file to check
            path_is_local: if ``True``
                ``path`` is expected to be on the local disk
            expected_checksum: expected checksum of ``path``

        """
        if path_is_local:
            checksum = audeer.md5(path)
        else:
            checksum = self._checksum(path)

        if checksum != expected_checksum:
            if path_is_local:
                os.remove(path)
                location = "local file system"
            else:
                self._remove_file(path)
                location = "backend"

            raise InterruptedError(
                f"Execution is interrupted because "
                f"{path} "
                f"has checksum "
                f"'{checksum}' "
                "when the expected checksum is "
                f"'{expected_checksum}'. "
                f"The file has been removed from the "
                f"{location}."
            )

    def checksum(
        self,
        path: str,
        *args,
        **kwargs,
    ) -> str:
        r"""MD5 checksum for file on backend.

        Requires MD5 checksum
        for comparison of the checksum across
        different backends,
        which is not guaranteed
        by simply relying on
        :meth:`fsspech.AbstractFileSystem.checksum`.

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

        """
        raise NotImplementedError

    def _checksum(
        self,
        path: str,
    ) -> str:
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
            md5 = ["ETag"][1:-1]  # pragma: nocover (only tested in CI)
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
        **kwargs,
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

        """
        raise NotImplementedError

    def _copy_file(
        self,
        src_path: str,
        dst_path: str,
        validate: bool,
        verbose: bool,
    ):
        if src_path == dst_path:
            return

        src_checksum = self._checksum(src_path)
        dst_exists = self._exists(dst_path)

        def copy(src_path, dst_path):
            # Copy only if dst_path does not exist or has a different checksum
            if not dst_exists or src_checksum != self._checksum(dst_path):
                # Remove dst_path if existent
                if dst_exists:
                    self._remove_file(dst_path)
                # Ensure sub-paths exist
                self.fs.makedirs(os.path.dirname(dst_path), exist_ok=True)
            self.fs.copy(src_path, dst_path, callback=pbar("Copy file", verbose))

        utils.call_function_on_backend(copy, src_path, dst_path)

        if validate:
            self._assert_equal_checksum(
                path=dst_path,
                path_is_local=False,
                expected_checksum=src_checksum,
            )

    def date(
        self,
        path: str,
        *args,
        **kwargs,
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

        """
        raise NotImplementedError

    def _date(
        self,
        path: str,
    ) -> str:
        date = utils.call_function_on_backend(self.fs.modified, path)
        date = utils.date_format(date)
        return date

    def exists(
        self,
        path: str,
        *args,
        suppress_backend_errors: bool = False,
        **kwargs,
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

        """
        raise NotImplementedError

    def _exists(
        self,
        path: str,
        suppress_backend_errors: bool = False,
    ) -> bool:
        return utils.call_function_on_backend(
            self.fs.exists,
            path,
            suppress_backend_errors=suppress_backend_errors,
            fallback_return_value=False,
        )

    def get_archive(
        self,
        src_path: str,
        dst_root: str,
        *args,
        tmp_root: str = None,
        validate: bool = False,
        verbose: bool = False,
        **kwargs,
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

        """
        src_path = self._path(src_path)
        return self._get_archive(src_path, dst_root, tmp_root, validate, verbose)

    def _get_archive(
        self,
        src_path: str,
        dst_root: str,
        tmp_root: str,
        validate: bool,
        verbose: bool,
    ) -> str:
        with tempfile.TemporaryDirectory(dir=tmp_root) as tmp:
            local_archive = os.path.join(tmp, os.path.basename(src_path))
            self._get_file(src_path, local_archive, validate, verbose)
            return audeer.extract_archive(local_archive, dst_root, verbose=verbose)

    def get_file(
        self,
        src_path: str,
        dst_path: str,
        *args,
        validate: bool = False,
        verbose: bool = False,
        **kwargs,
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

        """
        raise NotImplementedError

    def _get_file(
        self,
        src_path: str,
        dst_path: str,
        validate: bool,
        verbose: bool,
    ) -> str:
        dst_path = audeer.path(dst_path)

        # Raise error if dst_path is a folder
        if os.path.isdir(dst_path):
            raise utils.raise_is_a_directory(dst_path)

        # Get file only if it does not exist or has different checksum
        src_checksum = self._checksum(src_path)
        if not os.path.exists(dst_path) or src_checksum != audeer.md5(dst_path):
            # Ensure sub-paths of dst_path exists
            dst_root = os.path.dirname(dst_path)
            audeer.mkdir(dst_root)

            # Raise error if we don't have write permissions to dst_root
            if not os.access(dst_root, os.W_OK) or (
                os.path.exists(dst_path) and not os.access(dst_path, os.W_OK)
            ):  # pragma: no Windows cover
                msg = f"Permission denied: '{dst_path}'"
                raise PermissionError(msg)

            # Get file to a temporary directory first,
            # only on success move to final destination.
            # This also overwrites a potential existing dst_path
            with tempfile.TemporaryDirectory(dir=dst_root) as tmp:
                tmp_path = audeer.path(tmp, "~")
                utils.call_function_on_backend(
                    self.fs.get_file,
                    src_path,
                    tmp_path,
                    callback=pbar("Get file", verbose),
                )
                audeer.move_file(tmp_path, dst_path)

            if validate:
                self._assert_equal_checksum(
                    path=dst_path,
                    path_is_local=True,
                    expected_checksum=src_checksum,
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
            ValueError: if ``path`` contains invalid character
                or does not start with ``'/'``,
                or if joined path contains invalid character

        ..
            >>> fs = fsspec.filesystem("dir", path="./host/repo")
            >>> interface = Base(fs)

        Examples:
            >>> interface.join("/", "file.txt")
            '/file.txt'
            >>> interface.join("/sub", "file.txt")
            '/sub/file.txt'
            >>> interface.join("//sub//", "/", "", None, "/file.txt")
            '/sub/file.txt'

        """
        path = self._path(path, allow_sub_path=True)

        paths = [path] + [p for p in paths]
        paths = [path for path in paths if path]  # remove empty or None
        path = self.sep.join(paths)

        path = self._path(path, allow_sub_path=True)

        return path

    def ls(
        self,
        path: str = "/",
        *args,
        pattern: str = None,
        suppress_backend_errors: bool = False,
        **kwargs,
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

        """  # noqa: E501
        raise NotImplementedError

    def _ls(
        self,
        path: str,
        suppress_backend_errors: bool,
        pattern: str = None,
    ) -> typing.List[str]:
        # Find all files under path
        paths = utils.call_function_on_backend(
            self.fs.find,
            path,
            suppress_backend_errors=suppress_backend_errors,
            fallback_return_value=[],
        )
        # Sort and ensure each path starts with a sep
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

        # Filter for matching pattern
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
        *args,
        validate: bool = False,
        verbose: bool = False,
        **kwargs,
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
        raise NotImplementedError

    def _move_file(
        self,
        src_path: str,
        dst_path: str,
        validate: bool,
        verbose: bool,
    ):
        if src_path == dst_path:
            return

        # To support validation, we first copy the file
        self._copy_file(src_path, dst_path, validate, verbose)
        self._remove_file(src_path)

    def path(
        self,
        path: str,
        *args,
        allow_sub_path: bool = False,
        **kwargs,
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
        raise NotImplementedError

    def _path(self, path: str, allow_sub_path: bool = False) -> str:
        # Assert path starts with sep, but not ends on it
        if not path.startswith(self.sep):
            raise ValueError(
                f"Invalid backend path '{path}', " f"must start with '{self.sep}'."
            )
        if not allow_sub_path and path.endswith(self.sep):
            raise ValueError(
                f"Invalid backend path '{path}', " f"must not end on '{self.sep}'."
            )

        # Check for allowed characters.
        # This is mainly motivated by the Artifactory filesystem,
        # which allows only a very limited amount of characters
        allowed_chars = "[A-Za-z0-9/._-]+"
        if path and re.compile(allowed_chars).fullmatch(path) is None:
            raise ValueError(
                f"Invalid backend path '{path}', " f"does not match '{allowed_chars}'."
            )

        # Remove immediately consecutive seps
        is_sub_path = path.endswith(self.sep)
        paths = path.split(self.sep)
        paths = [path for path in paths if path]
        path = self.sep + self.sep.join(paths)
        if is_sub_path and not path.endswith(self.sep):
            path += self.sep

        return path

    def put_archive(
        self,
        src_root: str,
        dst_path: str,
        *args,
        files: typing.Union[str, typing.Sequence[str]] = None,
        tmp_root: str = None,
        validate: bool = False,
        verbose: bool = False,
        **kwargs,
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

        """
        dst_path = self._path(dst_path)
        self._put_archive(src_root, dst_path, files, tmp_root, validate, verbose)

    def _put_archive(
        self,
        src_root: str,
        dst_path: str,
        files: typing.Union[str, typing.Sequence[str]],
        tmp_root: str,
        validate: bool,
        verbose: bool,
    ):
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
            self._put_file(archive, dst_path, validate, verbose)

    def put_file(
        self,
        src_path: str,
        dst_path: str,
        *args,
        validate: bool = False,
        verbose: bool = False,
        **kwargs,
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
        raise NotImplementedError

    def _put_file(
        self,
        src_path: str,
        dst_path: str,
        validate: bool,
        verbose: bool,
    ):
        if not os.path.exists(src_path):
            utils.raise_file_not_found_error(src_path)
        elif os.path.isdir(src_path):
            raise utils.raise_is_a_directory(src_path)

        src_checksum = audeer.md5(src_path)
        dst_exists = self._exists(dst_path)

        def put(src_path, dst_path):
            # skip if file with same checksum already exists
            if not dst_exists or src_checksum != self._checksum(dst_path):
                if dst_exists:
                    self._remove_file(dst_path)
                # Ensure sub-paths exist
                self.fs.makedirs(os.path.dirname(dst_path), exist_ok=True)
                self.fs.put_file(src_path, dst_path, callback=pbar("Put file", verbose))

        utils.call_function_on_backend(put, src_path, dst_path)
        if validate:
            self._assert_equal_checksum(
                path=dst_path,
                path_is_local=False,
                expected_checksum=src_checksum,
            )

    def remove_file(
        self,
        path: str,
        *args,
        **kwargs,
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

        """
        raise NotImplementedError

    def _remove_file(
        self,
        path: str,
    ):
        utils.call_function_on_backend(self.fs.rm_file, path)

    @property
    def sep(
        self,
    ) -> str:
        r"""File separator on backend.

        Returns:
            file separator

        ..
            >>> fs = fsspec.filesystem("dir", path="./host/repo")
            >>> interface = Base(fs)

        Examples:
            >>> interface.sep
            '/'

        """
        return "/"

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

        ..
            >>> fs = fsspec.filesystem("dir", path="./host/repo")
            >>> interface = Base(fs)

        Examples:
            >>> interface.split("/")
            ('/', '')
            >>> interface.split("/file.txt")
            ('/', 'file.txt')
            >>> interface.split("/sub/")
            ('/sub/', '')
            >>> interface.split("/sub//file.txt")
            ('/sub/', 'file.txt')

        """
        path = self._path(path)
        root = self.sep.join(path.split(self.sep)[:-1]) + self.sep
        basename = path.split(self.sep)[-1]

        return root, basename


def pbar(
    desc: str,
    verbose: bool,
) -> tqdm.tqdm:
    r"""Progress bar for fsspec callbacks.

    Args:
        desc: description of progress bar
        verbose: if ``False`` don't show progress bar

    """
    return fsspec.callbacks.TqdmCallback(
        tqdm_kwargs={
            "desc": desc,
            "disable": not verbose,
        },
        tqdm_cls=audeer.progress_bar,
    )
