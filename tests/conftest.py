import getpass
import os

import pytest

import audeer

import audbackend

from singlefolder import SingleFolder


# UID for test session
# Repositories on the host will be named
# unittest-<session-uid>-<repository-uid>
pytest.UID = audeer.uid()[:8]

# Define static hosts
pytest.HOSTS = {
    "artifactory": "https://audeering.jfrog.io/artifactory",
    "minio": "play.min.io",
}


@pytest.fixture(scope="package", autouse=True)
def authentication():
    """Provide authentication tokens for supported backends."""
    if pytest.HOSTS["minio"] == "play.min.io":
        defaults = {}
        for key in [
            "MINIO_ACCESS_KEY",
            "MINIO_SECRET_KEY",
        ]:
            defaults[key] = os.environ.get(key, None)

        os.environ["MINIO_ACCESS_KEY"] = "Q3AM3UQ867SPQQA43P2F"
        os.environ["MINIO_SECRET_KEY"] = "zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG"

        yield

        for key, value in defaults.items():
            if value is not None:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]


@pytest.fixture(scope="package", autouse=True)
def register_single_folder():
    warning = (
        "register is deprecated and will be removed with version 2.2.0. "
        "Use backend classes directly instead."
    )
    with pytest.warns(UserWarning, match=warning):
        audbackend.register("single-folder", SingleFolder)


@pytest.fixture(scope="package", autouse=False)
def hosts(tmpdir_factory):
    return {
        # For tests based on backend names (deprecated),
        # like audbackend.access()
        "artifactory": pytest.HOSTS["artifactory"],
        "file-system": str(tmpdir_factory.mktemp("host")),
        "minio": pytest.HOSTS["minio"],
        "single-folder": str(tmpdir_factory.mktemp("host")),
    }


@pytest.fixture(scope="function", autouse=False)
def owner(request):
    r"""Return expected owner value."""
    backend_cls = request.param
    if (
        hasattr(audbackend.backend, "Artifactory")
        and backend_cls == audbackend.backend.Artifactory
    ):
        host_wo_https = pytest.HOSTS["artifactory"][8:]
        owner = backend_cls.get_authentication(host_wo_https)[0]
    else:
        if os.name == "nt":
            owner = "Administrators"
        else:
            owner = getpass.getuser()

    yield owner


@pytest.fixture(scope="function", autouse=False)
def interface(tmpdir_factory, request):
    r"""Create a backend with interface.

    This fixture should be called indirectly
    providing a list of ``(backend, interface)`` tuples.
    For example, to create a file-system backend
    and access it with a versioned interface:

    .. code-block:: python

        @pytest.mark.parametrize(
            "interface",
            [(audbackend.backend.FileSystem, audbackend.interface.Versioned)],
            indirect=True,
        )

    At the end of the test the backend is deleted.

    """
    backend_cls, interface_cls = request.param
    artifactory = False
    if (
        hasattr(audbackend.backend, "Artifactory")
        and backend_cls == audbackend.backend.Artifactory
    ):
        artifactory = True
        host = pytest.HOSTS["artifactory"]
    elif (
        hasattr(audbackend.backend, "Minio") and backend_cls == audbackend.backend.Minio
    ):
        host = pytest.HOSTS["minio"]
    else:
        host = str(tmpdir_factory.mktemp("host"))
    repository = f"unittest-{pytest.UID}-{audeer.uid()[:8]}"

    backend_cls.create(host, repository)
    with backend_cls(host, repository) as backend:
        interface = interface_cls(backend)

        yield interface

        if artifactory:
            import dohq_artifactory

            try:
                backend._repo.delete()
            except dohq_artifactory.exception.ArtifactoryException:
                # It might happen from time to time,
                # that a repository cannot be deleted.
                # In those cases,
                # we don't raise an error here,
                # but rely on the user calling the clean up script
                # from time to time:
                # $ python tests/misc/cleanup_artifactory.py
                pass

    if not artifactory:
        backend_cls.delete(host, repository)


@pytest.fixture(scope="package", autouse=True)
def cleanup_coverage():
    # clean up old coverage files
    path = audeer.path(
        os.path.dirname(os.path.realpath(__file__)),
        ".coverage.*",
    )
    for file in audeer.list_file_names(path):
        os.remove(file)
