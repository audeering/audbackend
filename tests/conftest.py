import os
import time

import pytest

import audeer
import audfactory

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


@pytest.fixture(scope='session', autouse=True)
def cleanup_artifactory():
    r"""Remove letover unit test repositories on Artifactory.

    As removing a unit test repsoitory
    in the ``backend()`` fixture
    might fail
    (https://github.com/audeering/audbackend/issues/97),
    we try to clean up the host
    everytime we run the tests.
    If this fails
    a ``RuntimeError`` is raised
    and the user then needs to clean up
    the repository manually.

    """

    yield

    # Delete leftover repositories
    name = 'artifactory'
    host = pytest.HOSTS[name]
    r = audfactory.rest_api_get(f'{host}/api/repositories')
    if r.status_code == 200:
        repos = [entry['key'] for entry in r.json()]
        repos = [
            repo for repo in repos
            if repo.startswith(f'unittest-{pytest.UID}')
        ]
        for repo in repos:
            try:
                audbackend.delete(name, host, repo)
            except audbackend.BackendError as ex:
                raise RuntimeError(
                    f'Cleaning up of repo {repo} failed. '
                    f'Please try to clean up manually with: '
                    f"'audbackend.delete({name}, {host}, {repo})' ."
                    f'The original error message was {ex}.'
                )


@pytest.fixture(scope='function', autouse=False)
def backend(request):
    r"""Create and delete a repository on the backend."""
    name = request.param
    host = pytest.HOSTS[name]
    repository = f'unittest-{pytest.UID}-{audeer.uid()[:8]}'

    backend = audbackend.create(name, host, repository)

    yield backend

    # Deleting repositories on Artifactory might fail
    for _ in range(3):
        try:
            audbackend.delete(name, host, repository)
            break
        except audbackend.BackendError:
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
