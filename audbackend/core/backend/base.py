from collections.abc import Sequence
import fnmatch
import inspect
import os
import tempfile

import audeer

from audbackend.core import utils
from audbackend.core.errors import BackendError


backend_not_opened_error = (
    "Call 'Backend.open()' to establish a connection to the repository first."
)


class Base:
    r"""Backend base class.

    Derive from this class to implement a new backend.

    """

    def __init__(
        self,
        host: str,
        repository: str,
        *,
        authentication: object = None,
    ):
        self.host = host
        r"""Host path."""
        self.repository = repository
        r"""Repository name."""
        self.authentication = authentication
        r"""Object used for authentication, e.g. username, password tuple."""
        self.opened = False
        r"""If a connection to the repository has been established."""

    def __enter__(self):
        r"""Open connection via context manager."""
        self.open()
        return self

    def __exit__(self, type, value, traceback):
        r"""Close connection via context manager."""
        self.close()

    def __repr__(self) -> str:  # noqa: D105
        name = self.__class__.__name__
        return f"audbackend.backend.{name}('{self.host}', '{self.repository}')"

    def _assert_equal_checksum(
        self,
        *,
        path: str,
        path_is_local: bool,
        path_ref: str,
        path_ref_is_local: bool,
    ):
        r"""Assert checksums are equal.

        Compare the MD5 sum of a file
        (``path``)
        to the MD5 sum of a reference file
        (``path_ref``).
        If check fails,
        ``path`` is removed
        and an error is raised.

        Both ``path`` and ``path_ref``
        can be local files,
        or stored on any backend.

        Args:
            path: path to a file.
                Its MD5 sum is compared
                to a reference one,
                calculated from ``path_ref``
            path_is_local: if ``True``,
                assumes ``path`` is stored on local machine
            path_ref: path to a file.
                Its MD5 sum is used as reference
            path_ref_is_local: if ``True``,
                assumes ``path_ref`` is stored on local machine

        Raises:
            InterruptedError: if the MD5 sums do not match

        """
        md5 = audeer.md5(path) if path_is_local else self.checksum(path)
        md5_ref = audeer.md5(path_ref) if path_ref_is_local else self.checksum(path_ref)

        if md5 != md5_ref:
            if path_is_local:
                os.remove(path)
                location = "local file system"
            else:
                self.remove_file(path)
                location = "backend"

            raise InterruptedError(
                f"Execution is interrupted because "
                f"{path} "
                f"has checksum "
                f"'{md5}' "
                "when the expected checksum is "
                f"'{md5_ref}'. "
                f"The file has been removed from the "
                f"{location}."
            )

    def _checksum(
        self,
        path: str,
    ) -> str:  # pragma: no cover
        r"""MD5 checksum of file on backend."""
        raise NotImplementedError()

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

        """
        if not self.opened:
            raise RuntimeError(backend_not_opened_error)
        path = utils.check_path(path)
        return utils.call_function_on_backend(
            self._checksum,
            path,
        )

    def _close(
        self,
    ):  # pragma: no cover
        r"""Close connection to repository.

        An error should be raised,
        if the connection to the backend
        cannot be closed.

        """
        pass

    def close(
        self,
    ):
        r"""Close connection to backend.

        Raises:
            BackendError: if an error is raised on the backend

        """
        if self.opened:
            utils.call_function_on_backend(self._close)
            self.opened = False

    def _copy_file(
        self,
        src_path: str,
        dst_path: str,
        verbose: bool,
    ):
        r"""Copy file on backend.

        A default implementation is provided,
        which temporarily gets the file from the backend
        and afterward puts it to the new location.
        It is recommended to overwrite the function
        if backend supports a native way to copy files.

        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = audeer.path(tmp, "~")
            tmp_path = self.get_file(src_path, tmp_path, verbose=verbose)
            self.put_file(tmp_path, dst_path, verbose=verbose)

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

        """
        if not self.opened:
            raise RuntimeError(backend_not_opened_error)

        src_path = utils.check_path(src_path)
        dst_path = utils.check_path(dst_path)

        if src_path != dst_path and (
            not self.exists(dst_path)
            or self.checksum(src_path) != self.checksum(dst_path)
        ):
            utils.call_function_on_backend(
                self._copy_file,
                src_path,
                dst_path,
                verbose,
            )

            if validate:
                self._assert_equal_checksum(
                    path=dst_path,
                    path_is_local=False,
                    path_ref=src_path,
                    path_ref_is_local=False,
                )

    def _create(
        self,
    ):  # pragma: no cover
        r"""Create a new repository.

        * If repository exists already an error should be raised

        """
        raise NotImplementedError()

    @classmethod
    def create(
        cls,
        host: str,
        repository: str,
        *,
        authentication: object = None,
    ):
        r"""Create repository.

        Creates ``repository``
        located at ``host``
        on the backend.

        Args:
            host: host address
            repository: repository name
            authentication: object used for authentication,
                e.g. a tuple with username and password

        Raises:
            BackendError: if an error is raised on the backend,
                e.g. repository exists already
                or cannot be created

        """
        signature = inspect.signature(cls)
        if "authentication" in signature.parameters:
            backend = cls(host, repository, authentication=authentication)
        else:
            backend = cls(host, repository)
        utils.call_function_on_backend(backend._create)

    def _date(
        self,
        path: str,
    ) -> str:  # pragma: no cover
        r"""Last modification date of file on backend.

        * Return empty string if date cannot be determined
        * Format should be '%Y-%m-%d'

        """
        raise NotImplementedError()

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

        """
        if not self.opened:
            raise RuntimeError(backend_not_opened_error)
        path = utils.check_path(path)
        return utils.call_function_on_backend(
            self._date,
            path,
        )

    def _delete(
        self,
    ):  # pragma: no cover
        r"""Delete repository and all its content."""
        raise NotImplementedError()

    @classmethod
    def delete(
        cls,
        host: str,
        repository: str,
        *,
        authentication: object = None,
    ):
        r"""Delete repository.

        Deletes ``repository``
        located at ``host``
        on the backend.

        Args:
            host: host address
            repository: repository name
            authentication: access token
                for possible authentication,
                e.g. username, password tuple

        Raises:
            BackendError: if an error is raised on the backend,
                e.g. repository does not exist

        """
        signature = inspect.signature(cls)
        if "authentication" in signature.parameters:
            backend = cls(host, repository, authentication=authentication)
        else:
            backend = cls(host, repository)
        utils.call_function_on_backend(backend._delete)

    def _exists(
        self,
        path: str,
    ) -> bool:  # pragma: no cover
        r"""Check if file exists on backend."""
        raise NotImplementedError()

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

        """
        if not self.opened:
            raise RuntimeError(backend_not_opened_error)
        path = utils.check_path(path)
        return utils.call_function_on_backend(
            self._exists,
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

        """
        if not self.opened:
            raise RuntimeError(backend_not_opened_error)

        src_path = utils.check_path(src_path)

        with tempfile.TemporaryDirectory(dir=tmp_root) as tmp:
            tmp_root = audeer.path(tmp, os.path.basename(dst_root))
            local_archive = os.path.join(
                tmp_root,
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

    def _get_file(
        self,
        src_path: str,
        dst_path: str,
        verbose: bool,
    ):  # pragma: no cover
        r"""Get file from backend."""
        raise NotImplementedError()

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

        """
        if not self.opened:
            raise RuntimeError(backend_not_opened_error)

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
                    self._get_file,
                    src_path,
                    tmp_path,
                    verbose,
                )
                audeer.move_file(tmp_path, dst_path)

            if validate:
                self._assert_equal_checksum(
                    path=dst_path,
                    path_is_local=True,
                    path_ref=src_path,
                    path_ref_is_local=False,
                )

        return dst_path

    def join(
        self,
        path: str,
        *paths,
    ) -> str:
        r"""Join to (sub-)path on backend.

        Args:
            path: first part of path
            *paths: additional parts of path

        Returns:
            path joined by :attr:`Backend.sep`

        Raises:
            ValueError: if ``path`` contains invalid character
                or does not start with ``'/'``,
                or if joined path contains invalid character

        """
        path = utils.check_path(path, allow_sub_path=True)

        paths = [path] + [p for p in paths]
        paths = [path for path in paths if path]  # remove empty or None
        path = self.sep.join(paths)

        path = utils.check_path(path, allow_sub_path=True)

        return path

    def _ls(
        self,
        path: str,
    ) -> list[str]:  # pragma: no cover
        r"""List all files under sub-path.

        If ``path`` does not exist
        an empty list can be returned.

        """
        raise NotImplementedError()

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

        """
        if not self.opened:
            raise RuntimeError(backend_not_opened_error)

        path = utils.check_path(path, allow_sub_path=True)

        if path.endswith("/"):  # find files under sub-path
            paths = utils.call_function_on_backend(
                self._ls,
                path,
                suppress_backend_errors=suppress_backend_errors,
                fallback_return_value=[],
            )

        else:  # find path
            if self.exists(path):
                paths = [path]
            else:
                paths = []

        if not paths:
            if path != "/" and not suppress_backend_errors:
                # if the path does not exist
                # we raise an error
                try:
                    raise utils.raise_file_not_found_error(path)
                except FileNotFoundError as ex:
                    raise BackendError(ex)

            return []

        paths = sorted(paths)

        if pattern:
            paths = [p for p in paths if fnmatch.fnmatch(os.path.basename(p), pattern)]

        return paths

    def _move_file(
        self,
        src_path: str,
        dst_path: str,
        verbose: bool,
    ):
        r"""Move file on backend.

        A default implementation is provided,
        which calls `:func:audbackend.Base.copy_file`
        and afterward removes the source file from the backend.
        It is recommended to overwrite the function
        if backend supports a native way to move files.

        """
        self.copy_file(src_path, dst_path, verbose=verbose)
        self.remove_file(src_path)

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

        """
        if not self.opened:
            raise RuntimeError(backend_not_opened_error)

        src_path = utils.check_path(src_path)
        dst_path = utils.check_path(dst_path)

        if src_path == dst_path:
            return

        if not self.exists(dst_path) or self.checksum(src_path) != self.checksum(
            dst_path
        ):
            if validate:
                self.copy_file(
                    src_path,
                    dst_path,
                    validate=True,
                    verbose=verbose,
                )
                self.remove_file(src_path)
            else:
                utils.call_function_on_backend(
                    self._move_file,
                    src_path,
                    dst_path,
                    verbose,
                )
        else:
            self.remove_file(src_path)

    def _open(
        self,
    ):  # pragma: no cover
        r"""Open connection to backend.

        If repository does not exist,
        or the backend cannot be opened,
        an error should be raised.

        """
        pass

    def open(
        self,
    ):
        r"""Open connection to backend.

        Repository must exist,
        use
        :func:`audbackend.backend.Base.create`
        to create it.
        Finally,
        use
        :func:`audbackend.backend.Base.close`
        to close the connection.
        Instead of explicitly calling
        :func:`audbackend.backend.Base.open`
        and
        :func:`audbackend.backend.Base.close`
        it is good practice to use a with_ statement.

        Raises:
            BackendError: if an error is raised on the backend,
                e.g. ``repository`` does not exist

        .. _with: https://docs.python.org/3/reference/compound_stmts.html#with

        """
        if not self.opened:
            utils.call_function_on_backend(self._open)
            self.opened = True

    def _owner(
        self,
        path: str,
    ) -> str:  # pragma: no cover
        r"""Owner of file on backend.

        * Return empty string if owner cannot be determined

        """
        raise NotImplementedError()

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

        """
        if not self.opened:
            raise RuntimeError(backend_not_opened_error)
        path = utils.check_path(path)
        return utils.call_function_on_backend(
            self._owner,
            path,
        )

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

        """
        if not self.opened:
            raise RuntimeError(backend_not_opened_error)

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

            self.put_file(
                archive,
                dst_path,
                validate=validate,
                verbose=verbose,
            )

    def _put_file(
        self,
        src_path: str,
        dst_path: str,
        checksum: str,
        verbose: bool,
    ):  # pragma: no cover
        r"""Put file to backend."""
        raise NotImplementedError()

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

        """
        if not self.opened:
            raise RuntimeError(backend_not_opened_error)

        dst_path = utils.check_path(dst_path)
        if not os.path.exists(src_path):
            utils.raise_file_not_found_error(src_path)
        elif os.path.isdir(src_path):
            raise utils.raise_is_a_directory(src_path)

        checksum = audeer.md5(src_path)

        # skip if file with same checksum already exists
        if not self.exists(dst_path) or self.checksum(dst_path) != checksum:
            utils.call_function_on_backend(
                self._put_file,
                src_path,
                dst_path,
                checksum,
                verbose,
            )

            if validate:
                self._assert_equal_checksum(
                    path=dst_path,
                    path_is_local=False,
                    path_ref=src_path,
                    path_ref_is_local=True,
                )

    def _remove_file(
        self,
        path: str,
    ):  # pragma: no cover
        r"""Remove file from backend."""
        raise NotImplementedError()

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
            RuntimeError: if backend was not opened

        """
        if not self.opened:
            raise RuntimeError(backend_not_opened_error)
        path = utils.check_path(path)
        utils.call_function_on_backend(
            self._remove_file,
            path,
        )

    @property
    def sep(self) -> str:
        r"""File separator on backend.

        Returns: file separator

        """
        return utils.BACKEND_SEPARATOR

    def split(
        self,
        path: str,
    ) -> tuple[str, str]:
        r"""Split path on backend into sub-path and basename.

        Args:
            path: path containing :attr:`Backend.sep` as separator

        Returns:
            tuple containing (root, basename)

        Raises:
            ValueError: if ``path`` does not start with ``'/'`` or
                does not match ``'[A-Za-z0-9/._-]+'``

        """
        path = utils.check_path(path, allow_sub_path=True)

        root = self.sep.join(path.split(self.sep)[:-1]) + self.sep
        basename = path.split(self.sep)[-1]

        return root, basename
