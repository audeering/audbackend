import dohq_artifactory
import os

import requests
import typing

import audfactory

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
        try:
            return audfactory.path(path).exists()
        except self._non_existing_path_error:
            return False

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

    def _glob(
            self,
            pattern: str,
            folder: typing.Optional[str],
    ) -> typing.List[str]:
        r"""Return matching files names."""
        if folder is not None:
            group_id = audfactory.path_to_group_id(folder)
        else:
            group_id = None
        url = audfactory.url(
            self.host,
            repository=self.repository,
            group_id=group_id,
        )
        path = audfactory.path(url)
        try:
            result = [str(x) for x in path.glob(pattern)]
        except self._non_existing_path_error:
            result = []
        return result

    def _ls(
            self,
            folder: str,
    ):
        r"""List all files under folder.

        Return an empty list if no files match or folder does not exist.

        """
        folder = self._folder(folder)

        folder = audfactory.path(folder)
        try:
            paths = [str(x) for x in folder.glob("**/*") if x.is_file()]
        except self._non_existing_path_error:  # pragma: nocover
            paths = []

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

    _non_existing_path_error = (
            RuntimeError,
            requests.exceptions.HTTPError,
            dohq_artifactory.exception.ArtifactoryException,
    )
    r"""Error expected for non-existing paths.

    If a user has no permission to a given path
    or the path does not exists
    :func:`audfactory.path` might return a
    ``RuntimeError``,
    ``requests.exceptions.HTTPError``
    for ``dohq_artifactory<0.8``
    or
    ``artifactory.exception.ArtifactoryException``
    for ``dohq_artifactory>=0.8``.
    So we better catch all of them.

    """
