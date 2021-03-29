import errno
import glob
import os
import re
import shutil
import tempfile
import typing

import audfactory
import audeer

from audbackend.core import utils


BACKEND_ALLOWED_CHARS = '[A-Za-z0-9/._-]+'


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
    ) -> str:
        r"""Get MD5 checksum for file on backend.

        Args:
            path: path to file on backend
            version: version string

        Returns:
            MD5 checksum

        Raises:
            FileNotFoundError: if file does not exist on backend

        """
        backend_path = self.path(path, version)

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
    ) -> bool:
        r"""Check if file exists on backend.

        Args:
            path: path to file on backend
            version: version string

        Returns:
            ``True`` if file exists

        """
        path = self.path(path, version)
        return self._exists(path)

    def get_archive(
            self,
            src_path: str,
            dst_root: str,
            version: str,
    ) -> typing.List[str]:
        r"""Get archive from backend and extract.

        Args:
            src_path: path to archive on backend without extension,
                e.g. ``media/archive1``
            dst_root: local destination directory
            version: version string

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
            self.get_file(remote_archive, local_archive, version)
            return audeer.extract_archive(local_archive, dst_root)

    def _get_file(
            self,
            src_path: str,
            dst_path: str,
    ) -> str:  # pragma: no cover
        r"""Get file from backend."""
        raise NotImplementedError()

    def get_file(
            self,
            src_path: str,
            dst_path: str,
            version: str,
    ):
        r"""Get file from backend.

        Args:
            src_path: path to file on backend
            dst_path: destination path to local file
            version: version string

        Returns:
            full path to local file

        Raises:
            FileNotFoundError: if file does not exist on backend

        """
        src_path = self.path(src_path, version)
        if not self._exists(src_path):
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), src_path,
            )

        dst_path = audeer.safe_path(dst_path)
        audeer.mkdir(os.path.dirname(dst_path))

        self._get_file(src_path, dst_path)

    def _glob(
            self,
            pattern: str,
    ) -> typing.List[str]:  # pragma: no cover
        r"""Return matching files names."""
        raise NotImplementedError()

    def glob(
            self,
            pattern: str,
    ) -> typing.List[str]:
        r"""Return matching files names.

        Use ``'**'`` to scan into sub-directories.

        Args:
            pattern: pattern string

        Returns:
            matching files on backend

        """
        return self._glob(pattern)

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
        return self.sep.join([path] + [p for p in paths])

    def latest_version(
            self,
            path: str,
    ) -> str:
        r"""Latest version of a file.

        Args:
            path: relative path to file in repository

        Returns:
            version string

        Raises:
            RuntimeError: if file does not exist on backend

        """
        vs = self.versions(path)
        if not vs:
            raise RuntimeError(
                f"Cannot find a version for "
                f"'{path}' in "
                f"'{self.repository}'.",
            )
        return vs[-1]

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
    ) -> str:
        r"""File path on backend.

        This converts a file path on the backend
        from the form it is presented to a user
        to the actual path on the backend storage.

        Args:
            path: relative path to file in repository
            version: version string

        Returns:
            file path on backend

        Example:
            >>> backend = FileSystem('~/my-host', 'data')
            >>> path = backend.path('media/archive1.zip', '1.0.0')
            >>> os.path.basename(path)
            'archive1-1.0.0.zip'

        """
        allowed_chars = re.compile(BACKEND_ALLOWED_CHARS)
        if allowed_chars.fullmatch(path) is None:
            raise ValueError(
                f"Invalid path name '{path}', "
                f"allowed characters are '{BACKEND_ALLOWED_CHARS}'."
            )
        folder, file = self.split(path)
        name, ext = os.path.splitext(file)
        return self._path(folder, name, ext, version)

    def put_archive(
            self,
            src_root: str,
            files: typing.Union[str, typing.Sequence[str]],
            dst_path: str,
            version: str,
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

        Returns:
            archive path on backend

        Raises:
            FileNotFoundError: if one or more files do not exist

        """
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
            audeer.create_archive(src_root, files, archive)
            remote_archive = dst_path + '.zip'
            return self.put_file(archive, remote_archive, version)

    def _put_file(
            self,
            src_path: str,
            dst_path: str,
    ):  # pragma: no cover
        r"""Put file to backend."""
        raise NotImplementedError()

    def put_file(
            self,
            src_path: str,
            dst_path: str,
            version: str,
    ):
        r"""Put file on backend.

        The operation is silently skipped,
        if a file with the same checksum
        already exists on the backend.

        Args:
            src_path: path to local file
            dst_path: path to file on backend
            version: version string

        Returns:
            file path on backend

        Raises:
            FileNotFoundError: if local file does not exist

        """
        if not os.path.exists(src_path):
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), src_path,
            )

        dst_path = self.path(dst_path, version)

        # skip if file with same checksum exists on backend
        skip = self._exists(dst_path) and \
            utils.md5(src_path) == self._checksum(dst_path)
        if not skip:
            self._put_file(src_path, dst_path)

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
    ) -> str:
        r"""Remove file from backend.

        Args:
            path: path to file on backend
            version: version string

        Returns:
            path of removed file on backend

        Raises:
            FileNotFoundError: if file does not exist on backend

        """
        path = self.path(path, version)
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
    ) -> typing.List[str]:
        r"""Versions of a file.

        Args:
            path: path to file on backend

        Returns:
            list of versions in ascending order

        """
        folder, file = self.split(path)
        name = audeer.basename_wo_ext(file)
        vs = self._versions(folder, name)
        return audeer.sort_versions(vs)


