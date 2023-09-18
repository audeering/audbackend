import datetime
import os
import shutil
import typing

import audeer

from audbackend.core import utils
from audbackend.core.backend import Backend


class FileSystem(Backend):
    r"""Backend for file system.

    Args:
        host: host directory
        repository: repository name

    """
    def __init__(
            self,
            host: str,
            repository: str,
    ):
        super().__init__(host, repository)

        self._root = audeer.path(host, repository) + os.sep

        # to support legacy file structure
        # see _use_legacy_file_structure()
        self._legacy_extensions = []
        self._legacy_file_structure = False

    def _access(
            self,
    ):
        r"""Access existing repository."""
        if not os.path.exists(self._root):
            utils.raise_file_not_found_error(self._root)

    def _checksum(
            self,
            path: str,
            version: str,
    ) -> str:
        r"""MD5 checksum of file on backend."""
        path = self._path(path, version)
        return audeer.md5(path)

    def _collapse(
            self,
            path,
    ):
        r"""Convert to virtual path.

        <host>/<repository>/<path>
        ->
        /<path>

        """
        path = path[len(self._root) - 1:]  # remove host and repo
        path = path.replace(os.path.sep, self.sep)
        return path

    def _create(
            self,
    ):
        r"""Access existing repository."""
        if os.path.exists(self._root):
            utils.raise_file_exists_error(self._root)

        audeer.mkdir(self._root)

    def _date(
            self,
            path: str,
            version: str,
    ) -> str:
        r"""Get last modification date of file on backend."""
        path = self._path(path, version)
        date = os.path.getmtime(path)
        date = datetime.datetime.fromtimestamp(date)
        date = utils.date_format(date)
        return date

    def _delete(
            self,
    ):
        r"""Delete repository and all its content."""
        audeer.rmdir(self._root)

    def _exists(
            self,
            path: str,
            version: str,
    ) -> bool:
        r"""Check if file exists on backend."""
        path = self._path(path, version)
        return os.path.exists(path)

    def _expand(
            self,
            path: str,
    ) -> str:
        r"""Convert to backend path.

        <path>
        ->
        <host>/<repository>/<path>

        """
        path = path.replace(self.sep, os.path.sep)
        if path.startswith(os.path.sep):
            path = path[1:]
        path = os.path.join(self._root, path)
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
        shutil.copy(src_path, dst_path)

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
            if not os.path.exists(path):
                utils.raise_file_not_found_error(path)
            paths = audeer.list_file_names(
                path,
                recursive=True,
                hidden=True,
            )

        else:  # find versions of path

            root, name = self.split(path)

            if self._legacy_file_structure:
                base, _ = self._legacy_split_ext(name)
                root = f'{self._expand(root)}{base}'
            else:
                root = self._expand(root)

            vs = audeer.list_dir_names(
                root,
                basenames=True,
                hidden=True,
            )

            # filter out other files with same root and version
            paths = [self._path(path, v) for v in vs if self._exists(path, v)]

            if not paths:
                utils.raise_file_not_found_error(path)

        # <host>/<repository>/<root>/<version>/<name>
        # ->
        # (/<root>/<name>, <version>)

        result = []
        for p in paths:

            p = self._collapse(p)  # remove host and repo
            tokens = p.split(self.sep)

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
        owner = utils.file_owner(path)
        return owner

    def _path(
            self,
            path: str,
            version: str,
    ) -> str:
        r"""Convert to backend path.

        <host>/<repository>/<root>/<name>
        ->
        <host>/<repository>/<root>/<version>/<name>

        """
        root, name = self.split(path)
        root = self._expand(root)

        if self._legacy_file_structure:
            base, ext = self._legacy_split_ext(name)
            path = os.path.join(root, base, version, f'{base}-{version}{ext}')
        else:
            path = os.path.join(root, version, name)

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
        audeer.mkdir(os.path.dirname(dst_path))
        shutil.copy(src_path, dst_path)

    def _remove_file(
            self,
            path: str,
            version: str,
    ):
        r"""Remove file from backend."""
        path = self._path(path, version)
        os.remove(path)

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
