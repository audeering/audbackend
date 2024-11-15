from collections.abc import Sequence
import fnmatch
import os
import re

import audeer

from audbackend.core import utils
from audbackend.core.backend.base import Base as Backend
from audbackend.core.errors import BackendError
from audbackend.core.interface.versioned import Versioned


class Maven(Versioned):
    r"""Interface for Maven style versioned file access.

    Use this interface,
    if you want to version files
    similar to how it is handled by Maven.
    For each file on the backend path
    one or more versions may exist.

    Files are stored under
    ``".../<name-wo-ext>/<version>/<name-wo-ext>-<version>.<ext>"``.
    By default,
    the extension
    ``<ext>``
    is set to the string after the last dot.
    I.e.,
    the backend path
    ``".../file.tar.gz"``
    will translate into
    ``".../file.tar/1.0.0/file.tar-1.0.0.gz"``.
    However,
    by passing a list with custom extensions
    it is possible to overwrite
    the default behavior
    for certain extensions.
    E.g.,
    with ``extensions=["tar.gz"]``
    it is ensured that
    ``"tar.gz"``
    will be recognized as an extension
    and the backend path
    ``".../file.tar.gz"``
    will then translate into
    ``".../file/1.0.0/file-1.0.0.tar.gz"``.
    If ``regex`` is set to ``True``,
    the extensions are treated as regular expressions.

    Args:
        backend: file storage backend
        extensions: list of file extensions to support
            including a ``"."``.
            Per default only the part after the last ``"."``,
            is considered as a file extension
        regex: if ``True``,
            ``extensions`` entries
            are treated as regular expressions.
            E.g. ``"\d+.tar.gz"`` will match
            ``"1.tar.gz"``,
            ``"2.tar.gz"``,
            ...
            as extensions

    ..
        >>> import audbackend
        >>> import audeer

    Examples:
        >>> host = audeer.mkdir("host")
        >>> audbackend.backend.FileSystem.create(host, "repo")
        >>> backend = audbackend.backend.FileSystem(host, "repo")
        >>> backend.open()
        >>> interface = Maven(backend)
        >>> file = "src.txt"
        >>> interface.put_archive(".", "/sub/archive.zip", "1.0.0", files=[file])
        >>> for version in ["1.0.0", "2.0.0"]:
        ...     interface.put_file(file, "/file.txt", version)
        >>> interface.ls()
        [('/file.txt', '1.0.0'), ('/file.txt', '2.0.0'), ('/sub/archive.zip', '1.0.0')]
        >>> interface.get_file("/file.txt", "dst.txt", "2.0.0")
        '...dst.txt'

    """  # noqa: E501

    def __init__(
        self,
        backend: Backend,
        *,
        extensions: Sequence[str] = [],
        regex: bool = False,
    ):
        super().__init__(backend)
        self.extensions = extensions
        self.regex = regex

    def ls(
        self,
        path: str = "/",
        *,
        latest_version: bool = False,
        pattern: str = None,
        suppress_backend_errors: bool = False,
    ) -> list[tuple[str, str]]:
        r"""List files on backend.

        Returns a sorted list of tuples
        with path and version.
        If a full path
        (e.g. ``/sub/file.ext``)
        is provided,
        all versions of the path are returned.
        If a sub-path
        (e.g. ``/sub/``)
        is provided,
        all files that start with
        the sub-path are returned.
        When ``path`` is set to ``'/'``
        a (possibly empty) list with
        all files on the backend is returned.

        Args:
            path: path or sub-path
                (if it ends with ``'/'``)
                on backend
            latest_version: if multiple versions of a file exist,
                only include the latest
            pattern: if not ``None``,
                return only files matching the pattern string,
                see :func:`fnmatch.fnmatch`
            suppress_backend_errors: if set to ``True``,
                silently catch errors raised on the backend
                and return an empty list

        Returns:
            list of tuples (path, version)

        Raises:
            BackendError: if ``suppress_backend_errors`` is ``False``
                and an error is raised on the backend,
                e.g. ``path`` does not exist
            ValueError: if ``path`` does not start with ``'/'`` or
                does not match ``'[A-Za-z0-9/._-]+'``
            RuntimeError: if backend was not opened

        ..
            >>> interface = Maven(filesystem)

        Examples:
            >>> file = "src.txt"
            >>> interface.put_archive(".", "/sub/archive.zip", "1.0.0", files=[file])
            >>> for version in ["1.0.0", "2.0.0"]:
            ...     interface.put_file(file, "/file.txt", version)
            >>> interface.ls()
            [('/file.txt', '1.0.0'), ('/file.txt', '2.0.0'), ('/sub/archive.zip', '1.0.0')]
            >>> interface.ls(latest_version=True)
            [('/file.txt', '2.0.0'), ('/sub/archive.zip', '1.0.0')]
            >>> interface.ls("/file.txt")
            [('/file.txt', '1.0.0'), ('/file.txt', '2.0.0')]
            >>> interface.ls(pattern="*.txt")
            [('/file.txt', '1.0.0'), ('/file.txt', '2.0.0')]
            >>> interface.ls(pattern="archive.*")
            [('/sub/archive.zip', '1.0.0')]
            >>> interface.ls("/sub/")
            [('/sub/archive.zip', '1.0.0')]

        """  # noqa: E501
        if path.endswith("/"):  # find files under sub-path
            paths = self.backend.ls(
                path,
                suppress_backend_errors=suppress_backend_errors,
            )
            # Files are also stored as sub-folder,
            # e.g. `.../<name>/<version>/<name>-<version><ext>`,
            # so we need to skip those
            sub_paths = len(path.split("/")) - 2
            if sub_paths > 0:
                paths = [
                    path for path in paths if len(path.split(self.sep)) > 3 + sub_paths
                ]

        else:  # find versions of path
            root, file = self.split(path)
            name, ext = self._split_ext(file)

            # Look inside `<root>/<name>/`
            # for available versions.
            # It will return entries in the form
            # `<root>/<name>/<version>/<name>-<version><ext>`
            paths = self.backend.ls(
                self.backend.join(root, name, self.sep),
                suppress_backend_errors=suppress_backend_errors,
            )

            # filter for '<root>/<name>/<version>/<name>-x.x.x<ext>'
            depth = root.count("/") + 2
            match = re.compile(rf"{name}-\d+\.\d+.\d+{ext}")
            paths = [
                p
                for p in paths
                if (p.count("/") == depth and match.match(os.path.basename(p)))
            ]

            if not paths and not suppress_backend_errors:
                # since the backend does no longer raise an error
                # if the path does not exist
                # we have to do it
                try:
                    utils.raise_file_not_found_error(path)
                except FileNotFoundError as ex:
                    raise BackendError(ex)

        if not paths:
            return []

        paths_and_versions = []
        for p in paths:
            # Split into
            # ["", ..., <name>, <version>, <name>-<version><ext>]
            tokens = p.split(self.sep)
            version = tokens[-2]

            if version:
                root = self.sep.join(tokens[:-3])
                name = tokens[-3]
                name_version_ext = tokens[-1]

                ext = name_version_ext[len(name) + len(version) + 1 :]
                file = f"{name}{ext}"

                path = self.join(self.sep, root, file)

                if not pattern or fnmatch.fnmatch(os.path.basename(path), pattern):
                    paths_and_versions.append((path, version))

        paths_and_versions = sorted(paths_and_versions)

        if latest_version:
            # d[path] = ['1.0.0', '2.0.0']
            d = {}
            for p, v in paths_and_versions:
                if p not in d:
                    d[p] = []
                d[p].append(v)
            # d[path] = '2.0.0'
            for p, vs in d.items():
                d[p] = audeer.sort_versions(vs)[-1]
            # [(path, '2.0.0')]
            paths_and_versions = [(p, v) for p, v in d.items()]

        return paths_and_versions

    def _split_ext(
        self,
        name: str,
    ) -> tuple[str, str]:
        r"""Split name into basename and extension."""
        ext = None
        for custom_ext in self.extensions:
            # check for custom extension
            # ensure basename is not empty
            if self.regex:
                pattern = rf"\.({custom_ext})$"
                match = re.search(pattern, name[1:])
                if match:
                    ext = match.group(1)
            elif name[1:].endswith(f".{custom_ext}"):
                ext = custom_ext
        if ext is None:
            # if no custom extension is found
            # use last string after dot
            ext = audeer.file_extension(name)

        base = audeer.replace_file_extension(name, "", ext=ext)

        if ext:
            ext = f".{ext}"

        return base, ext

    def _path_with_version(
        self,
        path: str,
        version: str,
    ) -> str:
        r"""Convert to versioned path.

        <root>/<base><ext>
        ->
        <root>/<base>/<version>/<base>-<version><ext>

        """
        version = utils.check_version(version)
        root, name = self.split(path)
        base, ext = self._split_ext(name)
        path = self.join(root, base, version, f"{base}-{version}{ext}")
        return path
