import os
import typing

import artifactory
import dohq_artifactory

import audfactory

from audbackend.core import utils
from audbackend.core.backend import Backend


def _artifactory_path(
        path,
        username,
        apikey,
) -> artifactory.ArtifactoryPath:
    r"""Authenticate at Artifactory and get path object."""
    return artifactory.ArtifactoryPath(
        path,
        auth=(username, apikey),
    )


def _authentication(host) -> typing.Tuple[str, str]:
    """Look for username and API key.

    It first looks for the two environment variables
    ``ARTIFACTORY_USERNAME`` and
    ``ARTIFACTORY_API_KEY``.

    If some of them or both are missing,
    it tries to extract them from the
    :file:`~/.artifactory_python.cfg` config file.
    For that it removes ``http://`` or ``https://``
    from the beginning of ``url``
    and ``/`` from the end.
    E.g. for ``https://audeering.jfrog.io/artifactory/`
    it will look for an entry in the config file under
    ``[audeering.jfrog.io/artifactory]``.

    If it cannot find the config file
    or a matching entry in the config file
    it will set the username to ``anonymous``
    and the API key to an empty string.
    If your Artifactory server is configured
    to allow anonymous users
    you will be able to access the server this way.

    Args:
        host: host address

    Returns:
        username and API key

    """
    username = os.getenv('ARTIFACTORY_USERNAME', None)
    apikey = os.getenv('ARTIFACTORY_API_KEY', None)
    if apikey is None or username is None:  # pragma: no cover
        if host.startswith('http://'):
            host = host[7:]
        elif host.startswith('https://'):
            host = host[8:]
        if host.endswith('/'):
            host = host[:-1]
        config_entry = artifactory.get_global_config_entry(host)
        if config_entry is None:
            if username is None:
                username = 'anonymous'
            if apikey is None:
                apikey = ''
        else:
            if username is None:
                username = config_entry['username']
            if apikey is None:
                apikey = config_entry['password']
    return username, apikey


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

        self._username, self._apikey = _authentication(host)
        path = _artifactory_path(
            self.host,
            self._username,
            self._apikey,
        )
        self._repo = path.find_repository_local(self.repository)

    def _access(
            self,
    ):
        r"""Access existing repository."""
        if self._repo is None:
            utils.raise_file_not_found_error(str(self._repo.path))

    def _checksum(
            self,
            path: str,
            version: str,
    ) -> str:
        r"""MD5 checksum of file on backend."""
        path = self._path(path, version)
        return audfactory.checksum(str(path))

    def _collapse(
            self,
            path,
    ):
        r"""Convert to virtual path.

        <host>/<repository>/<path>
        ->
        /<path>

        """
        path = path[len(str(self._repo.path)) - 1:]
        path = path.replace('/', self.sep)
        return path

    def _create(
            self,
    ):
        r"""Access existing repository."""
        if self._repo is not None:
            utils.raise_file_exists_error(str(self._repo.path))

        path = _artifactory_path(
            self.host,
            self._username,
            self._apikey,
        )
        self._repo = dohq_artifactory.RepositoryLocal(
            path,
            self.repository,
            package_type=dohq_artifactory.RepositoryLocal.GENERIC,
        )
        self._repo.create()

    def _delete(
            self,
    ):
        r"""Delete repository and all its content."""
        self._repo.delete()

    def _exists(
            self,
            path: str,
            version: str,
    ) -> bool:
        r"""Check if file exists on backend."""
        path = self._path(path, version)
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
        if path.startswith('/'):
            path = path[1:]
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
        src_path = self._path(src_path, version)
        audfactory.download(str(src_path), dst_path, verbose=verbose)

    def _ls(
            self,
            path: str,
    ):
        r"""List all files under (sub-)path."""

        if path.endswith('/'):  # find files under sub-path

            path = self._expand(path)
            path = _artifactory_path(
                path,
                self._username,
                self._apikey,
            )
            if not path.exists():
                utils.raise_file_not_found_error(str(path))
            paths = [str(x) for x in path.glob("**/*") if x.is_file()]

        else:  # find versions of path

            root, _ = self.split(path)
            root = self._expand(root)
            root = audfactory.path(root)
            vs = [os.path.basename(str(f)) for f in root if f.is_dir]

            # filter out other files with same root and version
            paths = [str(self._path(path, v))
                     for v in vs if self._exists(path, v)]

            if not paths:
                utils.raise_file_not_found_error(path)

        # <host>/<repository>/<root>/<name>
        # ->
        # (/<root>/<name>, <version>)

        result = []
        for p in paths:

            p = self._collapse(p)  # remove host and repo
            tokens = p.split('/')

            name = tokens[-1]
            version = tokens[-2]
            path = self.sep.join(tokens[:-2])
            path = self.sep + path
            path = self.join(path, name)

            result.append((path, version))

        return result

    def _path(
            self,
            path: str,
            version: str,
    ) -> artifactory.ArtifactoryPath:
        r"""Convert to backend path.

        <root>/<name>
        ->
        <host>/<repository>/<root>/<version>/<name>

        """
        root, name = self.split(path)
        root = self._expand(root)
        path = f'{root}/{version}/{name}'
        path = _artifactory_path(
            path,
            self._username,
            self._apikey,
        )
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
        audfactory.deploy(src_path, str(dst_path), verbose=verbose)

    def _remove_file(
            self,
            path: str,
            version: str,
    ):
        r"""Remove file from backend."""
        path = self._path(path, version)
        path.unlink()
