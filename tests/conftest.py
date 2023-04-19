import os

import pytest

import audeer


pytest.ROOT = os.path.dirname(os.path.realpath(__file__))

pytest.HOSTS = {
    'artifactory': 'https://audeering.jfrog.io/artifactory',
    'file-system': os.path.join(pytest.ROOT, 'host'),
}

# list of backends that will be tested
pytest.BACKENDS = [
    # 'artifactory',
    'file-system',
]


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
