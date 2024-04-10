import fnmatch
import os
import tempfile
import typing

import audeer

from audbackend.core import utils
from audbackend.core.errors import BackendError


class BaseAuthentication:
    r"""Backend base class with authentication.

    Derive from this class to implement a new backend.

    """

    def __init__(
        self,
        host: str,
        repository: str,
        *,
        auth: typing.Any = None,
    ):
        super().__init__(host, repository, auth=auth)

        self.auth = auth
        r"""Access token."""

    @classmethod
    def create(
        cls,
        host: str,
        repository: str,
        *,
        auth: typing.Any = None,
    ):
        r"""Create repository.

        Creates ``repository``
        located at ``host``
        on the backend.

        Args:
            host: host address
            repository: repository name
            auth: access token
                for backends
                that require authentication,
                e.g. username, password tuple

        Raises:
            BackendError: if an error is raised on the backend,
                e.g. repository exists already
                or cannot be created

        """
        backend = cls(host, repository, auth=auth)
        utils.call_function_on_backend(backend._create)

    @classmethod
    def delete(
        cls,
        host: str,
        repository: str,
        *,
        auth: typing.Any = None,
    ):
        r"""Delete repository.

        Deletes ``repository``
        located at ``host``
        on the backend.

        Args:
            host: host address
            repository: repository name
            auth: access token
                for backends
                that require authentication,
                e.g. username, password tuple

        Raises:
            BackendError: if an error is raised on the backend,
                e.g. repository does not exist

        """
        backend = cls(host, repository, auth=auth)
        utils.call_function_on_backend(backend._delete)
