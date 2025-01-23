import os

import artifactory
import dohq_artifactory
import requests

import audeer

from audbackend.core import utils
from audbackend.core.backend.base import Base


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
            f"Deploy {src_path}",
            pbar=False,
        )
        print(desc, end="\r")

    if not dst_path.parent.exists():
        dst_path.parent.mkdir()

    with open(src_path, "rb") as fd:
        dst_path.deploy(fd, md5=checksum, quote_parameters=True)

    if verbose:  # pragma: no cover
        # Clear progress line
        print(audeer.format_display_message(" ", pbar=False), end="\r")


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
            f"Download {os.path.basename(str(src_path))}",
            pbar=True,
        )
        pbar.set_description_str(desc)
        pbar.refresh()

        dst_size = 0
        with src_path.open() as src_fp:
            with open(dst_path, "wb") as dst_fp:
                while src_size > dst_size:
                    data = src_fp.read(chunk)
                    n_data = len(data)
                    if n_data > 0:
                        dst_fp.write(data)
                        dst_size += n_data
                        pbar.update(n_data)


class Artifactory(Base):
    r"""Backend for Artifactory.

    Args:
        host: host address
        repository: repository name
        authentication: username, password / API key / access token tuple.
            If ``None``,
            it requests it by calling :meth:`get_authentication`

    """  # noqa: E501

    def __init__(
        self,
        host: str,
        repository: str,
        *,
        authentication: tuple[str, str] = None,
    ):
        super().__init__(host, repository, authentication=authentication)

        if authentication is None:
            self.authentication = self.get_authentication(host)

        # Store ArtifactoryPath object to the repository,
        # when opening the backend.
        self._repo = None

        # Store request.Session as handed to ArtifactoryPath
        self._session = None

    @classmethod
    def get_authentication(cls, host: str) -> tuple[str, str]:
        """Username and password/access token for given host.

        Returns a username
        and password / API key / access token,
        which can be used to authenticate
        with an Artifactory server.

        Note, API keys are deprecated
        and will no longer work
        with newer versions of Artifactory.

        To get the username,
        password/access token combination,
        the function looks first
        for the two environment variables
        ``ARTIFACTORY_USERNAME`` and
        ``ARTIFACTORY_API_KEY``.
        Otherwise,
        it tries to extract missing values
        from a global `config file`_.
        The default path of the config file
        (:file:`~/.artifactory_python.cfg`)
        can be overwritten with the environment variable
        ``ARTIFACTORY_CONFIG_FILE``.
        If no config file exists
        or if it does not contain an
        entry for the ``host``,
        the username is set to ``'anonymous'``
        and the password/key to an empty string.
        In that case the ``host``
        has to support anonymous access,
        when trying to authenticate.

        .. _`config file`: https://devopshq.github.io/artifactory/#global-configuration-file

        Args:
            host: hostname of Artifactory backend

        Returns:
            username, password / API key / access token tuple

        """
        username = os.getenv("ARTIFACTORY_USERNAME", None)
        api_key = os.getenv("ARTIFACTORY_API_KEY", None)
        config_file = os.getenv(
            "ARTIFACTORY_CONFIG_FILE",
            artifactory.default_config_path,
        )
        config_file = audeer.path(config_file)

        if os.path.exists(config_file) and (api_key is None or username is None):
            config = artifactory.read_config(config_file)
            config_entry = artifactory.get_config_entry(config, host)

            if config_entry is not None:
                if username is None:
                    username = config_entry.get("username", None)
                if api_key is None:
                    api_key = config_entry.get("password", None)

        if username is None:
            username = "anonymous"
        if api_key is None:
            api_key = ""

        return username, api_key

    def _checksum(
        self,
        path: str,
    ) -> str:
        r"""MD5 checksum of file on backend."""
        path = self.path(path)
        checksum = artifactory.ArtifactoryPath.stat(path).md5
        return checksum

    def _close(
        self,
    ):
        r"""Close connection to repository.

        An error should be raised,
        if the connection to the backend
        cannot be closed.

        """
        if self._session is not None:
            self._session.close()

    def _collapse(
        self,
        path,
    ):
        r"""Convert to virtual path.

        <host>/<repository>/<path>
        ->
        /<path>

        """
        # Requires dohq-artifactory>=1.0.0,
        # before length was one longer
        path = path[len(str(self.path("/"))) :]
        path = path.replace("/", self.sep)
        return path

    def _copy_file(
        self,
        src_path: str,
        dst_path: str,
        verbose: bool,
    ):
        r"""Copy file on backend."""
        src_path = self.path(src_path)
        dst_path = self.path(dst_path)
        if not dst_path.parent.exists():
            dst_path.parent.mkdir()
        src_path.copy(dst_path)

    def _create(
        self,
    ):
        r"""Create repository."""
        with requests.Session() as session:
            session.auth = self.authentication
            path = artifactory.ArtifactoryPath(self.host, session=session)
            repo = dohq_artifactory.RepositoryLocal(
                path,
                self.repository,
                package_type=dohq_artifactory.RepositoryLocal.GENERIC,
            )
            if repo.path.exists():
                utils.raise_file_exists_error(str(repo.path))
            repo.create()

    def _date(
        self,
        path: str,
    ) -> str:
        r"""Get last modification date of file on backend."""
        path = self.path(path)
        date = path.stat().mtime
        date = utils.date_format(date)
        return date

    def _delete(
        self,
    ):
        r"""Delete repository and all its content."""
        with self:
            self._repo.delete()

    def _exists(
        self,
        path: str,
    ) -> bool:
        r"""Check if file exists on backend."""
        path = self.path(path)
        return path.exists()

    def _get_file(
        self,
        src_path: str,
        dst_path: str,
        verbose: bool,
    ):
        r"""Get file from backend."""
        src_path = self.path(src_path)
        _download(src_path, dst_path, verbose=verbose)

    def _ls(
        self,
        path: str,
    ) -> list[str]:
        r"""List all files under sub-path."""
        path = self.path(path)
        if not path.exists():
            return []

        paths = [str(x) for x in path.glob("**/*") if x.is_file()]
        paths = [self._collapse(path) for path in paths]

        return paths

    def _move_file(
        self,
        src_path: str,
        dst_path: str,
        verbose: bool,
    ):
        r"""Move file on backend."""
        src_path = self.path(src_path)
        dst_path = self.path(dst_path)
        if not dst_path.parent.exists():
            dst_path.parent.mkdir()
        src_path.move(dst_path)

    def _open(
        self,
    ):
        r"""Open connection to backend."""
        self._session = requests.Session()
        self._session.auth = self.authentication
        path = artifactory.ArtifactoryPath(self.host, session=self._session)
        self._repo = path.find_repository(self.repository)
        if self._repo is None:
            utils.raise_file_not_found_error(self.repository)

    def _owner(
        self,
        path: str,
    ) -> str:
        r"""Get owner of file on backend."""
        path = self.path(path)
        owner = path.stat().modified_by
        return owner

    def path(
        self,
        path: str,
    ) -> artifactory.ArtifactoryPath:
        r"""Convert to backend path.

        This extends the relative ``path`` on the backend
        by :attr:`host` and :attr:`repository`,
        and returns an :class:`artifactory.ArtifactoryPath` object.

        Args:
            path: path on backend

        Returns:
            Artifactory path object

        """
        path = path.replace(self.sep, "/").removeprefix("/")
        # path -> host/repository/path
        return self._repo / path

    def _put_file(
        self,
        src_path: str,
        dst_path: str,
        checksum: str,
        verbose: bool,
    ):
        r"""Put file to backend."""
        dst_path = self.path(dst_path)
        _deploy(src_path, dst_path, checksum, verbose=verbose)

    def _remove_file(
        self,
        path: str,
    ):
        r"""Remove file from backend."""
        path = self.path(path)
        path.unlink()
