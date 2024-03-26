import getpass
import os
import time

import pytest
from bad_file_system import BadFileSystem
from singlefolder import SingleFolder

import audeer

import audbackend


# list of backends to test
pytest.BACKENDS = [
    "artifactory",
    "file-system",
    "single-folder",
]


# UID for test session
# Repositories on the host will be named
# unittest-<session-uid>-<repository-uid>
pytest.UID = audeer.uid()[:8]


@pytest.fixture(scope="package", autouse=True)
def register_single_folder():
    audbackend.register("single-folder", SingleFolder)


@pytest.fixture(scope="package", autouse=False)
def hosts(tmpdir_factory):
    return {
        # For tests based on backend names (deprecated),
        # like audbackend.access()
        "artifactory": "https://audeering.jfrog.io/artifactory",
        "file-system": str(tmpdir_factory.mktemp("host")),
        "single-folder": str(tmpdir_factory.mktemp("host")),
        # For tests using backend classes
        audbackend.backend.Artifactory: "https://audeering.jfrog.io/artifactory",
        audbackend.backend.FileSystem: str(tmpdir_factory.mktemp("host")),
        SingleFolder: str(tmpdir_factory.mktemp("host")),
        BadFileSystem: str(tmpdir_factory.mktemp("host")),
    }


@pytest.fixture(scope="package", autouse=False)
def backends():
    return {
        "artifactory": audbackend.backend.Artifactory,
        "file-system": audbackend.backend.FileSystem,
        "single-folder": SingleFolder,
    }


@pytest.fixture(scope="function", autouse=False)
def owner(request):
    r"""Return expected owner value."""
    backend = request.param
    if backend == audbackend.backend.Artifactory:
        owner = audbackend.core.backend.artifactory._authentication(
            "audeering.jfrog.io/artifactory"
        )[0]
    else:
        if os.name == "nt":
            owner = "Administrators"
        else:
            owner = getpass.getuser()

    yield owner


@pytest.fixture(scope="function", autouse=False)
def interface(hosts, request):
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
    host = hosts[backend_cls]
    repository = f"unittest-{pytest.UID}-{audeer.uid()[:8]}"

    backend = backend_cls.create(host, repository)
    interface = interface_cls(backend)

    yield interface

    # Deleting repositories on Artifactory might fail
    for n in range(3):
        try:
            backend_cls.delete(host, repository)
            break
        except audbackend.BackendError:
            if n == 2:
                error_msg = (
                    f"Cleaning up of repo {repository} failed.\n"
                    "Please delete remaining repositories manually \n"
                    "by running the following command \n"
                    "when no tests are actively running:\n"
                    f"python tests/misc/cleanup_artifactory.py"
                )
                raise RuntimeError(error_msg)
            time.sleep(1)


@pytest.fixture(scope="package", autouse=True)
def cleanup_coverage():
    # clean up old coverage files
    path = audeer.path(
        os.path.dirname(os.path.realpath(__file__)),
        ".coverage.*",
    )
    for file in audeer.list_file_names(path):
        os.remove(file)
