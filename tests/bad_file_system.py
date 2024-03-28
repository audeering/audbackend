import audbackend


class BadFileSystem(audbackend.backend.FileSystem):
    r"""Imitates a corrupted file system."""

    def _get_file(
        self,
        src_path: str,
        dst_path: str,
        verbose: bool,
    ):
        super()._get_file(src_path, dst_path, verbose)
        # raise error after file was retrieved
        raise InterruptedError()
