import concurrent.futures
import configparser
import getpass
import mimetypes
import os
import tempfile
import threading

import minio

import audeer

from audbackend.core import utils
from audbackend.core.backend.base import Base


class Minio(Base):
    r"""Backend for MinIO.

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

        if secure is None:
            config = self.get_config(host)
            secure = config.get("secure", True)

        # Open MinIO client
        self._client = minio.Minio(
            host,
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
        meta = self._client.stat_object(self.repository, path).metadata
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
                self.repository,
                dst_path,
                minio.commonconfig.CopySource(self.repository, src_path),
                metadata=_metadata(checksum),
            )

    def _create(
        self,
    ):
        r"""Create repository."""
        if self._client.bucket_exists(self.repository):
            utils.raise_file_exists_error(self.repository)
        self._client.make_bucket(self.repository)

    def _date(
        self,
        path: str,
    ) -> str:
        r"""Get last modification date of file on backend."""
        path = self.path(path)
        date = self._client.stat_object(self.repository, path).last_modified
        date = utils.date_format(date)
        return date

    def _delete(
        self,
    ):
        r"""Delete repository and all its content."""
        # Delete all objects in bucket
        objects = self._client.list_objects(self.repository, recursive=True)
        for obj in objects:
            self._client.remove_object(self.repository, obj.object_name)
        # Delete bucket
        self._client.remove_bucket(self.repository)

    def _exists(
        self,
        path: str,
    ) -> bool:
        r"""Check if file exists on backend."""
        path = self.path(path)
        try:
            self._client.stat_object(self.repository, path)
        except minio.error.S3Error:
            return False
        return True

    def _get_file(
        self,
        src_path: str,
        dst_path: str,
        num_workers: int,
        verbose: bool,
        *,
        chunk_size: int = 50 * 1024 * 1024,  # 50MB
    ):
        r"""Get file from backend."""
        src_path = self.path(src_path)
        src_size = self._client.stat_object(self.repository, src_path).size

        # Pre-allocate local file of same size
        with open(dst_path, "wb") as f:
            f.truncate(src_size)

        params = []
        for offset in range(0, src_size, chunk_size):
            length = min(chunk_size, src_size - offset)
            params.append(([src_path, dst_path, offset, length], {}))
        audeer.run_tasks(
            self._get_file_part,
            params,
            num_workers=num_workers,
            progress_bar=verbose,
        )

    def _get_file_part(
        self,
        src_path: str,
        dst_path: str,
        offset: int,
        length: int,
    ):
        """Get part of file from backend."""
        try:
            # Fetch byte range from remote file
            response = self._client.get_object(
                self.repository,
                src_path,
                offset=offset,
                length=length,
            )
            data = response.read()
            # Write into correct spot in local file
            with open(dst_path, "r+b") as fp:
                fp.seek(offset)
                fp.write(data)
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"Error downloading file: {e}")
        finally:
            response.close()
            response.release_conn()

    def _get_file_sequential(
        self,
        src_path: str,
        dst_path: str,
        src_size: int,
        chunk_size: int,
        verbose: bool,
    ):
        r"""Download file sequentially."""
        with audeer.progress_bar(total=src_size, disable=not verbose) as pbar:
            desc = audeer.format_display_message(
                f"Download {os.path.basename(str(src_path))}", pbar=True
            )
            pbar.set_description_str(desc)
            pbar.refresh()

            dst_size = 0
            try:
                response = self._client.get_object(self.repository, src_path)
                with open(dst_path, "wb") as dst_fp:
                    while src_size > dst_size:
                        data = response.read(chunk_size)
                        n_data = len(data)
                        if n_data > 0:
                            dst_fp.write(data)
                            dst_size += n_data
                            pbar.update(n_data)
            except Exception as e:  # pragma: no cover
                raise RuntimeError(f"Error downloading file: {e}")
            finally:
                response.close()
                response.release_conn()

    def _get_file_parallel(
        self,
        src_path: str,
        dst_path: str,
        src_size: int,
        num_workers: int,
        chunk_size: int,
        verbose: bool,
    ):
        r"""Download file in parallel using multiple workers."""
        # Calculate part size for each worker
        part_size = src_size // num_workers
        if part_size == 0:
            # File too small for parallel download, use sequential
            self._get_file_sequential(src_path, dst_path, src_size, chunk_size, verbose)
            return

        # Create temporary directory for parts
        with tempfile.TemporaryDirectory() as temp_dir:
            # Thread-safe progress bar
            pbar_lock = threading.Lock()

            with audeer.progress_bar(total=src_size, disable=not verbose) as pbar:
                desc = audeer.format_display_message(
                    f"Download {os.path.basename(str(src_path))}", pbar=True
                )
                pbar.set_description_str(desc)
                pbar.refresh()

                def download_part(part_num):
                    """Download a single part of the file."""
                    start = part_num * part_size
                    # Last part gets remaining bytes
                    end = (
                        src_size - 1
                        if part_num == num_workers - 1
                        else (part_num + 1) * part_size - 1
                    )

                    part_file = os.path.join(temp_dir, f"part_{part_num}")

                    try:
                        response = self._client.get_object(
                            self.repository,
                            src_path,
                            offset=start,
                            length=end - start + 1,
                        )
                        with open(part_file, "wb") as f:
                            downloaded = 0
                            while True:
                                data = response.read(chunk_size)
                                n_data = len(data)
                                if n_data == 0:
                                    break
                                f.write(data)
                                downloaded += n_data
                                with pbar_lock:
                                    pbar.update(n_data)
                        return part_num, part_file
                    except Exception as e:  # pragma: no cover
                        raise RuntimeError(f"Error downloading part {part_num}: {e}")
                    finally:
                        response.close()
                        response.release_conn()

                # Download parts in parallel
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=num_workers
                ) as executor:
                    futures = [
                        executor.submit(download_part, i) for i in range(num_workers)
                    ]
                    parts = [None] * num_workers

                    for future in concurrent.futures.as_completed(futures):
                        part_num, part_file = future.result()
                        parts[part_num] = part_file

                # Combine parts into final file
                with open(dst_path, "wb") as dst_fp:
                    for part_file in parts:
                        with open(part_file, "rb") as src_fp:
                            dst_fp.write(src_fp.read())

    def _ls(
        self,
        path: str,
    ) -> list[str]:
        r"""List all files under sub-path."""
        path = self.path(path)
        objects = self._client.list_objects(
            self.repository,
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
        if not self._client.bucket_exists(self.repository):
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
        meta = self._client.stat_object(self.repository, path).metadata
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
            self.repository,
            dst_path,
            src_path,
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
        self._client.stat_object(self.repository, path)
        self._client.remove_object(self.repository, path)

    def _size(
        self,
        path: str,
    ) -> int:
        r"""Get size of file on backend."""
        path = self.path(path)
        size = self._client.stat_object(self.repository, path).size
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
