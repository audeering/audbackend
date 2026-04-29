from collections.abc import Iterator
import configparser
import os

import requests

import audeer

from audbackend.core import utils
from audbackend.core.backend._artifactory_rest import DEFAULT_TIMEOUT
from audbackend.core.backend._artifactory_rest import ArtifactoryRestClient
from audbackend.core.backend.base import Base


DEFAULT_CONFIG_PATH = "~/.artifactory_python.cfg"

# Sentinel for "use the default / environment variable"
# so a caller can still pass ``timeout=None`` to disable timeouts.
_TIMEOUT_UNSET = object()


def _download_with_progress(
    client: ArtifactoryRestClient,
    src_path: str,
    dst_path: str,
    *,
    verbose: bool = False,
):
    r"""Download an artifact via the REST client with an optional progress bar."""
    src_size = client.stat(src_path)["size"]

    with audeer.progress_bar(total=src_size, disable=not verbose) as pbar:
        desc = audeer.format_display_message(
            f"Download {os.path.basename(src_path)}",
            pbar=True,
        )
        pbar.set_description_str(desc)
        pbar.refresh()

        client.download(src_path, dst_path, on_chunk=pbar.update)


def _find_config_entry(
    config: configparser.ConfigParser,
    host: str,
) -> dict | None:
    r"""Look up a host entry in an Artifactory Python config file.

    Tries the host as-is, with the scheme stripped,
    and each of those with any trailing slash removed.
    """
    candidates = [host, host.rstrip("/")]
    for scheme in ("https://", "http://"):
        if host.startswith(scheme):
            without_scheme = host[len(scheme) :]
            candidates.append(without_scheme)
            candidates.append(without_scheme.rstrip("/"))
            break

    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if config.has_section(candidate):
            return dict(config.items(candidate))
    return None


