import asyncio
from collections.abc import Iterator
from collections.abc import Sequence
import configparser
import os
from typing import Callable
import warnings

import artifactory
import dohq_artifactory
import requests
from requests.adapters import HTTPAdapter

import audeer

from audbackend.core import utils
from audbackend.core.backend.base import Base
from audbackend.core.errors import BackendError


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

    Connection pool settings can be configured
    via the config file (see :meth:`get_config`):

    * ``pool_connections``: number of connection pools to cache (default: 10)
    * ``pool_maxsize``: max connections per pool (default: 10)
    * ``max_retries``: max retries per connection (default: 0)

    For bulk operations downloading many files in parallel,
    increase ``pool_maxsize`` to match the number of workers.

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

    @classmethod
    def get_config(cls, host: str) -> dict:
        """Configuration of Artifactory server.

        The default path of the config file is
        :file:`~/.config/audbackend/artifactory.cfg`.
        It can be overwritten with the environment variable
        ``ARTIFACTORY_POOL_CONFIG_FILE``.

        If no config file can be found,
        or no entry for the requested host,
        an empty dictionary is returned.

        The config file
        expects one section per host,
        e.g.

        .. code-block:: ini

            [artifactory.example.com/artifactory]
            pool_connections = 10
            pool_maxsize = 100
            max_retries = 3

        Connection pool settings (for bulk operations with many files):

        * ``pool_connections``: number of connection pools to cache (default: 10)
        * ``pool_maxsize``: maximum number of connections per pool.
          Increase this for parallel downloads of many files (default: 10)
        * ``max_retries``: maximum number of retries per connection (default: 0)

        Args:
            host: hostname

        Returns:
            config entries as dictionary

        """
        config_file = os.getenv(
            "ARTIFACTORY_POOL_CONFIG_FILE",
            "~/.config/audbackend/artifactory.cfg",
        )
        config_file = audeer.path(config_file)

        if os.path.exists(config_file):
            config = configparser.ConfigParser(allow_no_value=True)
            config.read(config_file)
            try:
                config = dict(config.items(host))
            except configparser.NoSectionError:
                config = {}
        else:
            config = {}

        return config

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
        num_workers: int,
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
        num_workers: int,
        verbose: bool,
    ):
        r"""Get file from backend."""
        src_path = self.path(src_path)
        _download(src_path, dst_path, verbose=verbose)

    def _get_file_stream(
        self,
        src_path: str,
    ) -> Iterator[bytes]:
        r"""Get file from backend as byte stream."""
        from audbackend.core.backend.base import STREAM_CHUNK_SIZE

        src_path = self.path(src_path)

        with src_path.open("r") as fp:
            while data := fp.read(STREAM_CHUNK_SIZE):
                yield data

    def _size(
        self,
        path: str,
    ) -> int:
        r"""Get size of file on backend."""
        path = self.path(path)
        return artifactory.ArtifactoryPath.stat(path).size

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
        num_workers: int,
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

        # Configure connection pooling for better performance
        # with parallel downloads of many files.
        # Settings can be tuned via backend config:
        #   - "pool_connections": number of pools to cache (default: 10)
        #   - "pool_maxsize": max connections per pool (default: 10)
        #   - "max_retries": max retries per connection (default: 0)
        config = self.get_config(self.host)
        pool_connections = _parse_int(
            config.get("pool_connections", 10),
            name="pool_connections",
            default=10,
        )
        pool_maxsize = _parse_int(
            config.get("pool_maxsize", 10),
            name="pool_maxsize",
            default=10,
        )
        max_retries = _parse_int(
            config.get("max_retries", 0),
            name="max_retries",
            default=0,
        )
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=max_retries,
        )
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

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

    def get_files_async(
        self,
        files: Sequence[tuple[str, str]],
        *,
        max_concurrent: int = 50,
        progress_callback: Callable[[str, str], None] | None = None,
        verbose: bool = False,
    ) -> list[str]:
        r"""Download multiple files concurrently using asyncio.

        This method provides efficient concurrent downloads for bulk operations
        with many files. It uses asyncio to manage concurrent downloads,
        reducing thread overhead compared to thread-based parallelism.

        Args:
            files: sequence of (src_path, dst_path) tuples where
                src_path is the path on the backend (must start with /)
                and dst_path is the local destination path
            max_concurrent: maximum number of concurrent downloads (default: 50).
                Higher values increase throughput but also memory usage
            progress_callback: optional callback called with (src_path, dst_path)
                after each successful download
            verbose: if ``True``, show progress bar

        Returns:
            list of successfully downloaded local file paths

        Raises:
            BackendError: if backend is not opened

        Example:
            >>> files = [
            ...     ("/data/file1.txt", "/local/file1.txt"),
            ...     ("/data/file2.txt", "/local/file2.txt"),
            ... ]
            >>> with backend:
            ...     downloaded = backend.get_files_async(files, max_concurrent=100)

        """
        if not self.opened:
            raise BackendError(RuntimeError("Backend not opened"))

        return asyncio.run(
            self._get_files_async(
                files,
                max_concurrent=max_concurrent,
                progress_callback=progress_callback,
                verbose=verbose,
            )
        )

    async def _get_files_async(
        self,
        files: Sequence[tuple[str, str]],
        *,
        max_concurrent: int = 50,
        progress_callback: Callable[[str, str], None] | None = None,
        verbose: bool = False,
    ) -> list[str]:
        r"""Internal async implementation for concurrent file downloads."""
        semaphore = asyncio.Semaphore(max_concurrent)
        downloaded = []
        errors = []

        # Setup progress bar
        pbar = audeer.progress_bar(
            total=len(files),
            desc="Download files (async)",
            disable=not verbose,
        )

        async def download_one(src_path: str, dst_path: str) -> str | None:
            """Download a single file with semaphore limiting."""
            async with semaphore:
                try:
                    # Run the sync download in a thread pool
                    await asyncio.to_thread(
                        self._download_single_file,
                        src_path,
                        dst_path,
                    )
                    if progress_callback:
                        progress_callback(src_path, dst_path)
                    pbar.update(1)
                    return dst_path
                except Exception as e:
                    errors.append((src_path, str(e)))
                    pbar.update(1)
                    return None

        with pbar:
            # Create all download tasks
            tasks = [download_one(src, dst) for src, dst in files]
            # Run all tasks concurrently
            results = await asyncio.gather(*tasks)

        # Collect successful downloads
        downloaded = [r for r in results if r is not None]

        if errors and verbose:
            print(f"Warning: {len(errors)} files failed to download")

        return downloaded

    def _download_single_file(
        self,
        src_path: str,
        dst_path: str,
    ) -> None:
        r"""Download a single file without progress bar.

        This is a simplified version of _get_file for use in async contexts.

        """
        src_path = self.path(src_path)

        # Ensure destination directory exists
        dst_dir = os.path.dirname(dst_path)
        if dst_dir:
            os.makedirs(dst_dir, exist_ok=True)

        # Download file using Artifactory API
        src_size = artifactory.ArtifactoryPath.stat(src_path).size
        dst_size = 0
        chunk_size = 4 * 1024

        with src_path.open() as src_fp:
            with open(dst_path, "wb") as dst_fp:
                while src_size > dst_size:
                    data = src_fp.read(chunk_size)
                    n_data = len(data)
                    if n_data > 0:
                        dst_fp.write(data)
                        dst_size += n_data


def _parse_int(
    value: str | int,
    *,
    name: str,
    default: int,
) -> int:
    """Parse an integer value from config.

    Converts string values to int.
    If parsing fails, logs a warning and returns the default value.

    Args:
        value: integer value (string from config or int)
        name: name of the setting (for warning messages)
        default: default value to use if parsing fails

    Returns:
        parsed integer value or default

    """
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (ValueError, TypeError):
        warnings.warn(
            f"Invalid {name} value '{value}' in config, using default: {default}",
            UserWarning,
            stacklevel=4,
        )
        return default
