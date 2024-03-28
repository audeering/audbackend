import getpass
import os
import time

import pytest

import audeer

import audbackend

from singlefolder import SingleFolder


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
    }


@pytest.fixture(scope="function", autouse=False)
def owner(request):
    r"""Return expected owner value."""
    backend_cls = request.param
    if (
        hasattr(audbackend.backend, "Artifactory")
        and backend_cls == audbackend.backend.Artifactory
    ):
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
    if (
        hasattr(audbackend.backend, "Artifactory")
        and backend_cls == audbackend.backend.Artifactory
    ):
        host = "https://audeering.jfrog.io/artifactory"
    else:
        host = str(tmpdir_factory.mktemp("host"))
    repository = f"unittest-{pytest.UID}-{audeer.uid()[:8]}"

    backend_cls.create(host, repository)
    backend = backend_cls(host, repository)
    interface = interface_cls(backend)

    yield interface

    # Deleting repositories on Artifactory might fail
    for n in range(3):
        try:
            backend_cls.delete(host, repository)
            break
        except audbackend.BackendError:
            if n == 2:
                warning_msg = (
                    f"Cleaning up of repo {repository} failed.\n"
                    "Please delete remaining repositories manually \n"
                    "by running the following command \n"
                    "when no tests are actively running:\n"
                    f"python tests/misc/cleanup_artifactory.py"
                )
                warnings.warn(warning_msg, UserWarning)
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
