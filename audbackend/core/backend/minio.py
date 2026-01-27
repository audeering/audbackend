import configparser
import getpass
import mimetypes
import os
import tempfile
import warnings

import minio
import urllib3

import audeer

from audbackend.core import utils
from audbackend.core.backend.base import Base


class Minio(Base):
    r"""Backend for MinIO.

    HTTP timeouts can be configured via the config file
    (see :meth:`get_config`):

    * ``connect_timeout``: seconds for connection establishment (default: 10.0)
    * ``read_timeout``: seconds for read operations; ``None`` means no timeout
      (default: ``None``)

    Alternatively,
    provide a custom ``http_client`` object as ``kwargs``
    to fully control connection behavior.

    Args:
        host: host address
        repository: repository name
        authentication: username, password / access key, secret key token tuple.
            If ``None``,
            it requests it by calling :meth:`get_authentication`
        secure: if ``None``,
            it looks in the config file for it,
            compare :meth:`get_config`.
            If it cannot find a matching entry,
            it defaults to ``True``.
            Needs to be ``True``
            when using TLS for the connection,
            and ``False`` otherwise,
            e.g. when using a `local MinIO server`_.
        **kwargs: keyword arguments passed on to `minio.Minio`_

    .. _local MinIO server: https://min.io/docs/minio/container/index.html
    .. _minio.Minio: https://min.io/docs/minio/linux/developers/python/API.html

    Examples:
        >>> host = "play.min.io"  # playground provided by https://min.io
        >>> auth = ("Q3AM3UQ867SPQQA43P2F", "zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG")
        >>> repository = "my-data" + audeer.uid()
        >>> Minio.create(host, repository, authentication=auth)
        >>> file = audeer.touch("src.txt")
        >>> backend = Minio(host, repository, authentication=auth)
        >>> try:
        ...     with backend:
        ...         backend.put_file(file, "/sub/file.txt")
        ...         backend.ls()
        ... finally:
        ...     Minio.delete(host, repository, authentication=auth)
        ['/sub/file.txt']

    """  # noqa: E501

    def __init__(
        self,
        host: str,
        repository: str,
        *,
        authentication: tuple[str, str] = None,
        secure: bool = None,
        **kwargs,
    ):
        super().__init__(host, repository, authentication=authentication)

        if authentication is None:
            self.authentication = self.get_authentication(host)

        config = self.get_config(host)
        if secure is None:
            secure = config.get("secure", True)

        # Configure HTTP client with timeouts to prevent hanging connections.
        # Users can override by passing their own http_client in kwargs.
        # Timeouts can be tuned via backend config:
        #   - "connect_timeout": seconds for connection establishment (default: 10.0)
        #   - "read_timeout": seconds for read operations; None means no timeout
        #     (default: None)
        if "http_client" not in kwargs:
            connect_timeout = _parse_timeout(
                config.get("connect_timeout", 10.0),
                name="connect_timeout",
                default=10.0,
            )
            read_timeout = _parse_timeout(
                config.get("read_timeout", None),
                name="read_timeout",
                default=None,
            )
            timeout = urllib3.Timeout(connect=connect_timeout, read=read_timeout)
            kwargs["http_client"] = urllib3.PoolManager(timeout=timeout)

        # Open MinIO client
        self._client = minio.Minio(
            endpoint=host,
            access_key=self.authentication[0],
            secret_key=self.authentication[1],
            secure=secure,
            **kwargs,
        )

    @classmethod
    def get_authentication(cls, host: str) -> tuple[str, str]:
        """Access and secret tokens for given host.

        Returns a authentication for MinIO server
        as tuple.

        To get the authentication tuple,
        the function looks first
        for the two environment variables
        ``MINIO_ACCESS_KEY`` and
        ``MINIO_SECRET_KEY``.
        Otherwise,
        it tries to extract missing values
        from a config file,
        see :meth:`get_config`.
        If no config file exists
        or if it has missing entries,
        ``None`` is returned
        for the missing entries.

        Args:
            host: hostname

        Returns:
            access token tuple

        """
        config = cls.get_config(host)
        access_key = os.getenv("MINIO_ACCESS_KEY", config.get("access_key"))
        secret_key = os.getenv("MINIO_SECRET_KEY", config.get("secret_key"))

        return access_key, secret_key

    @classmethod
    def get_config(cls, host: str) -> dict:
        """Configuration of MinIO server.

        The default path of the config file is
        :file:`~/.config/audbackend/minio.cfg`.
        It can be overwritten with the environment variable
        ``MINIO_CONFIG_FILE``.

        If no config file can be found,
        or no entry for the requested host,
        an empty dictionary is returned.

        The config file
        expects one section per host,
        e.g.

        .. code-block:: ini

            [play.min.io]
            access_key = "Q3AM3UQ867SPQQA43P2F"
            secret_key = "zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG"

        Optional timeout settings can also be configured:

        .. code-block:: ini

            [play.min.io]
            access_key = "Q3AM3UQ867SPQQA43P2F"
            secret_key = "zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG"
            connect_timeout = 10.0
            read_timeout = 60.0

        * ``connect_timeout``: seconds for connection establishment
          (default: 10.0)
        * ``read_timeout``: seconds for read operations;
          use ``None`` for no timeout (default: ``None``)

        Args:
            host: hostname

        Returns:
            config entries as dictionary

        """
        config_file = os.getenv("MINIO_CONFIG_FILE", "~/.config/audbackend/minio.cfg")
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

    def close(
        self,
    ):
        r"""Close connection to backend.

        This will only change the status of
        :attr:`audbackend.backend.Minio.opened`
        as Minio handles closing the session itself.

        """
        if self.opened:
            self.opened = False

    def _checksum(
        self,
        path: str,
    ) -> str:
        r"""MD5 checksum of file on backend."""
        path = self.path(path)
        meta = self._client.stat_object(
            bucket_name=self.repository,
            object_name=path,
        ).metadata
        return meta["x-amz-meta-checksum"] if "x-amz-meta-checksum" in meta else ""

    def _collapse(
        self,
        path,
    ):
        r"""Convert to virtual path.

        <path>
        ->
        /<path>

        """
        path = f"/{path}"
        return path.replace("/", self.sep)

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
        checksum = self._checksum(src_path)
        # `copy_object()` has a maximum size limit of 5GB.
        # We use 4.9GB to have some headroom
        if self._size(src_path) / 1024 / 1024 / 1024 >= 4.9:
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = audeer.path(tmp_dir, os.path.basename(src_path))
                self._get_file(src_path, tmp_path, num_workers, verbose)
                self._put_file(tmp_path, dst_path, checksum, verbose)
        else:
            self._client.copy_object(
                bucket_name=self.repository,
                object_name=dst_path,
                source=minio.commonconfig.CopySource(self.repository, src_path),
                metadata=_metadata(checksum),
            )

    def _create(
        self,
    ):
        r"""Create repository."""
        if self._client.bucket_exists(bucket_name=self.repository):
            utils.raise_file_exists_error(self.repository)
        self._client.make_bucket(bucket_name=self.repository)

    def _date(
        self,
        path: str,
    ) -> str:
        r"""Get last modification date of file on backend."""
        path = self.path(path)
        date = self._client.stat_object(
            bucket_name=self.repository,
            object_name=path,
        ).last_modified
        date = utils.date_format(date)
        return date

    def _delete(
        self,
    ):
        r"""Delete repository and all its content."""
        # Delete all objects in bucket
        objects = self._client.list_objects(bucket_name=self.repository, recursive=True)
        for obj in objects:
            self._client.remove_object(
                bucket_name=self.repository,
                object_name=obj.object_name,
            )
        # Delete bucket
        self._client.remove_bucket(bucket_name=self.repository)

    def _exists(
        self,
        path: str,
    ) -> bool:
        r"""Check if file exists on backend."""
        path = self.path(path)
        try:
            self._client.stat_object(
                bucket_name=self.repository,
                object_name=path,
            )
        except minio.error.S3Error:
            return False
        return True

    def _get_file(
        self,
        src_path: str,
        dst_path: str,
        num_workers: int,
        verbose: bool,
    ):
        r"""Get file from backend."""
        src_path = self.path(src_path)
        src_size = self._client.stat_object(
            bucket_name=self.repository,
            object_name=src_path,
        ).size

        # Setup progress bar
        desc = audeer.format_display_message(
            f"Download {os.path.basename(str(src_path))}",
            pbar=verbose,
        )
        pbar = audeer.progress_bar(total=src_size, desc=desc, disable=not verbose)

        try:
            if num_workers == 1:
                # Simple single-threaded download
                with pbar:
                    self._download_file(src_path, dst_path, pbar)
            else:
                # Multi-threaded download with pre-allocated file
                with open(dst_path, "wb") as f:
                    f.truncate(src_size)

                # Create and run download tasks
                tasks = []
                # Ensure num_workers does not exceed src_size
                num_workers = min(num_workers, src_size) if src_size > 0 else 1
                chunk_size = src_size // num_workers
                for i in range(num_workers):
                    offset = i * chunk_size
                    length = chunk_size if i < num_workers - 1 else src_size - offset
                    tasks.append(([src_path, dst_path, pbar, offset, length], {}))

                with pbar:
                    audeer.run_tasks(
                        self._download_file, tasks, num_workers=num_workers
                    )
        except KeyboardInterrupt:
            # Clean up partial file
            if os.path.exists(dst_path):
                os.remove(dst_path)
            raise

    def _download_file(
        self,
        src_path: str,
        dst_path: str,
        pbar,
        offset: int = 0,
        length: int | None = None,
    ):
        """Download file or part of file."""
        chunk_size = 4 * 1024  # 4 KB

        # Get the data stream
        kwargs = {"offset": offset}
        if length is not None:
            kwargs["length"] = length
        response = self._client.get_object(
            bucket_name=self.repository,
            object_name=src_path,
            **kwargs,
        )

        try:
            # When length is not None, we're in multi-worker mode
            # and the file is already pre-allocated, so use r+b for all workers.
            # When length is None, we're in single-worker mode and use wb.
            mode = "r+b" if length is not None else "wb"
            with open(dst_path, mode) as f:
                if offset:
                    f.seek(offset)

                while data := response.read(chunk_size):
                    f.write(data)
                    pbar.update(len(data))
        finally:
            response.close()
            response.release_conn()

    def _get_file_stream(
        self,
        src_path: str,
    ) -> Iterator[bytes]:
        r"""Get file from backend as byte stream."""
        from audbackend.core.backend.base import STREAM_CHUNK_SIZE

        src_path = self.path(src_path)

        response = self._client.get_object(
            bucket_name=self.repository,
            object_name=src_path,
        )

        try:
            while data := response.read(STREAM_CHUNK_SIZE):
                yield data
        finally:
            response.close()
            response.release_conn()

    def _ls(
        self,
        path: str,
    ) -> list[str]:
        r"""List all files under sub-path."""
        path = self.path(path)
        objects = self._client.list_objects(
            bucket_name=self.repository,
            prefix=path,
            recursive=True,
        )
        return [self._collapse(obj.object_name) for obj in objects]

    def _move_file(
        self,
        src_path: str,
        dst_path: str,
        num_workers: int,
        verbose: bool,
    ):
        r"""Move file on backend."""
        self._copy_file(src_path, dst_path, num_workers, verbose)
        self._remove_file(src_path)

    def _open(
        self,
    ):
        r"""Open connection to backend."""
        # At the moment, session management is handled automatically.
        # If we want to manage this ourselves,
        # we need to use the `http_client` argument of `minio.Minio`
        if not self._client.bucket_exists(bucket_name=self.repository):
            utils.raise_file_not_found_error(self.repository)

    def _owner(
        self,
        path: str,
    ) -> str:
        r"""Get owner of file on backend."""
        path = self.path(path)
        # NOTE:
        # we use a custom metadata entry to track the owner
        # as stats.owner_name is always empty.
        meta = self._client.stat_object(
            bucket_name=self.repository,
            object_name=path,
        ).metadata
        return meta["x-amz-meta-owner"] if "x-amz-meta-owner" in meta else ""

    def path(
        self,
        path: str,
    ) -> str:
        r"""Convert to backend path.

        Args:
            path: path on backend

        Returns:
            path

        """
        return path.replace(self.sep, "/").removeprefix("/")

    def _put_file(
        self,
        src_path: str,
        dst_path: str,
        checksum: str,
        verbose: bool,
    ):
        r"""Put file to backend."""
        dst_path = self.path(dst_path)
        if verbose:  # pragma: no cover
            desc = audeer.format_display_message(
                f"Deploy {src_path}",
                pbar=False,
            )
            print(desc, end="\r")

        content_type = mimetypes.guess_type(src_path)[0] or "application/octet-stream"
        self._client.fput_object(
            bucket_name=self.repository,
            object_name=dst_path,
            file_path=src_path,
            content_type=content_type,
            metadata=_metadata(checksum),
        )

        if verbose:  # pragma: no cover
            # Clear progress line
            print(audeer.format_display_message(" ", pbar=False), end="\r")

    def _remove_file(
        self,
        path: str,
    ):
        r"""Remove file from backend."""
        path = self.path(path)
        # Enforce error if path does not exist
        self._client.stat_object(
            bucket_name=self.repository,
            object_name=path,
        )
        self._client.remove_object(
            bucket_name=self.repository,
            object_name=path,
        )

    def _size(
        self,
        path: str,
    ) -> int:
        r"""Get size of file on backend."""
        path = self.path(path)
        size = self._client.stat_object(
            bucket_name=self.repository,
            object_name=path,
        ).size
        return size


def _metadata(checksum: str):
    """Dictionary with owner entry.

    When uploaded as metadata to MinIO,
    it can be accessed under ``stat_object(...).metadata["x-amz-meta-owner"]``.

    Args:
        checksum: checksum to be stored in metadata
    """
    return {
        "checksum": checksum,
        "owner": getpass.getuser(),
    }


def _parse_timeout(
    value: str | float | None,
    *,
    name: str,
    default: float | None,
) -> float | None:
    """Parse a timeout value from config.

    Converts string values to float, handling "None" as Python None.
    If parsing fails, logs a warning and returns the default value.

    Args:
        value: timeout value (string from config, float, or None)
        name: name of the timeout setting (for warning messages)
        default: default value to use if parsing fails

    Returns:
        parsed timeout value or default

    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        if value.lower() == "none":
            return None
    try:
        return float(value)
    except ValueError:
        warnings.warn(
            f"Invalid {name} value '{value}' in config, using default: {default}",
            UserWarning,
            stacklevel=4,
        )
        return default
