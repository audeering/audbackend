import os
import shutil

import audeer

from audbackend.core import utils
from audbackend.core.backend import Backend


class FileSystem(Backend):
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
        if not os.path.exists(self._root):
            audeer.mkdir(self._root)

    def _checksum(
            self,
            path: str,
            version: str,
    ) -> str:
        r"""MD5 checksum of file on backend."""
        path = self._path(path, version)
        return utils.md5(path)

    def _collapse(
            self,
            path,
    ):
        r"""Convert to virtual path.

        <host>/<repository>/<path>
        ->
        <path>

        """
        path = path[len(self._root):]  # remove host and repo
        path = path.replace(os.path.sep, self.sep)
        return path

    def _delete(
            self,
    ):
        r"""Delete repository and all its content."""
        audeer.rmdir(self._root)

    def _exists(
            self,
            path: str,
            version: str,
    ) -> bool:
        r"""Check if file exists on backend."""
        path = self._path(path, version)
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
        path = path.replace(self.sep, os.path.sep)
        if path.startswith(os.path.sep):
            path = path[1:]
        path = os.path.join(self._root, path)
        return path

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
            path: str,
    ):
        r"""List all files under (sub-)path."""

        if path.endswith('/'):  # find files under sub-path

            path = self._expand(path)
            if not os.path.exists(path):
                utils.raise_file_not_found_error(path)
            paths = audeer.list_file_names(
                path,
                recursive=True,
                hidden=True,
            )

        else:  # find versions of path

            root, _ = self.split(path)
            root = self._expand(root)
            vs = audeer.list_dir_names(
                root,
                basenames=True,
                hidden=True,
            )

            # filter out other files with same root and version
            paths = [self._path(path, v) for v in vs if self._exists(path, v)]

            if not paths:
                utils.raise_file_not_found_error(path)

        # <host>/<repository>/<root>/<version>/<name>
        # ->
        # (<root>/<name>, <version>)

        result = []
        for p in paths:

            p = self._collapse(p)  # remove host and repo
            tokens = p.split(self.sep)

            name = tokens[-1]
            version = tokens[-2]
            path = self.sep.join(tokens[:-2])
            path = self.join(path, name)

            result.append((path, version))

        return result

    def _path(
            self,
            path: str,
            version: str,
    ) -> str:
        r"""Convert to backend path.

        <host>/<repository>/<root>/<name>
        ->
        <host>/<repository>/<root>/<version>/<name>

        """
        root, name = self.split(path)
        root = self._expand(root)
        path = os.path.join(root, version, name)
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
