import glob
import os
import shutil
import typing

import audeer

from audbackend.core import utils
from audbackend.core.backend import Backend


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
