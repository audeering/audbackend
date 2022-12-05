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
            version: typing.Optional[str],
            ext: str,
    ) -> str:
        r"""Convert to backend path.

        Format: <host>/<folder>/<version>/<name>-<version>.<ext>

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
            name = file[:-len(ext)]

        utils.check_path_ends_on_ext(path, ext)

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

    def _put_file(
            self,
            src_path: str,
            dst_path: str,
            version: str,
            ext: str,
            verbose: bool,
    ):
        r"""Put file to backend."""
        dst_path = self._path(dst_path, version, ext)
        audeer.mkdir(os.path.dirname(dst_path))
        shutil.copy(src_path, dst_path)

    def _remove_file(
            self,
            path: str,
            version: str,
            ext: str,
    ):
        r"""Remove file from backend."""
        path = self._path(path, version, ext)
        os.remove(path)

    def _versions(
            self,
            path: str,
            ext: str,
    ) -> typing.List[str]:
        r"""Versions of a file."""
        path = self._path(path, None, ext)
        root = os.path.join(
            self.host,
            self.repository,
            path.replace(self.sep, os.path.sep),
        )
        if os.path.exists(root):
            vs = audeer.list_dir_names(root, basenames=True)
        else:
            vs = []
        return vs
