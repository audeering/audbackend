import os
import time

import pytest

import audeer

import audbackend


pytest.ROOT = os.path.dirname(os.path.realpath(__file__))

pytest.HOSTS = {
    'artifactory': 'https://audeering.jfrog.io/artifactory',
    'file-system': os.path.join(pytest.ROOT, 'host'),
}

# list of backends that will be tested by default
pytest.BACKENDS = [
    'artifactory',
    'file-system',
]

# UID for test session
# Repositories on the host will be named
# unittest-<session-uid>-<repository-uid>
pytest.UID = audeer.uid()[:8]


@pytest.fixture(scope='function', autouse=False)
def backend(request):
    r"""Create and delete a repository on the backend."""
    name = request.param
    host = pytest.HOSTS[name]
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
def cleanup_session():

    # clean up old coverage files
    path = audeer.path(
        pytest.ROOT,
        '.coverage.*',
    )
    for file in audeer.list_file_names(path):
        os.remove(file)

    yield

    if os.path.exists(pytest.HOSTS['file-system']):
        os.rmdir(pytest.HOSTS['file-system'])


@pytest.fixture(scope='function', autouse=False)
def no_artifactory_access_rights():
    current_username = os.environ.get('ARTIFACTORY_USERNAME', False)
    current_api_key = os.environ.get('ARTIFACTORY_API_KEY', False)
    os.environ['ARTIFACTORY_USERNAME'] = 'non-existing-user'
    os.environ['ARTIFACTORY_API_KEY'] = 'non-existing-password'
    yield
    if current_username:
        os.environ["ARTIFACTORY_USERNAME"] = current_username
    else:
        del os.environ['ARTIFACTORY_USERNAME']
    if current_api_key:
        os.environ['ARTIFACTORY_API_KEY'] = current_api_key
    else:
        del os.environ['ARTIFACTORY_API_KEY']
