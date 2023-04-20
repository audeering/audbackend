import os
import typing

import dohq_artifactory

import audfactory

from audbackend.core import utils
from audbackend.core.backend import Backend


class Artifactory(Backend):
    r"""Backend for Artifactory.

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

        self._artifactory = audfactory.path(self.host)
        self._repo = self._artifactory.find_repository_local(self.repository)

        if self._repo is None:
            # create repository if it does not exist
            self._repo = dohq_artifactory.RepositoryLocal(
                self._artifactory,
                self.repository,
                packageType=dohq_artifactory.RepositoryLocal.GENERIC,
            )
            self._repo.create()

    def _checksum(
            self,
            path: str,
            version: str,
    ) -> str:
        r"""MD5 checksum of file on backend."""
        path = self._expand(path)
        path = self._path(path, version)
        return audfactory.checksum(path)

    def _collapse(
            self,
            path,
    ):
        r"""Convert to virtual path

        <host>/<repository>/<path>
        ->
        <path>

        """
        path = path[len(self._repo.path) + 1:]  # remove host and repo
        path = path.replace('/', self.sep)
        return path

    def _exists(
            self,
            path: str,
            version: str,
    ) -> bool:
        r"""Check if file exists on backend."""
        path = self._expand(path)
        path = self._path(path, version)
        path = audfactory.path(path)
        return path.exists()

    def _expand(
            self,
            path: str,
    ) -> str:
        r"""Convert to backend path.

        <path>
        ->
        <host>/<repository>/<path>

        """
        path = path.replace(self.sep, '/')
        if not path.startswith('/'):
            path = '/' + path
        path = f'{self._repo.path}{path}'
        return path

    def _get_file(
            self,
            src_path: str,
            dst_path: str,
            version: str,
            verbose: bool,
    ):
        r"""Get file from backend."""
        src_path = self._expand(src_path)
        src_path = self._path(src_path, version)
        audfactory.download(src_path, dst_path, verbose=verbose)

    def _ls(
            self,
            folder: str,
    ):
        r"""List all files under folder.

        If folder does not exist an error should be raised.

        """

        folder = self._expand(folder)
        folder = audfactory.path(folder)

        if not folder.exists():
            utils.raise_file_not_found_error(str(folder))

        paths = [str(x) for x in folder.glob("**/*") if x.is_file()]

        # <host>/<repository>/<folder>/<name>
        # ->
        # (<folder>/<name>, <version>)

        result = []
        for full_path in paths:

            # remove host and repo
            full_path = full_path[len(str(self._repo.path)):]
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

        <root>/<name>
        ->
        <host>/<repository>/<root>/<version>/<name>

        """
        root, name = self.split(path)
        path = f'{root}/{version}/{name}'
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
        r"""Versions of a file.

        If path does not exist an error should be raised.

        """
        folder, _ = self.split(path)
        folder = self._expand(folder)
        folder = audfactory.path(folder)

        vs = [os.path.basename(str(f)) for f in folder if f.is_dir]

        # filter out versions of files with different extension
        vs = [v for v in vs if self._exists(path, v)]

        if not vs:
            utils.raise_file_not_found_error(path)

        return vs
