import os
import time

import pytest

import audeer

import audbackend


# list of backends that will be tested by default
pytest.BACKENDS = [
    'artifactory',
    'file-system',
]

# UID for test session
# Repositories on the host will be named
# unittest-<session-uid>-<repository-uid>
pytest.UID = audeer.uid()[:8]


@pytest.fixture(scope='package', autouse=False)
def hosts(tmpdir_factory):
    return {
        'artifactory': 'https://audeering.jfrog.io/artifactory',
        'file-system': str(tmpdir_factory.mktemp('host')),
    }


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
                    'Please delete remaining repositories manually with:\n'
                    f"'audbackend.delete({name}, {host}, {repository})'"
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
