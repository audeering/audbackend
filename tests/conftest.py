import os

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


@pytest.fixture(scope='function', autouse=False)
def backend(request):
    r"""Create and delete a repository on the backend.

    Deleting a repository might fail on Artifactory hosts,
    hence we catch the error
    and instead look for leftover repositories
    at the beginning and clean try to clean them.

    """
    name = request.param
    host = pytest.HOSTS[name]
    repository = f'unittest-{audeer.uid()[:8]}'

    # Clean up possible left over repos on Artifactory host
    if name == 'artifactory':
        r = audfactory.rest_api_get(f'{host}/api/repositories')
        if r.status_code == 200:
            repos = [entry['key'] for entry in r.json()]
            repos = [
                repo for repo in repos
                if repo != 'unittests-public' and repo.startswith('unittest-')
            ]
            for repo in repos:
                try:
                    audbackend.delete(name, host, repo)
                except audbackend.BackendError:
                    pass

    backend = audbackend.create(name, host, repository)

    yield backend

    # Deleting repositories on Artifactory might fail
    try:
        audbackend.delete(name, host, repository)
    except audbackend.BackendError:
        pass


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
