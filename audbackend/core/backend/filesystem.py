import datetime
import os
import shutil

import audeer

from audbackend.core import utils
from audbackend.core.backend.base import Base


class FileSystem(Base):
    r"""Backend for file system.

    Args:
        host: host directory
        repository: repository name

    """

    def __init__(
        self,
        host: str,
        repository: str,
    ):
        super().__init__(host, repository)

        self._root = audeer.path(host, repository) + os.sep

    def _checksum(
        self,
        path: str,
    ) -> str:
        r"""MD5 checksum of file on backend."""
        path = self._expand(path)
        return audeer.md5(path)

    def _collapse(
        self,
        path,
    ):
        r"""Convert to virtual path.

        <host>/<repository>/<path>
        ->
        /<path>

        """
        path = path[len(self._root) - 1 :]  # remove host and repo
        path = path.replace(os.path.sep, self.sep)
        return path

    def _copy_file(
        self,
        src_path: str,
        dst_path: str,
        verbose: bool,
    ):
        r"""Copy file on backend."""
        src_path = self._expand(src_path)
        dst_path = self._expand(dst_path)
        audeer.mkdir(os.path.dirname(dst_path))
        shutil.copy(src_path, dst_path)

    def _create(
        self,
    ):
        r"""Create repository."""
        if os.path.exists(self._root):
            utils.raise_file_exists_error(self._root)

        audeer.mkdir(self._root)

    def _date(
        self,
        path: str,
    ) -> str:
        r"""Get last modification date of file on backend."""
        path = self._expand(path)
        date = os.path.getmtime(path)
        date = datetime.datetime.fromtimestamp(date)
        date = utils.date_format(date)
        return date

    def _delete(
        self,
    ):
        r"""Delete repository and all its content."""
        audeer.rmdir(self._root)

    def _exists(
        self,
        path: str,
    ) -> bool:
        r"""Check if file exists on backend."""
        path = self._expand(path)
        return os.path.exists(path)

    def _expand(
        self,
        path: str,
    ) -> str:
        r"""Convert to backend path.

        <path>
        ->
        <host>/<repository>/<path>

        """
        path = path.replace(self.sep, os.path.sep).removeprefix(os.path.sep)
        path = os.path.join(self._root, path)
        return path

    def _get_file(
        self,
        src_path: str,
        dst_path: str,
        verbose: bool,
    ):
        r"""Get file from backend."""
        src_path = self._expand(src_path)
        shutil.copy(src_path, dst_path)

    def _ls(
        self,
        path: str,
    ) -> list[str]:
        r"""List all files under sub-path."""
        path = self._expand(path)
        if not os.path.exists(path):
            return []

        paths = audeer.list_file_names(
            path,
            recursive=True,
            hidden=True,
        )
        paths = [self._collapse(path) for path in paths]

        return paths

    def _move_file(
        self,
        src_path: str,
        dst_path: str,
        verbose: bool,
    ):
        r"""Move file on backend."""
        src_path = self._expand(src_path)
        dst_path = self._expand(dst_path)
        audeer.mkdir(os.path.dirname(dst_path))
        audeer.move(src_path, dst_path)

    def _open(
        self,
    ):
        r"""Open connection to backend."""
        if not os.path.exists(self._root):
            utils.raise_file_not_found_error(self._root)

    def _owner(
        self,
        path: str,
    ) -> str:
        r"""Get owner of file on backend."""
        path = self._expand(path)
        owner = utils.file_owner(path)
        return owner

    def _put_file(
        self,
        src_path: str,
        dst_path: str,
        checksum: str,
        verbose: bool,
    ):
        r"""Put file to backend."""
        dst_path = self._expand(dst_path)
        audeer.mkdir(os.path.dirname(dst_path))
        shutil.copy(src_path, dst_path)

    def _remove_file(
        self,
        path: str,
    ):
        r"""Remove file from backend."""
        path = self._expand(path)
        os.remove(path)