class Artifactory(Backend):
    r"""Artifactory backend.

    Stores files and archives on Artifactory.

    Args:
        host: host address
        repository: repository name

    """

    def __init__(
            self,
            host,
            repository,
    ):
        super().__init__(host, repository)

    def _checksum(
            self,
            path: str,
    ) -> str:
        r"""MD5 checksum of file on backend."""
        return audfactory.checksum(path)

    def _path(
            self,
            folder: str,
            name: str,
            ext: str,
            version: str,
    ) -> str:
        r"""File path on backend."""
        server_url = audfactory.url(
            self.host,
            repository=self.repository,
            group_id=audfactory.path_to_group_id(folder),
            name=name,
            version=version,
        )
        return f'{server_url}/{name}-{version}{ext}'

    def _exists(
            self,
            path: str,
    ) -> bool:
        r"""Check if file exists on backend."""
        try:
            # Can lead to RuntimeError: 404 page not found
            return audfactory.path(path).exists()
        except RuntimeError:  # pragma: nocover
            return False

    def _get_file(
            self,
            src_path: str,
            dst_path: str,
    ):
        r"""Get file from backend."""
        audfactory.download(src_path, dst_path, verbose=False)

    def _glob(
            self,
            pattern: str,
    ) -> typing.List[str]:
        r"""Return matching files names."""
        url = audfactory.url(
            self.host,
            repository=self.repository,
        )
        path = audfactory.path(url)
        try:
            result = [str(x) for x in path.glob(pattern)]
        except RuntimeError:  # pragma: no cover
            result = []
        return result

    def _put_file(
            self,
            src_path: str,
            dst_path: str,
    ):
        r"""Put file to backend."""
        audfactory.deploy(src_path, dst_path)

    def _remove_file(
            self,
            path: str,
    ):
        r"""Remove file from backend."""
        audfactory.path(path).unlink()

    def _versions(
            self,
            folder: str,
            name: str,
    ) -> typing.List[str]:
        r"""Versions of a file."""
        group_id = audfactory.path_to_group_id(folder)
        return audfactory.versions(self.host, self.repository, group_id, name)


class FileSystem(Backend):
    r"""File system backend.

    Stores files and archives on a file system.

    Args:
        host: host directory
        repository: repository name

    """
    def __init__(
            self,
            host: str,
            repository: str,
    ):
        super().__init__(audeer.safe_path(host), repository)

    def _checksum(
            self,
            path: str,
    ) -> str:
        r"""MD5 checksum of file on backend."""
        return utils.md5(path)

    def _path(
            self,
            folder: str,
            name: str,
            ext: str,
            version: str,
    ) -> str:
        r"""File path on backend."""
        path = os.path.join(
            self.host,
            self.repository,
            folder.replace(self.sep, os.path.sep),
            name,
        )
        if version is not None:
            path = os.path.join(
                path,
                version,
                f'{name}-{version}{ext}',
            )
        return path

    def _exists(
            self,
            path: str,
    ) -> bool:
        r"""Check if file exists on backend."""
        return os.path.exists(path)

    def _get_file(
            self,
            src_path: str,
            dst_path: str,
    ):
        r"""Get file from backend."""
        shutil.copy(src_path, dst_path)

    def _glob(
            self,
            pattern: str,
    ) -> typing.List[str]:
        r"""Return matching files names."""
        pattern = pattern.replace(self.sep, os.path.sep)
        root = os.path.join(self.host, self.repository)
        path = os.path.join(root, pattern)
        return [os.path.join(root, p) for p in glob.glob(path, recursive=True)]

    def _put_file(
            self,
            src_path: str,
            dst_path: str,
    ):
        r"""Put file to backend."""
        audeer.mkdir(os.path.dirname(dst_path))
        shutil.copy(src_path, dst_path)

    def _remove_file(
            self,
            path: str,
    ):
        r"""Remove file from backend."""
        os.remove(path)

    def _versions(
            self,
            folder: str,
            name: str,
    ) -> typing.List[str]:
        r"""Versions of a file."""
        root = self._path(folder, name, '', None)
        vs = []
        if os.path.exists(root):
            vs = [
                v for v in os.listdir(root)
                if os.path.isdir(os.path.join(root, v))
            ]
        return vs


backends = {}
r"""Backend cache."""

backend_registry = {
    'file-system': FileSystem,
    'artifactory': Artifactory,
}
r"""Backend registry."""


def create(
        name: str,
        host: str,
        repository: str,
) -> Backend:
    r"""Create backend.

    Args:
        name: backend registry name
        host: host address
        repository: repository name

    Returns:
        backend object

    Raises:
        ValueError: if registry name does not exist

    """
    if name not in backend_registry:
        raise ValueError(
            'A backend class with name '
            f"'{name} "
            'does not exist.'
            "Use 'register_backend()' to register one."
        )

    if name not in backends:
        backends[name] = {}
    if host not in backends[name]:
        backends[name][host] = {}
    if repository not in backends[name][host]:
        backend = backend_registry[name]
        backends[name][host][repository] = backend(host, repository)
    return backends[name][host][repository]


def register(
        name: str,
        cls: typing.Type[Backend],
):
    r"""Register backend.

    If a backend with this name already exists,
    it will be overwritten.

    Args:
        name: backend registry name
        cls: backend class

    """
    backend_registry[name] = cls


register('artifactory', Artifactory)
register('file-system', FileSystem)
