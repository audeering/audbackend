import typing

from audbackend.core.backend import Backend


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
            backend: Backend,
    ):
        self._backend = backend

    def __repr__(self) -> str:  # noqa: D105
        name = f'{self.__class__.__module__}.{self.__class__.__name__}'
        return f'{name}{self.backend}'

    @property
    def backend(self) -> Backend:
        r"""Backend object.

        Returns:
            backend object

        Examples:
            >>> interface.backend
            ('audbackend.core.backend.Backend', 'host', 'repo')

        """
        return self._backend

    @property
    def host(self) -> str:
        r"""Host path.

        Returns: host path

        Examples:
            >>> interface.host
            'host'

        """
        return self.backend.host

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

        Examples:
            >>> interface.join('/', 'f.ext')
            '/f.ext'
            >>> interface.join('/sub', 'f.ext')
            '/sub/f.ext'
            >>> interface.join('//sub//', '/', '', None, '/f.ext')
            '/sub/f.ext'

        """
        return self.backend.join(path, *paths)

    @property
    def repository(self) -> str:
        r"""Repository name.

        Returns:
            repository name

        Examples:
            >>> interface.repository
            'repo'

        """
        return self.backend.repository

    @property
    def sep(self) -> str:
        r"""File separator on backend.

        Returns:
            file separator

        Examples:
            >>> interface.sep
            '/'

        """
        return self.backend.sep

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

        Examples:
            >>> interface.split('/')
            ('/', '')
            >>> interface.split('/f.ext')
            ('/', 'f.ext')
            >>> interface.split('/sub/')
            ('/sub/', '')
            >>> interface.split('/sub//f.ext')
            ('/sub/', 'f.ext')

        """
        return self.backend.split(path)
