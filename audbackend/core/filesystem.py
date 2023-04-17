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
    ) -> str:
        r"""MD5 checksum of file on backend."""
        path = self._path(path, version)
        return utils.md5(path)

    def _exists(
            self,
            path: str,
            version: str,
    ) -> bool:
        r"""Check if file exists on backend."""
        path = self._path(path, version)
        return os.path.exists(path)

    def _folder(
            self,
            folder: str,
    ) -> str:
        r"""Convert to backend folder.

        <folder>
        ->
        <host>/<repository>/<folder>

        """
        folder = folder.replace(self.sep, os.path.sep)
        if folder.startswith(os.path.sep):
            folder = folder[1:]
        folder = os.path.join(self.host, self.repository, folder)
        return folder

    def _get_file(
            self,
            src_path: str,
            dst_path: str,
            version: str,
            verbose: bool,
    ):
        r"""Get file from backend."""
        src_path = self._path(src_path, version)
        shutil.copy(src_path, dst_path)

    def _ls(
            self,
            folder: str,
    ):
        r"""List all files under folder."""

        folder = self._folder(folder)

        if not os.path.exists(folder):
            utils.raise_file_not_found_error(folder)

        paths = audeer.list_file_names(folder, recursive=True)

        # <host>/<repository>/<folder>/<version>/<name>
        # ->
        # (<folder>/<name>, <version>)

        result = []
        for full_path in paths:

            host_repo = os.path.join(self.host, self.repository)
            full_path = full_path[len(host_repo) + 1:]  # remove host and repo
            full_path = full_path.replace(os.path.sep, self.sep)
            tokens = full_path.split(self.sep)

            name = tokens[-1]
            version = tokens[-2]
            folder = self.sep.join(tokens[:-2])
            path = self.join(folder, name)

            result.append((path, version))

        return result

    def _path(
            self,
            path: str,
            version: str,
    ) -> str:
        r"""Convert to backend path.

        <folder>/<name>
        ->
        <host>/<repository>/<folder>/<version>/<name>

        """
        folder, name = self.split(path)
        folder = self._folder(folder)
        path = os.path.join(folder, version, name)
        return path

    def _put_file(
            self,
            src_path: str,
            dst_path: str,
            version: str,
            verbose: bool,
    ):
        r"""Put file to backend."""
        dst_path = self._path(dst_path, version)
        audeer.mkdir(os.path.dirname(dst_path))
        shutil.copy(src_path, dst_path)

    def _remove_file(
            self,
            path: str,
            version: str,
    ):
        r"""Remove file from backend."""
        path = self._path(path, version)
        os.remove(path)

    def _versions(
            self,
            path: str,
    ) -> typing.List[str]:
        r"""Versions of a file."""
        folder, _ = self.split(path)
        folder = self._folder(folder)

        if os.path.exists(folder):
            vs = audeer.list_dir_names(
                folder,
                basenames=True,
            )
        else:
            vs = []

        # filter out versions of files with different extension
        vs = [v for v in vs if self._exists(path, v)]

        return vs
