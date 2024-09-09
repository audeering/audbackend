import typing

import fsspec

from audbackend.core import utils


class Base:
    r"""Interface base class.

    Provides an interface to a backend,
    see e.g.
    :class:`audbackend.Unversioned`
    and
    :class:`audbackend.Versioned`.

    Derive from this class to
    create a new interface.

    Args:
        fs: filesystem object
            following :mod:`fsspec` specifications

    """

    def __init__(
        self,
        fs: fsspec.AbstractFileSystem,
        *,
        repository: str = None,
    ):
        self.fs = fs
        """Filesystem object."""

    def __repr__(self) -> str:
        r"""String representation.

        ..
            >>> fs = fsspec.filesystem("dir", path="./host/repo")
            >>> interface = Base(fs)

        Examples:
            >>> interface
            'audbackend.interface.Base(DirFileSystem)'

        """
        name = self.__class__.__name__
        return f"audbackend.interface.{name}({self.fs.__class__.__name__})"

    def join(
        self,
        path: str,
        *paths,
    ) -> str:
        r"""Join to path on backend.

        Args:
            path: first part of path
            *paths: additional parts of path

        Returns:
            path joined by :attr:`Backend.sep`

        Raises:
            ValueError: if ``path`` contains invalid character
                or does not start with ``'/'``,
                or if joined path contains invalid character

        ..
            >>> fs = fsspec.filesystem("dir", path="./host/repo")
            >>> interface = Base(fs)

        Examples:
            >>> interface.join("/", "file.txt")
            '/file.txt'
            >>> interface.join("/sub", "file.txt")
            '/sub/file.txt'
            >>> interface.join("//sub//", "/", "", None, "/file.txt")
            '/sub/file.txt'

        """
        path = utils.check_path(path, allow_sub_path=True)

        paths = [path] + [p for p in paths]
        paths = [path for path in paths if path]  # remove empty or None
        path = self.sep.join(paths)

        path = utils.check_path(path, allow_sub_path=True)

        return path

    @property
    def sep(self) -> str:
        r"""File separator on backend.

        Returns:
            file separator

        ..
            >>> fs = fsspec.filesystem("dir", path="./host/repo")
            >>> interface = Base(fs)

        Examples:
            >>> interface.sep
            '/'

        """
        return "/"

    def split(
        self,
        path: str,
    ) -> typing.Tuple[str, str]:
        r"""Split path on backend into sub-path and basename.

        Args:
            path: path containing :attr:`Backend.sep` as separator

        Returns:
            tuple containing (root, basename)

        Raises:
            ValueError: if ``path`` does not start with ``'/'`` or
                does not match ``'[A-Za-z0-9/._-]+'``

        ..
            >>> fs = fsspec.filesystem("dir", path="./host/repo")
            >>> interface = Base(fs)

        Examples:
            >>> interface.split("/")
            ('/', '')
            >>> interface.split("/file.txt")
            ('/', 'file.txt')
            >>> interface.split("/sub/")
            ('/sub/', '')
            >>> interface.split("/sub//file.txt")
            ('/sub/', 'file.txt')

        """
        path = utils.check_path(path)
        root = self.sep.join(path.split(self.sep)[:-1]) + self.sep
        basename = path.split(self.sep)[-1]

        return root, basename
