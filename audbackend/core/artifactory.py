import os
import typing

import artifactory
import dohq_artifactory

import audeer

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

    Looks for the two environment variables
    ``ARTIFACTORY_USERNAME`` and
    ``ARTIFACTORY_API_KEY``.

    Missing values are extracted them from the
    :file:`~/.artifactory_python.cfg` config file.

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

        config_entry = artifactory.get_global_config_entry(host)

        if config_entry is not None:
            if username is None:
                username = config_entry['username']
            if apikey is None:
                apikey = config_entry['password']

    username = username if username is not None else 'anonymous'
    apikey = apikey if apikey is not None else ''

    return username, apikey


def _deploy(
        src_path: str,
        dst_path: artifactory.ArtifactoryPath,
        *,
        verbose: bool = False,
):
    r"""Deploy local file as an artifact.

    Args:
        src_path: local file path
        dst_path: path on Artifactory
        verbose: show information on the upload process

    """
    if verbose:  # pragma: no cover
        desc = audeer.format_display_message(
            f'Deploy {src_path}',
            pbar=False,
        )
        print(desc, end='\r')

    if not dst_path.parent.exists():
        dst_path.parent.mkdir()

    md5 = utils.md5(src_path)
    with open(src_path, 'rb') as fd:
        dst_path.deploy(fd, md5=md5)

    if verbose:  # pragma: no cover
        # Clear progress line
        print(audeer.format_display_message(' ', pbar=False), end='\r')


def _download(
        src_path: artifactory.ArtifactoryPath,
        dst_path: str,
        *,
        chunk: int = 4 * 1024,
        verbose=False,
):
    r"""Download an artifact.

    Args:
        src_path: local file path
        dst_path: path on Artifactory
        chunk: amount of data read at once during the download
        verbose: show information on the download process

    """
    src_size = artifactory.ArtifactoryPath.stat(src_path).size

    with audeer.progress_bar(total=src_size, disable=not verbose) as pbar:

        desc = audeer.format_display_message(
            'Download {}'.format(os.path.basename(str(src_path))),
            pbar=True,
        )
        pbar.set_description_str(desc)
        pbar.refresh()

        dst_size = 0
        with src_path.open() as src_fp:
            with open(dst_path, 'wb') as dst_fp:
                while src_size > dst_size:
                    data = src_fp.read(chunk)
                    n_data = len(data)
                    if n_data > 0:
                        dst_fp.write(data)
                        dst_size += n_data
                        pbar.update(n_data)


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
        checksum = artifactory.ArtifactoryPath.stat(path).md5
        return checksum

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
        _download(src_path, dst_path, verbose=verbose)

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
            root = _artifactory_path(
                root,
                self._username,
                self._apikey,
            )
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
        _deploy(src_path, dst_path, verbose=verbose)

    def _remove_file(
            self,
            path: str,
            version: str,
    ):
        r"""Remove file from backend."""
        path = self._path(path, version)
        path.unlink()
