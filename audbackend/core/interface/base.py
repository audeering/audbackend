import os
import typing

import fsspec

from audbackend.core.backend.base import Base as Backend


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
        backend: backend object

    """

    def __init__(
        self,
        backend: fsspec.AbstractFileSystem,
    ):
        self.host = None
        self.repository = None
        self._backend = backend

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
        return f"audbackend.interface.{name}({self._backend})"

    @property
    def backend(self) -> Backend:
        r"""Backend object.

        Returns:
            backend object

        ..
            >>> fs = fsspec.filesystem("dir", path="./host/repo")
            >>> interface = Base(fs)

        Examples:
            >>> interface.backend
            'DirFileSystem'

        """
        return self._backend.__class__.__name__

    @property
    def host(self) -> str:
        r"""Host path.

        Returns: host path

        ..
            >>> fs = fsspec.filesystem("dir", path="./host/repo")
            >>> interface = Base(fs)

        Examples:
            >>> interface.host
            'host'

        """
        return self.host

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
        return os.path.join(path, *paths)

    @property
    def repository(self) -> str:
        r"""Repository name.

        Returns:
            repository name

        ..
            >>> fs = fsspec.filesystem("dir", path="./host/repo")
            >>> interface = Base(fs)

        Examples:
            >>> interface.repository
            'repo'

        """
        return self.repository

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
        root = self.sep.join(path.split(self.sep)[:-1]) + self.sep
        basename = path.split(self.sep)[-1]

        return root, basename