class Artifactory(Base):
    r"""Backend for Artifactory.

    HTTP requests use a default timeout of 60 seconds to avoid hanging
    on a stalled server or connection. The default can be overridden
    by passing ``timeout`` to the constructor or by setting the
    ``ARTIFACTORY_TIMEOUT`` environment variable. The value is forwarded
    to :mod:`requests` and accepts a float (combined connect/read
    timeout), a ``(connect, read)`` tuple, or ``None`` (wait
    indefinitely).

    Args:
        host: host address
        repository: repository name
        authentication: username, password / API key / access token tuple.
            If ``None``,
            it requests it by calling :meth:`get_authentication`
        timeout: HTTP timeout in seconds applied to every request.
            Pass ``None`` to disable the timeout entirely.
            If the argument is omitted,
            the value is read from the ``ARTIFACTORY_TIMEOUT``
            environment variable
            (use ``"none"`` to disable),
            falling back to ``60.0`` if the variable is unset.

    """  # noqa: E501

    def __init__(
        self,
        host: str,
        repository: str,
        *,
        authentication: tuple[str, str] = None,
        timeout: float | tuple[float, float] | None = _TIMEOUT_UNSET,
    ):
        super().__init__(host, repository, authentication=authentication)

        if authentication is None:
            self.authentication = self.get_authentication(host)

        if timeout is _TIMEOUT_UNSET:
            timeout = self._timeout_from_env()
        self.timeout = timeout

        # REST client bound to the repository; populated in _open().
        self._client = None

        # Session used by the client; owned here so _close can release it.
        self._session = None

    @staticmethod
    def _timeout_from_env() -> float | None:
        r"""Read ``ARTIFACTORY_TIMEOUT`` from the environment.

        Returns the default timeout if the variable is unset
        or cannot be parsed as a float.
        ``"none"`` (case-insensitive) disables the timeout.
        """
        raw = os.getenv("ARTIFACTORY_TIMEOUT")
        if raw is None:
            return DEFAULT_TIMEOUT
        if raw.strip().lower() == "none":
            return None
        try:
            return float(raw)
        except ValueError:
            return DEFAULT_TIMEOUT

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
            os.path.expanduser(DEFAULT_CONFIG_PATH),
        )
        config_file = audeer.path(config_file)

        if os.path.exists(config_file) and (api_key is None or username is None):
            config = configparser.ConfigParser()
            config.read(config_file)
            entry = _find_config_entry(config, host)

            if entry is not None:
                if username is None:
                    username = entry.get("username", None)
                if api_key is None:
                    api_key = entry.get("password", None)

        if username is None:
            username = "anonymous"
        if api_key is None:
            api_key = ""

        return username, api_key

    def _checksum(self, path: str) -> str:
        r"""MD5 checksum of file on backend."""
        return self._client.stat(path)["md5"]

    def _close(self):
        r"""Close connection to repository."""
        if self._session is not None:
            self._session.close()
        self._session = None
        self._client = None

    def _copy_file(
        self,
        src_path: str,
        dst_path: str,
        num_workers: int,
        verbose: bool,
    ):
        r"""Copy file on backend."""
        self._client.copy(src_path, dst_path)

    def _create(self):
        r"""Create repository."""
        with requests.Session() as session:
            session.auth = self.authentication
            client = ArtifactoryRestClient(
                self.host,
                self.repository,
                session,
                timeout=self.timeout,
            )
            if client.repository_exists():
                utils.raise_file_exists_error(self.repository)
            client.create_repository()

    def _date(self, path: str) -> str:
        r"""Get last modification date of file on backend."""
        return utils.date_format(self._client.stat(path)["mtime"])

    def _delete(self):
        r"""Delete repository and all its content."""
        with requests.Session() as session:
            session.auth = self.authentication
            client = ArtifactoryRestClient(
                self.host,
                self.repository,
                session,
                timeout=self.timeout,
            )
            client.delete_repository()

    def _exists(self, path: str) -> bool:
        r"""Check if file exists on backend."""
        return self._client.exists(path)

    def _get_file(
        self,
        src_path: str,
        dst_path: str,
        num_workers: int,
        verbose: bool,
    ):
        r"""Get file from backend."""
        _download_with_progress(self._client, src_path, dst_path, verbose=verbose)

    def _get_file_stream(self, src_path: str) -> Iterator[bytes]:
        r"""Get file from backend as byte stream."""
        from audbackend.core.backend.base import STREAM_CHUNK_SIZE

        yield from self._client.stream(src_path, chunk_size=STREAM_CHUNK_SIZE)

    def _ls(self, path: str) -> list[str]:
        r"""List all files under sub-path."""
        return self._client.list_files(path)

    def _move_file(
        self,
        src_path: str,
        dst_path: str,
        num_workers: int,
        verbose: bool,
    ):
        r"""Move file on backend."""
        self._client.move(src_path, dst_path)

    def _open(self):
        r"""Open connection to backend."""
        self._session = requests.Session()
        self._session.auth = self.authentication
        self._client = ArtifactoryRestClient(
            self.host,
            self.repository,
            self._session,
            timeout=self.timeout,
        )
        if not self._client.repository_exists():
            utils.raise_file_not_found_error(self.repository)

    def _owner(self, path: str) -> str:
        r"""Get owner of file on backend."""
        return self._client.stat(path)["modified_by"]

    def path(self, path: str) -> str:
        r"""Convert to backend path.

        Extends the relative ``path`` on the backend
        by :attr:`host` and :attr:`repository`
        and returns a full URL as a string.

        Args:
            path: path on backend

        Returns:
            full URL to the artifact on the backend

        """
        path = path.replace(self.sep, "/").removeprefix("/")
        return f"{self.host.rstrip('/')}/{self.repository}/{path}"

    def _put_file(
        self,
        src_path: str,
        dst_path: str,
        checksum: str,
        verbose: bool,
    ):
        r"""Put file to backend."""
        if verbose:  # pragma: no cover
            desc = audeer.format_display_message(
                f"Deploy {src_path}",
                pbar=False,
            )
            print(desc, end="\r")

        self._client.upload(src_path, dst_path, md5=checksum)

        if verbose:  # pragma: no cover
            print(audeer.format_display_message(" ", pbar=False), end="\r")

    def _remove_file(self, path: str):
        r"""Remove file from backend."""
        self._client.delete(path)

    def _size(self, path: str) -> int:
        r"""Get size of file on backend."""
        return self._client.stat(path)["size"]
