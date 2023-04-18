import os

import typing

import audfactory

from audbackend.core import utils
from audbackend.core.backend import Backend


class Artifactory(Backend):
    r"""Artifactory backend.

    Store files and archives on Artifactory.

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
            version: str,
    ) -> str:
        r"""MD5 checksum of file on backend."""
        path = self._path(path, version)
        return audfactory.checksum(path)

    def _exists(
            self,
            path: str,
            version: str,
    ) -> bool:
        r"""Check if file exists on backend."""
        path = self._path(path, version)
        path = audfactory.path(path)
        return path.exists()

    def _folder(
            self,
            folder: str,
    ) -> str:
        r"""Convert to backend folder.

        <folder>
        ->
        <host>/<repository>/<folder>

        """
        folder = folder.replace(self.sep, '/')
        if not folder.startswith('/'):
            folder = '/' + folder
        folder = f'{self.host}/{self.repository}{folder}'
        if not folder.endswith('/'):
            folder = folder + '/'
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
        audfactory.download(src_path, dst_path, verbose=verbose)

    def _ls(
            self,
            folder: str,
    ):
        r"""List all files under folder."""

        folder = self._folder(folder)
        folder = audfactory.path(folder)

        if not folder.exists():
            utils.raise_file_not_found_error(str(folder))

        paths = [str(x) for x in folder.glob("**/*") if x.is_file()]

        # <host>/<repository>/<folder>/<name>
        # ->
        # (<folder>/<name>, <version>)

        result = []
        for full_path in paths:

            host_repo = f'{self.host}/{self.repository}'
            full_path = full_path[len(host_repo) + 1:]  # remove host and repo
            full_path = full_path.replace('/', self.sep)
            tokens = full_path.split('/')

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
        path = f'{folder}{version}/{name}'

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
        audfactory.deploy(src_path, dst_path, verbose=verbose)

    def _remove_file(
            self,
            path: str,
            version: str,
    ):
        r"""Remove file from backend."""
        path = self._path(path, version)
        audfactory.path(path).unlink()

    def _versions(
            self,
            path: str,
    ) -> typing.List[str]:
        r"""Versions of a file."""
        folder, _ = self.split(path)
        folder = self._folder(folder)
        folder = audfactory.path(folder)

        try:
            vs = [os.path.basename(str(f)) for f in folder if f.is_dir]
        except (FileNotFoundError, RuntimeError):
            vs = []

        # filter out versions of files with different extension
        vs = [v for v in vs if self._exists(path, v)]

        return vs
