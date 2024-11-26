import audeer

import audbackend


class BadFileSystem(audbackend.backend.FileSystem):
    r"""Imitates a corrupted file system."""

    # Overwrite `put_file()` to avoid calling it `exists()`
    def put_file(
        self,
        src_path: str,
        dst_path: str,
        *,
        validate: bool = False,
        verbose: bool = False,
    ):
        r"""Put file on backend."""
        checksum = audeer.md5(src_path)
        audbackend.core.utils.call_function_on_backend(
            self._put_file,
            src_path,
            dst_path,
            checksum,
            verbose,
        )

    def _get_file(
        self,
        src_path: str,
        dst_path: str,
        verbose: bool,
    ):
        super()._get_file(src_path, dst_path, verbose)
        # raise error after file was retrieved
        raise InterruptedError()

    def _exists(
        self,
        path: str,
    ):
        # raise error when checking if file exists
        raise InterruptedError()
