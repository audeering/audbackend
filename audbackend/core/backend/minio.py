import configparser
import os
import typing

import minio

import audeer

from audbackend.core import utils
from audbackend.core.backend.base import Base


class Minio(Base):
    r"""Backend for MinIO.

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
        authentication: typing.Tuple[str, str] = None,
    ):
        super().__init__(host, repository, authentication=authentication)

        if authentication is None:
            self.authentication = self.get_authentication(host)

        # Open MinIO client
        self._client = minio.Minio(
            host,
            access_key=self.authentication[0],
            secret_key=self.authentication[1],
            secure=False,  # change later
        )

    @classmethod
    def get_authentication(cls, host: str) -> typing.Tuple[str, str]:
        """Username and password/access token for given host.

        Returns a authentication for MinIO server
        as tuple.

        To get the authentication tuple,
        the function looks first
        for the two environment variables
        ``MINIO_ACCESS_KEY`` and
        ``MINIO_SECRET_KEY``.
        Otherwise,
        it tries to extract missing values
        from a config file.
        The default path of the config file
        (:file:`~/.config/audbackend/minio.cfg`)
        can be overwritten with the environment variable
        ``MINIO_CONFIG_FILE``.
        If no config file exists
        or if it has missing entries,
        ``None`` is returned
        for the missing entries.

        Args:
            host: hostname

        Returns:
            access token tuple

        """
        access_key = os.getenv("MINIO_ACCESS_KEY", None)
        secret_key = os.getenv("MINIO_SECRET_KEY", None)
        config_file = os.getenv("MINIO_CONFIG_FILE", "~/.config/audbackend/minio.cfg")
        config_file = audeer.path(config_file)

        if os.path.exists(config_file) and (access_key is None or secret_key is None):
            config = configparser.ConfigParser(allow_no_value=True)
            config.read(config_file)
            if access_key is None:
                access_key = config.get(host, "access_key", fallback=None)
            if secret_key is None:
                secret_key = config.get(host, "secret_key", fallback=None)

        return access_key, secret_key

    def _checksum(
        self,
        path: str,
    ) -> str:
        r"""MD5 checksum of file on backend."""
        path = self.path(path)
        checksum = self._client.stat_object(self.repository, path).etag
        return checksum

    def _close(
        self,
    ):
        r"""Close connection to repository.

        An error should be raised,
        if the connection to the backend
        cannot be closed.

        """
        # At the moment, this is automatically handled.

    def _collapse(
        self,
        path,
    ):
        r"""Convert to virtual path.

        <path>
        ->
        /<path>

        """
        path = "/" + path
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
        # This has a maximum size limit of 5GB.
        stats = self._client.stat_object(self.repository, src_path)
        if stats.size / 1024 / 1024 / 1024 > 5:
            # TODO: implement copying with temporary file
            pass
        else:
            self._client.copy_object(
                self.repository,
                src_path,
                minio.commonconfig.CopySource(self.repository, dst_path),
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
        date = self.client.stat_object(self.repository, path).last_modified
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
        if path == "":
            # Return True for root
            return True
        try:
            self._client.stat_object(self.repository, path)
        except minio.error.S3Error:
            return False
        return True

    def _get_file(
        self,
        src_path: str,
        dst_path: str,
        verbose: bool,
    ):
        r"""Get file from backend."""
        src_path = self.path(src_path)
        src_size = self._client.stat_object(self.repository, src_path).size
        chunk = (4 * 1024,)
        with audeer.progress_bar(total=src_size, disable=not verbose) as pbar:
            desc = audeer.format_display_message(
                "Download {}".format(os.path.basename(str(src_path))),
                pbar=True,
            )
            pbar.set_description_str(desc)
            pbar.refresh()

            dst_size = 0
            try:
                response = self.client.get_object(self.repository, src_path)
                with open(dst_path, "wb") as dst_fp:
                    while src_size > dst_size:
                        data = response.read(chunk)
                        n_data = len(data)
                        if n_data > 0:
                            dst_fp.write(data)
                            dst_size += n_data
                            pbar.update(n_data)
            finally:
                response.close()
                response.release_conn()

    def _ls(
        self,
        path: str,
    ) -> typing.List[str]:
        r"""List all files under sub-path."""
        if not self._exists(path):
            return []

        path = self.path(path)
        objects = self._client.list_objects(
            self.repository,
            prefix=path,
            recursive=True,
        )
        paths = [self._collapse(obj.object_name) for obj in objects]

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
        # TODO: owner seems to be empty,
        # need to check if we have to manage this ourselves?
        owner = self._client.stat_object(self.repository, path).owner_name
        return owner

    def path(
        self,
        path: str,
    ) -> str:
        r"""Convert to backend path.

        This extends the relative ``path`` on the backend
        by :attr:`host` and :attr:`repository`,
        and returns an :class:`artifactory.ArtifactoryPath` object.

        Args:
            path: path on backend

        Returns:
            Artifactory path object

        """
        path = path.replace(self.sep, "/")
        if path.startswith("/"):
            # /path -> path
            path = path[1:]
        return path

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

        self._client.fput_object(self.repository, dst_path, src_path)

        if verbose:  # pragma: no cover
            # Clear progress line
            print(audeer.format_display_message(" ", pbar=False), end="\r")

    def _remove_file(
        self,
        path: str,
    ):
        r"""Remove file from backend."""
        path = self.path(path)
        self._client.remove_object(self.repository, path)
