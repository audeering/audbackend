import errno
import os
import tempfile
import typing

import audeer

from audbackend.core import utils


class Backend:
    r"""Abstract backend.

    A backend stores files and archives.

    Args:
        host: host address
        repository: repository name

    """
    def __init__(
            self,
            host: str,
            repository: str,
    ):
        self.host = host
        r"""Host path."""
        self.repository = repository
        r"""Repository name."""

    def _checksum(
            self,
            path: str,
    ) -> str:  # pragma: no cover
        r"""MD5 checksum of file on backend."""
        raise NotImplementedError()

    def checksum(
            self,
            path: str,
            version: str,
            *,
            ext: str = None,
    ) -> str:
        r"""Get MD5 checksum for file on backend.

        Args:
            path: path to file on backend
            version: version string
            ext: file extension, if ``None`` uses characters after last dot

        Returns:
            MD5 checksum

        Raises:
            FileNotFoundError: if file does not exist on backend

        """
        backend_path = self.path(path, version, ext=ext)

        if not self._exists(backend_path):
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), path,
            )

        return self._checksum(backend_path)

    def _exists(
            self,
            path: str,
    ) -> bool:  # pragma: no cover
        r"""Check if file exists on backend."""
        raise NotImplementedError()

    def exists(
            self,
            path: str,
            version: str,
            *,
            ext: str = None,
    ) -> bool:
        r"""Check if file exists on backend.

        Args:
            path: path to file on backend
            version: version string
            ext: file extension, if ``None`` uses characters after last dot

        Returns:
            ``True`` if file exists

        """
        path = self.path(path, version, ext=ext)
        return self._exists(path)

    def get_archive(
            self,
            src_path: str,
            dst_root: str,
            version: str,
            *,
            verbose: bool = False,
    ) -> typing.List[str]:
        r"""Get archive from backend and extract.

        Args:
            src_path: path to archive on backend without extension,
                e.g. ``media/archive1``
            dst_root: local destination directory
            version: version string
            verbose: show debug messages

        Returns:
            extracted files

        Raises:
            FileNotFoundError: if archive does not exist on backend

        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = os.path.join(tmp, os.path.basename(dst_root))
            remote_archive = src_path + '.zip'
            local_archive = os.path.join(
                tmp_root,
                os.path.basename(remote_archive),
            )
            self.get_file(
                remote_archive,
                local_archive,
                version,
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
    ) -> str:  # pragma: no cover
        r"""Get file from backend."""
        raise NotImplementedError()

    def get_file(
            self,
            src_path: str,
            dst_path: str,
            version: str,
            *,
            ext: str = None,
            verbose: bool = False,
    ):
        r"""Get file from backend.

        Args:
            src_path: path to file on backend
            dst_path: destination path to local file
            version: version string
            ext: file extension, if ``None`` uses characters after last dot
            verbose: show debug messages

        Returns:
            full path to local file

        Raises:
            FileNotFoundError: if file does not exist on backend

        """
        src_path = self.path(src_path, version, ext=ext)
        if not self._exists(src_path):
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), src_path,
            )

        dst_path = audeer.safe_path(dst_path)
        audeer.mkdir(os.path.dirname(dst_path))

        self._get_file(src_path, dst_path, verbose)

    def _glob(
            self,
            pattern: str,
            folder: typing.Optional[str],
    ) -> typing.List[str]:  # pragma: no cover
        r"""Return matching files names."""
        raise NotImplementedError()

    def glob(
            self,
            pattern: str,
            *,
            folder: str = None,
    ) -> typing.List[str]:
        r"""Return matching files names.

        Use ``'**'`` to scan into sub-directories.

        Args:
            pattern: pattern string
            folder: search under this folder

        Returns:
            matching files on backend

        """
        return self._glob(pattern, folder)

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

        """
        paths = [path] + [p for p in paths]
        # skip part if '' or None
        paths = [path for path in paths if path]
        return self.sep.join(paths)

    def latest_version(
            self,
            path: str,
            *,
            ext: str = None,
    ) -> str:
        r"""Latest version of a file.

        Args:
            path: relative path to file in repository
            ext: file extension, if ``None`` uses characters after last dot

        Returns:
            version string

        Raises:
            RuntimeError: if file does not exist on backend

        """
        vs = self.versions(path, ext=ext)
        if not vs:
            raise RuntimeError(
                f"Cannot find a version for "
                f"'{path}' in "
                f"'{self.repository}'.",
            )
        return vs[-1]

    def _ls(
            self,
            path: str,
    ) -> typing.List:  # pragma: no cover
        r"""List content of path."""
        raise NotImplementedError()

    def ls(
            self,
            path: str,
    ) -> typing.List:
        r"""List content of path.

        Args:
            path: relative path to folder in repository

        Returns:
            folder content

        Raises:
            RuntimeError: if ``path`` does not exist on backend

        """
        return sorted(self._ls(path))

    def _path(
            self,
            folder: str,
            name: str,
            ext: str,
            version: str,
    ) -> str:  # pragma: no cover
        r"""File path on backend."""
        raise NotImplementedError()

    def path(
            self,
            path: str,
            version: str,
            *,
            ext: str = None,
    ) -> str:
        r"""File path on backend.

        This converts a file path on the backend
        from the form it is presented to a user
        to the actual path on the backend storage.

        Args:
            path: relative path to file in repository
            version: version string
            ext: file extension, if ``None`` uses characters after last dot

        Returns:
            file path on backend

        Raises:
            ValueError: if ``path`` contains invalid character
            ValueError: if ``path`` does not end on file extension

        Example:
            >>> import audbackend
            >>> backend = audbackend.FileSystem('~/my-host', 'data')
            >>> path = backend.path('media/archive1.zip', '1.0.0')
            >>> os.path.basename(path)
            'archive1-1.0.0.zip'
            >>> path = backend.path(
            ...     'media/archive1.tar.gz',
            ...     '1.0.0',
            ...     ext='tar.gz',
            ... )
            >>> os.path.basename(path)
            'archive1-1.0.0.tar.gz'

        """
        utils.check_path_for_allowed_chars(path)
        folder, file = self.split(path)
        if ext is None:
            name, ext = os.path.splitext(file)
        elif ext == '':
            name = file
        else:
            if not ext.startswith('.'):
                ext = '.' + ext
            if not path.endswith(ext):
                raise ValueError(
                    f"Invalid path name '{path}', "
                    f"does not end on '{ext}'."
                )
            name = file[:-len(ext)]
        return self._path(folder, name, ext, version)

    def put_archive(
            self,
            src_root: str,
            files: typing.Union[str, typing.Sequence[str]],
            dst_path: str,
            version: str,
            *,
            verbose: bool = False,
    ) -> str:
        r"""Create archive and put on backend.

        The operation is silently skipped,
        if an archive with the same checksum
        already exists on the backend.

        Args:
            src_root: local root directory where files are located.
                Only folders and files below ``src_root``
                will be included into the archive
            files: relative path to file(s) from ``src_root``
            dst_path: path to archive on backend without extension,
                e.g. ``media/archive1``
            version: version string
            verbose: show debug messages

        Returns:
            archive path on backend

        Raises:
            FileNotFoundError: if one or more files do not exist

        """
        utils.check_path_for_allowed_chars(dst_path)
        src_root = audeer.safe_path(src_root)

        if isinstance(files, str):
            files = [files]

        for file in files:
            path = os.path.join(src_root, file)
            if not os.path.exists(path):
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), path,
                )

        with tempfile.TemporaryDirectory() as tmp:
            _, archive_name = self.split(dst_path)
            archive = os.path.join(tmp, f'{archive_name}-{version}.zip')
            audeer.create_archive(
                src_root,
                files,
                archive,
                verbose=verbose,
            )
            remote_archive = dst_path + '.zip'
            return self.put_file(
                archive,
                remote_archive,
                version,
                verbose=verbose,
            )

    def _put_file(
            self,
            src_path: str,
            dst_path: str,
            verbose: bool,
    ):  # pragma: no cover
        r"""Put file to backend."""
        raise NotImplementedError()

    def put_file(
            self,
            src_path: str,
            dst_path: str,
            version: str,
            *,
            ext: str = None,
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
            ext: file extension, if ``None`` uses characters after last dot
            verbose: show debug messages

        Returns:
            file path on backend

        Raises:
            FileNotFoundError: if local file does not exist

        """
        if not os.path.exists(src_path):
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), src_path,
            )

        dst_path = self.path(dst_path, version, ext=ext)

        # skip if file with same checksum exists on backend
        skip = self._exists(dst_path) and \
            utils.md5(src_path) == self._checksum(dst_path)
        if not skip:
            self._put_file(src_path, dst_path, verbose)

        return dst_path

    def _remove_file(
            self,
            path: str,
    ):  # pragma: no cover
        r"""Remove file from backend."""
        raise NotImplementedError()

    def remove_file(
            self,
            path: str,
            version: str,
            *,
            ext: str = None,
    ) -> str:
        r"""Remove file from backend.

        Args:
            path: path to file on backend
            version: version string
            ext: file extension, if ``None`` uses characters after last dot

        Returns:
            path of removed file on backend

        Raises:
            FileNotFoundError: if file does not exist on backend

        """
        path = self.path(path, version, ext=ext)
        if not self._exists(path):
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), path,
            )

        self._remove_file(path)

        return path

    @property
    def sep(self) -> str:
        r"""File separator on backend."""
        return '/'

    def split(
            self,
            path: str,
    ) -> typing.Tuple[str, str]:
        r"""Split path on backend into folder and basename.

        Args:
            path: path containing :attr:`Backend.sep` as separator

        Returns:
            tuple containing (folder, basename)

        """
        folder = self.sep.join(path.split(self.sep)[:-1])
        basename = path.split(self.sep)[-1]
        return folder, basename

    def _versions(
            self,
            folder: str,
            name: str,
    ) -> typing.List[str]:  # pragma: no cover
        r"""Versions of a file."""
        raise NotImplementedError()

    def versions(
            self,
            path: str,
            *,
            ext: str = None,
    ) -> typing.List[str]:
        r"""Versions of a file.

        Args:
            path: path to file on backend
            ext: file extension, if ``None`` uses characters after last dot

        Returns:
            list of versions in ascending order

        """
        folder, file = self.split(path)
        name = audeer.basename_wo_ext(file, ext=ext)
        vs = self._versions(folder, name)
        return audeer.sort_versions(vs)
