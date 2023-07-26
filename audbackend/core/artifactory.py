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
    """Look for username and API key."""
    username = os.getenv('ARTIFACTORY_USERNAME', None)
    api_key = os.getenv('ARTIFACTORY_API_KEY', None)
    config_file = os.getenv(
        'ARTIFACTORY_CONFIG_FILE',
        artifactory.default_config_path,
    )
    config_file = audeer.path(config_file)

    if (
            os.path.exists(config_file) and
            (api_key is None or username is None)
    ):
        config = artifactory.read_config(config_file)
        config_entry = artifactory.get_config_entry(config, host)

        if config_entry is not None:
            if username is None:
                username = config_entry.get('username', None)
            if api_key is None:
                api_key = config_entry.get('password', None)

    if username is None:
        username = 'anonymous'
    if api_key is None:
        api_key = ''

    return username, api_key


def _deploy(
        src_path: str,
        dst_path: artifactory.ArtifactoryPath,
        checksum: str,
        *,
        verbose: bool = False,
):
    r"""Deploy local file as an artifact."""
    if verbose:  # pragma: no cover
        desc = audeer.format_display_message(
            f'Deploy {src_path}',
            pbar=False,
        )
        print(desc, end='\r')

    if not dst_path.parent.exists():
        dst_path.parent.mkdir()

    with open(src_path, 'rb') as fd:
        dst_path.deploy(fd, md5=checksum)

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
    r"""Download an artifact."""
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

    Looks for the two environment variables
    ``ARTIFACTORY_USERNAME`` and
    ``ARTIFACTORY_API_KEY``.
    Otherwise,
    tries to extract missing values
    from a global `config file`_.
    The default path of the config file
    (:file:`~/.artifactory_python.cfg`)
    can be overwritten with the environment variable
    ``ARTIFACTORY_CONFIG_FILE``.
    If no config file exists
    or if it does not contain an
    entry for the ``host``,
    the username is set to ``'anonymous'``
    and the API key to an empty string.
    In that case the ``host``
    should support anonymous access.

    Args:
        host: host address
        repository: repository name

    .. _`config file`: https://devopshq.github.io/artifactory/#global-configuration-file

    """  # noqa: E501
    def __init__(
            self,
            host,
            repository,
    ):
        super().__init__(host, repository)

        self._username, self._api_key = _authentication(host)
        path = _artifactory_path(
            self.host,
            self._username,
            self._api_key,
        )
        self._repo = path.find_repository_local(self.repository)

        # to support legacy file structure
        # see _use_legacy_file_structure()
        self._legacy_extensions = []
        self._legacy_file_structure = False

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
            self._api_key,
        )
        self._repo = dohq_artifactory.RepositoryLocal(
            path,
            self.repository,
            package_type=dohq_artifactory.RepositoryLocal.GENERIC,
        )
        self._repo.create()

    def _date(
            self,
            path: str,
            version: str,
    ) -> str:
        r"""Get last modification date of file on backend."""
        path = self._path(path, version)
        date = path.stat().mtime
        date = utils.date_format(date)
        return date

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

    def _legacy_split_ext(
            self,
            name: str,
    ) -> typing.Tuple[str, str]:
        r"""Split name into basename and extension."""
        ext = None
        for custom_ext in self._legacy_extensions:
            # check for custom extension
            # ensure basename is not empty
            if name[1:].endswith(f'.{custom_ext}'):
                ext = custom_ext
        if ext is None:
            # if no custom extension is found
            # use last string after dot
            ext = audeer.file_extension(name)

        base = audeer.replace_file_extension(name, '', ext=ext)

        if ext:
            ext = f'.{ext}'

        return base, ext

    def _ls(
            self,
            path: str,
    ) -> typing.List[typing.Tuple[str, str]]:
        r"""List all files under (sub-)path."""
        if path.endswith('/'):  # find files under sub-path

            path = self._expand(path)
            path = _artifactory_path(
                path,
                self._username,
                self._api_key,
            )
            if not path.exists():
                utils.raise_file_not_found_error(str(path))

            paths = [str(x) for x in path.glob("**/*") if x.is_file()]

        else:  # find versions of path

            root, name = self.split(path)

            if self._legacy_file_structure:
                base, _ = self._legacy_split_ext(name)
                root = f'{self._expand(root)}{base}'
            else:
                root = self._expand(root)

            root = _artifactory_path(
                root,
                self._username,
                self._api_key,
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
        #
        # or legacy:
        #
        # <host>/<repository>/<root>/<base>/<version>/<base>-<version>.<ext>
        # ->
        # (/<root>/<base>.<ext>, <version>)

        result = []
        for p in paths:

            p = self._collapse(p)  # remove host and repo
            tokens = p.split('/')

            name = tokens[-1]
            version = tokens[-2]

            if self._legacy_file_structure:
                base = tokens[-3]
                ext = name[len(base) + len(version) + 1:]
                name = f'{base}{ext}'
                path = self.sep.join(tokens[:-3])
            else:
                path = self.sep.join(tokens[:-2])

            path = self.sep + path
            path = self.join(path, name)

            result.append((path, version))

        return result

    def _owner(
            self,
            path: str,
            version: str,
    ) -> str:
        r"""Get owner of file on backend."""
        path = self._path(path, version)
        owner = path.stat().modified_by
        return owner

    def _path(
            self,
            path: str,
            version: str,
    ) -> artifactory.ArtifactoryPath:
        r"""Convert to backend path.

        <root>/<name>
        ->
        <host>/<repository>/<root>/<version>/<name>

        or legacy:

        <root>/<base>.<ext>
        ->
        <host>/<repository>/<root>/<base>/<version>/<name>-<version>.<ext>

        """
        root, name = self.split(path)
        root = self._expand(root)

        if self._legacy_file_structure:
            base, ext = self._legacy_split_ext(name)
            path = f'{root}{base}/{version}/{base}-{version}{ext}'
        else:
            path = f'{root}{version}/{name}'

        path = _artifactory_path(
            path,
            self._username,
            self._api_key,
        )
        return path

    def _put_file(
            self,
            src_path: str,
            dst_path: str,
            version: str,
            checksum: str,
            verbose: bool,
    ):
        r"""Put file to backend."""
        dst_path = self._path(dst_path, version)
        _deploy(src_path, dst_path, checksum, verbose=verbose)

    def _remove_file(
            self,
            path: str,
            version: str,
    ):
        r"""Remove file from backend."""
        path = self._path(path, version)
        path.unlink()

    def _use_legacy_file_structure(
            self,
            *,
            extensions: typing.List[str] = None,
    ):
        r"""Use legacy file structure.

        Stores files under
        ``'.../<name-wo-ext>/<version>/<name-wo-ext>-<version>.<ext>'``
        instead of
        ``'.../<version>/<name>'``.
        By default,
        the extension
        ``<ext>``
        is set to the string after the last dot.
        I.e.,
        the backend path
        ``'.../file.tar.gz'``
        will translate into
        ``'.../file.tar/1.0.0/file.tar-1.0.0.gz'``.
        However,
        by passing a list with custom extensions
        it is possible to overwrite
        the default behavior
        for certain extensions.
        E.g.,
        with
        ``backend._use_legacy_file_structure(extensions=['tar.gz'])``
        it is ensured that
        ``'tar.gz'``
        will be recognized as an extension
        and the backend path
        ``'.../file.tar.gz'``
        will then translate into
        ``'.../file/1.0.0/file-1.0.0.tar.gz'``.

        """
        self._legacy_file_structure = True
        self._legacy_extensions = extensions or []
