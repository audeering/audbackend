import glob
import os
import shutil
import typing

import audeer

from audbackend.core import utils
from audbackend.core.backend import Backend


class FileSystem(Backend):
    r"""File system backend.

    Store files and archives on a file system.

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
            version: str,
            ext: str,
    ) -> str:
        r"""MD5 checksum of file on backend."""
        path = self._path(path, version, ext)
        return utils.md5(path)

    def _exists(
            self,
            path: str,
            version: str,
            ext: str,
    ) -> bool:
        r"""Check if file exists on backend."""
        path = self._path(path, version, ext)
        return os.path.exists(path)

    def _folder(
            self,
            path: str,
            ext: str,
    ) -> str:
        r"""Convert to backend folder.

        <folder>/<name>.<ext>
        ->
        <host>/<repository>/<folder>/<name>/

        """
        folder, file = self.split(path)
        name, ext = utils.splitext(file, ext)

        path = os.path.join(
            self.host,
            self.repository,
            folder.replace(self.sep, os.path.sep),
            name,
        )

        return path

    def _get_file(
            self,
            src_path: str,
            dst_path: str,
            version: str,
            ext: str,
            verbose: bool,
    ):
        r"""Get file from backend."""
        src_path = self._path(src_path, version, ext)
        shutil.copy(src_path, dst_path)

    def _glob(
            self,
            pattern: str,
            folder: typing.Optional[str],
    ) -> typing.List[str]:
        r"""Return matching files names."""
        if folder is None:
            folder = ''
        pattern = pattern.replace(self.sep, os.path.sep)
        folder = folder.replace(self.sep, os.path.sep)
        root = os.path.join(self.host, self.repository)
        path = os.path.join(root, folder, pattern)
        matches = glob.glob(path, recursive=True)
        return [os.path.join(root, folder, match) for match in matches]

    def _ls(
            self,
            path: str,
    ):
        r"""List content of path."""
        path = os.path.join(
            self.host,
            self.repository,
            path.replace(self.sep, os.path.sep),
        )
        return os.listdir(path)

    def _path(
            self,
            path: str,
            version: str,
            ext: str,
    ) -> str:
        r"""Convert to backend path.

        <folder>/<name>.<ext>
        ->
        <host>/<repository>/<folder>/<name>/<version>/<name>-<version>.<ext>

        """
        folder = self._folder(path, ext)
        name = os.path.basename(folder)
        path = os.path.join(
            folder,
            version,
            f'{name}-{version}{ext}',
        )
        return path

    def _put_file(
            self,
            src_path: str,
            dst_path: str,
            version: str,
            ext: str,
            verbose: bool,
    ) -> str:
        r"""Put file to backend."""
        skip = False

        # skip if file with same checksum already exists
        if self._exists(dst_path, version, ext):
            checksum = self._checksum(dst_path, version, ext)
            skip = utils.md5(src_path) == checksum

        dst_path = self._path(dst_path, version, ext)

        if not skip:
            audeer.mkdir(os.path.dirname(dst_path))
            shutil.copy(src_path, dst_path)

        return dst_path

    def _remove_file(
            self,
            path: str,
            version: str,
            ext: str,
    ) -> str:
        r"""Remove file from backend."""
        path = self._path(path, version, ext)
        os.remove(path)
        return path

    def _versions(
            self,
            path: str,
            ext: str,
    ) -> typing.List[str]:
        r"""Versions of a file."""
        folder = self._folder(path, ext)

        if os.path.exists(folder):
            vs = audeer.list_dir_names(
                folder,
                basenames=True,
            )
        else:
            vs = []

        # filter out versions of files with different extension
        vs = [v for v in vs if self._exists(path, v, ext)]

        return vs
