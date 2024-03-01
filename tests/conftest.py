import getpass
import os
import time

import pytest
from singlefolder import SingleFolder

import audeer

import audbackend


# list of backends to test
pytest.BACKENDS = [
    'artifactory',
    'file-system',
    'single-folder',
]


# list of interfaces to test
pytest.UNVERSIONED = [
    (backend, audbackend.interface.Unversioned)
    for backend in pytest.BACKENDS
]
pytest.VERSIONED = [
    ('file-system', audbackend.interface.Versioned),
]

# UID for test session
# Repositories on the host will be named
# unittest-<session-uid>-<repository-uid>
pytest.UID = audeer.uid()[:8]


@pytest.fixture(scope='package', autouse=True)
def register_single_folder():
    if os.name != 'nt':
        audbackend.register('single-folder', SingleFolder)


@pytest.fixture(scope='package', autouse=False)
def hosts(tmpdir_factory):
    return {
        'artifactory': 'https://audeering.jfrog.io/artifactory',
        'file-system': str(tmpdir_factory.mktemp('host')),
        'single-folder': str(tmpdir_factory.mktemp('host')),
    }


@pytest.fixture(scope='function', autouse=False)
def owner(request):
    r"""Return expected owner value."""
    name = request.param
    if name == 'artifactory':
        owner = audbackend.core.backend.artifactory._authentication(
            'audeering.jfrog.io/artifactory'
        )[0]
    else:
        if os.name == 'nt':
            owner = 'Administrators'
        else:
            owner = getpass.getuser()

    yield owner


@pytest.fixture(scope='function', autouse=False)
def interface(hosts, request):

    name, interface_cls = request.param
    host = hosts[name]
    repository = f'unittest-{pytest.UID}-{audeer.uid()[:8]}'

    audbackend.create(name, host, repository)
    interface = audbackend.access(
        name,
        host,
        repository,
        interface=interface_cls,
    )

    yield interface

    # Deleting repositories on Artifactory might fail
    for n in range(3):
        try:
            audbackend.delete(name, host, repository)
            break
        except audbackend.BackendError:
            if n == 2:
                error_msg = (
                    f'Cleaning up of repo {repository} failed.\n'
                    'Please delete remaining repositories manually \n'
                    'by running the following command \n'
                    'when no tests are actively running:\n'
                    f"python tests/misc/cleanup_artifactory.py"
                )
                raise RuntimeError(error_msg)
            time.sleep(1)


@pytest.fixture(scope='package', autouse=True)
def cleanup_coverage():

    # clean up old coverage files
    path = audeer.path(
        os.path.dirname(os.path.realpath(__file__)),
        '.coverage.*',
    )
    for file in audeer.list_file_names(path):
        os.remove(file)
