import typing

import audfactory
from audb2.core.backend import Backend


class Artifactory(Backend):
    r"""Artifactory backend.

    Stores files and archives on Artifactory.

    Args:
        host: host address

    """

    def __init__(
            self,
            host,
    ):
        super().__init__(host)

    def _checksum(
            self,
            path: str,
    ) -> str:
        r"""MD5 checksum of file on backend."""
        return audfactory.checksum(path)

    def _path(
            self,
            repository: str,
            folder: str,
            name: str,
            ext: str,
            version: str,
    ) -> str:
        r"""File path on backend."""
        server_url = audfactory.server_url(
            group_id=audfactory.path_to_group_id(folder),
            name=name,
            repository=repository,
            version=version,
        )
        return f'{server_url}/{name}-{version}{ext}'

    def _exists(
            self,
            path: str,
    ) -> bool:
        r"""Check if file exists on backend."""
        return audfactory.artifactory_path(path).exists()

    def _get_file(
            self,
            src_path: str,
            dst_path: str,
    ):
        r"""Get file from backend."""
        audfactory.download_artifact(src_path, dst_path, verbose=False)

    def _glob(
            self,
            pattern: str,
            repository: str,
    ) -> typing.List[str]:
        r"""Return matching files names."""
        url = audfactory.server_url(
            '',
            repository=repository,
        )
        path = audfactory.artifactory_path(url)
        try:
            result = [str(x) for x in path.glob(pattern)]
        except RuntimeError:  # pragma: no cover
            result = []
        return result

    def _put_file(
            self,
            src_path: str,
            dst_path: str,
    ):
        r"""Put file to backend."""
        audfactory.deploy_artifact(src_path, dst_path)

    def _remove_file(
            self,
            path: str,
    ):
        r"""Remove file from backend."""
        audfactory.artifactory_path(path).unlink()

    def _versions(
            self,
            repository: str,
            folder: str,
            name: str,
    ) -> typing.List[str]:
        r"""Versions of a file."""
        group_id = audfactory.path_to_group_id(folder)
        return audfactory.versions(group_id, name, repository=repository)
