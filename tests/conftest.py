import getpass
import os
import time

import pytest
from singlefolder import SingleFolder

import audeer

import audbackend


# list of backends that will be tested by default
pytest.BACKENDS = [
    'artifactory',
    'file-system',
]
if os.name != 'nt':
    pytest.BACKENDS.append('single-folder')

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
        owner = 'audeering-unittest'
    else:
        if os.name == 'nt':
            owner = 'Administrators'
        else:
            owner = getpass.getuser()

    yield owner


@pytest.fixture(scope='function', autouse=False)
def backend(hosts, request):

    name = request.param
    host = hosts[name]
    repository = f'unittest-{pytest.UID}-{audeer.uid()[:8]}'

    backend = audbackend.create(name, host, repository)

    yield backend

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
