import requests
import typing

import audfactory

from audbackend.core.backend import Backend


class Artifactory(Backend):
    r"""Artifactory backend.

    Stores files and archives on Artifactory.

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
    ) -> str:
        r"""MD5 checksum of file on backend."""
        return audfactory.checksum(path)

    def _path(
            self,
            folder: str,
            name: str,
            ext: str,
            version: str,
    ) -> str:
        r"""File path on backend."""
        server_url = audfactory.url(
            self.host,
            repository=self.repository,
            group_id=audfactory.path_to_group_id(folder),
            name=name,
            version=version,
        )
        return f'{server_url}/{name}-{version}{ext}'

    def _exists(
            self,
            path: str,
    ) -> bool:
        r"""Check if file exists on backend."""
        try:
            # Can lead to
            # RuntimeError: 404 page not found
            # or
            # requests.exceptions.HTTPError: 403 Client Error
            return audfactory.path(path).exists()
        except self._non_existing_path_error:  # pragma: nocover
            return False

    def _get_file(
            self,
            src_path: str,
            dst_path: str,
            verbose: bool,
    ):
        r"""Get file from backend."""
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
        except self._non_existing_path_error:  # pragma: nocover
            result = []
        return result

    def _ls(
            self,
            path: str,
    ):
        r"""List content of path."""
        path = audfactory.url(
            self.host,
            repository=self.repository,
            group_id=audfactory.path_to_group_id(path),
        )
        return [p.name for p in audfactory.path(path)]

    def _put_file(
            self,
            src_path: str,
            dst_path: str,
            verbose: bool,
    ):
        r"""Put file to backend."""
        audfactory.deploy(src_path, dst_path, verbose=verbose)

    def _remove_file(
            self,
            path: str,
    ):
        r"""Remove file from backend."""
        audfactory.path(path).unlink()

    def _versions(
            self,
            folder: str,
            name: str,
    ) -> typing.List[str]:
        r"""Versions of a file."""
        group_id = audfactory.path_to_group_id(folder)
        return audfactory.versions(self.host, self.repository, group_id, name)

    _non_existing_path_error = (RuntimeError, requests.exceptions.HTTPError)
    r"""Error expected for non-existing paths.

    If a user has no permission to a given path
    or the path does not exists :func:`audfactory.path`
    might return a
    ``RuntimeError: 404 page not found``
    or
    ``requests.exceptions.HTTPError: 403 Client Error``
    error,
    which might depend on the instaleld ``dohq-artifactory``
    version. So we better catch both of them.

    """
