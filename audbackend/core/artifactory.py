import os

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
        return audfactory.checksum(path)

    def _collapse(
            self,
            path,
    ):
        r"""Convert to virtual path.

        <host>/<repository>/<path>
        ->
        <path>

        """
        path = path[len(str(self._repo.path)):]
        path = path.replace('/', self.sep)
        return path

    def _create(
            self,
    ):
        r"""Access existing repository."""
        if self._repo is not None:
            utils.raise_file_exists_error(str(self._repo.path))

        self._repo = dohq_artifactory.RepositoryLocal(
            self._artifactory,
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
        audfactory.download(src_path, dst_path, verbose=verbose)

    def _ls(
            self,
            path: str,
    ):
        r"""List all files under (sub-)path."""

        if path.endswith('/'):  # find files under sub-path

            path = self._expand(path)
            path = audfactory.path(path)
            if not path.exists():
                utils.raise_file_not_found_error(str(path))
            paths = [str(x) for x in path.glob("**/*") if x.is_file()]

        else:  # find versions of path

            root, _ = self.split(path)
            root = self._expand(root)
            root = audfactory.path(root)
            vs = [os.path.basename(str(f)) for f in root if f.is_dir]

            # filter out other files with same root and version
            paths = [self._path(path, v) for v in vs if self._exists(path, v)]

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
    ) -> str:
        r"""Convert to backend path.

        <root>/<name>
        ->
        <host>/<repository>/<root>/<version>/<name>

        """
        root, name = self.split(path)
        root = self._expand(root)
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
