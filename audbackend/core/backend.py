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

    def __repr__(self) -> str:
        name = f'{self.__class__.__module__}.{self.__class__.__name__}'
        return str((name, self.host, self.repository))

    def _checksum(
            self,
            path: str,
            version: str,
            ext: str,
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
            ValueError: if ``path`` contains invalid character
            ValueError: if ``path`` does not end on file extension

        Example:
            >>> backend.checksum('folder/name.ext', '1.0.0')
            'd41d8cd98f00b204e9800998ecf8427e'

        """
        path, ext = utils.check_path_and_ext(path, ext)
        if not self._exists(path, version, ext):
            utils.raise_file_not_found_error(path, version=version)

        return self._checksum(path, version, ext=ext)

    def _exists(
            self,
            path: str,
            version: str,
            ext: str,
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

        Raises:
            ValueError: if ``path`` contains invalid character
            ValueError: if ``path`` does not end on file extension

        Example:
            >>> backend.exists('folder/name.ext', '1.0.0')
            True

        """
        path, ext = utils.check_path_and_ext(path, ext)

        return self._exists(path, version, ext)

    def get_archive(
            self,
            src_path: str,
            dst_root: str,
            version: str,
            *,
            tmp_root: str = None,
            verbose: bool = False,
    ) -> typing.List[str]:
        r"""Get archive from backend and extract.

        Args:
            src_path: path to archive on backend without extension,
                e.g. ``media/archive1``
            dst_root: local destination directory
            version: version string
            tmp_root: directory under which archive is temporarily extracted.
                Defaults to temporary directory of system
            verbose: show debug messages

        Returns:
            extracted files

        Raises:
            FileNotFoundError: if archive does not exist on backend
            FileNotFoundError: if ``tmp_root`` does not exist
            ValueError: if ``src_path`` contains invalid character

        Example:
            >>> dst_root = audeer.path(tmp, 'dst')
            >>> backend.get_archive('folder/name', dst_root, '1.0.0')
            ['src.pth']

        """
        ext = '.zip'
        src_path += ext
        src_path, ext = utils.check_path_and_ext(src_path, ext)

        with tempfile.TemporaryDirectory(dir=tmp_root) as tmp:

            tmp_root = audeer.path(tmp, os.path.basename(dst_root))
            local_archive = os.path.join(
                tmp_root,
                os.path.basename(src_path),
            )
            self.get_file(
                src_path,
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
            version: str,
            ext: str,
            verbose: bool,
    ):  # pragma: no cover
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
    ) -> str:
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
            ValueError: if ``src_path`` contains invalid character
            ValueError: if ``src_path`` does not end on file extension

        Example:
            >>> dst_path = audeer.path(tmp, 'dst.pth')
            >>> os.path.exists(dst_path)
            False
            >>> _ = backend.get_file('folder/name.ext', dst_path, '1.0.0')
            >>> os.path.exists(dst_path)
            True

        """
        path, ext = utils.check_path_and_ext(src_path, ext)
        if not self._exists(src_path, version, ext):
            utils.raise_file_not_found_error(src_path, version=version)

        dst_path = audeer.safe_path(dst_path)
        audeer.mkdir(os.path.dirname(dst_path))

        self._get_file(src_path, dst_path, version, ext, verbose)

        return dst_path

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

        Raises:
            ValueError: if joined path contains invalid character

        Example:
            >>> backend.join('folder', 'name.ext')
            'folder/name.ext'

        """
        paths = [path] + [p for p in paths]
        # skip part if '' or None
        paths = [path for path in paths if path]
        path = self.sep.join(paths)

        utils.check_path_for_allowed_chars(path)

        return path

    def latest_version(
            self,
            path: str,
            *,
            ext: str = None,
    ) -> str:
        r"""Latest version of a file.

        Args:
            path: path to file on backend
            ext: file extension, if ``None`` uses characters after last dot

        Returns:
            version string

        Raises:
            RuntimeError: if file does not exist on backend
            ValueError: if ``path`` contains invalid character
            ValueError: if ``path`` does not end on file extension

        Example:
            >>> backend.latest_version('folder/name.ext')
            '2.0.0'

        """
        path, ext = utils.check_path_and_ext(path, ext)

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
            folder: str,
    ) -> typing.List[typing.Tuple[str, str, str]]:  # pragma: no cover
        r"""List all files under folder.

        Return an empty list if no files match or folder does not exist.

        """
        raise NotImplementedError()

    def ls(
            self,
            folder: str = '/',
            *,
            latest_version: bool = False,
    ) -> typing.List[typing.Tuple[str, str, str]]:
        r"""List all files under folder.

        Returns a sorted list of tuples
        with path, extension and version.
        When ``folder`` is set to the
        root of the backend (``'/'``)
        a (possibly empty) list with
        all files on the backend is returned.

        Args:
            folder: folder on backend
            latest_version: if multiple versions of a file exist,
                only include the latest

        Returns:
            list of tuples (path, extension, version)

        Raises:
            FileNotFoundError: if ``folder`` does not exist
            ValueError: if ``folder`` contains invalid character

        Example:
            >>> backend.ls('folder')[:2]
            [('folder/name.ext', '.ext', '1.0.0'), ('folder/name.ext', '.ext', '2.0.0')]
            >>> backend.ls('folder', latest_version=True)[:1]
            [('folder/name.ext', '.ext', '2.0.0')]

        """  # noqa: E501
        utils.check_path_for_allowed_chars(folder)
        if not folder.endswith('/'):
            folder += '/'
        paths = self._ls(folder)
        paths = sorted(paths)

        if len(paths) == 0:
            if folder == '/':
                # special case that there are no files on the backend
                return []
            else:
                utils.raise_file_not_found_error(folder)

        if latest_version:
            # d[(path, ext)] = ['1.0.0', '2.0.0']
            d = {}
            for p, e, v in paths:
                key = (p, e)
                if key not in d:
                    d[key] = []
                d[key].append(v)
            # d[(path, ext)] = '2.0.0'
            for key, vs in d.items():
                d[key] = audeer.sort_versions(vs)[-1]
            # [(path, ext, '2.0.0')]
            paths = [(p, e, v) for (p, e), v in d.items()]

        return paths

    def put_archive(
            self,
            src_root: str,
            files: typing.Union[str, typing.Sequence[str]],
            dst_path: str,
            version: str,
            *,
            tmp_root: str = None,
            verbose: bool = False,
    ):
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
            tmp_root: directory under which archive is temporarily created.
                Defaults to temporary directory of system
            verbose: show debug messages

        Raises:
            FileNotFoundError: if one or more files do not exist
            FileNotFoundError: if ``tmp_root`` does not exist
            ValueError: if ``dst_path`` contains invalid character

        Example:
            >>> backend.exists('folder/name.zip', '2.0.0')
            False
            >>> files = ['src.pth']
            >>> backend.put_archive(tmp, files, 'folder/name', '2.0.0')
            >>> backend.exists('folder/name.zip', '2.0.0')
            True

        """
        ext = '.zip'
        dst_path += ext
        dst_path, ext = utils.check_path_and_ext(dst_path, ext)
        src_root = audeer.safe_path(src_root)

        if isinstance(files, str):
            files = [files]

        for file in files:
            path = os.path.join(src_root, file)
            if not os.path.exists(path):
                utils.raise_file_not_found_error(path)

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
                version,
                verbose=verbose,
            )

    def _put_file(
            self,
            src_path: str,
            dst_path: str,
            version: str,
            ext: str,
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
            ValueError: if ``dst_path`` contains invalid character
            ValueError: if ``dst_path`` does not end on file extension

        Example:
            >>> backend.exists('folder/name.ext', '3.0.0')
            False
            >>> src_path = audeer.path(tmp, 'src.pth')
            >>> backend.put_file(src_path, 'folder/name.ext', '3.0.0')
            >>> backend.exists('folder/name.ext', '3.0.0')
            True

        """
        dst_path, ext = utils.check_path_and_ext(dst_path, ext)
        if not os.path.exists(src_path):
            utils.raise_file_not_found_error(src_path)

        # skip if file with same checksum already exists
        if not (
            self._exists(dst_path, version, ext)
            and self._checksum(dst_path, version, ext) == utils.md5(src_path)
        ):
            self._put_file(
                src_path,
                dst_path,
                version,
                ext,
                verbose,
            )

    def _remove_file(
            self,
            path: str,
            version: str,
            ext: str,
    ):  # pragma: no cover
        r"""Remove file from backend."""
        raise NotImplementedError()

    def remove_file(
            self,
            path: str,
            version: str,
            *,
            ext: str = None,
    ):
        r"""Remove file from backend.

        Args:
            path: path to file on backend
            version: version string
            ext: file extension, if ``None`` uses characters after last dot

        Raises:
            FileNotFoundError: if file does not exist on backend
            ValueError: if ``path`` contains invalid character
            ValueError: if ``path`` does not end on file extension

        Example:
            >>> backend.exists('folder/name.ext', '1.0.0')
            True
            >>> backend.remove_file('folder/name.ext', '1.0.0')
            >>> backend.exists('folder/name.ext', '1.0.0')
            False

        """
        path, ext = utils.check_path_and_ext(path, ext)
        if not self._exists(path, version, ext):
            utils.raise_file_not_found_error(path, version=version)

        path = self._remove_file(path, version, ext)

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

        Raises:
            ValueError: if ``path`` contains invalid character

        Example:
            >>> backend.split('folder/name.ext')
            ('folder', 'name.ext')

        """
        utils.check_path_for_allowed_chars(path)

        folder = self.sep.join(path.split(self.sep)[:-1])
        basename = path.split(self.sep)[-1]

        return folder, basename

    def _versions(
            self,
            path: str,
            ext: str,
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

        Raises:
            ValueError: if ``path`` contains invalid character
            ValueError: if ``path`` does not end on file extension

        Example:
            >>> backend.versions('folder/name.ext')
            ['1.0.0', '2.0.0']

        """
        path, ext = utils.check_path_and_ext(path, ext)

        vs = self._versions(path, ext)

        return audeer.sort_versions(vs)
