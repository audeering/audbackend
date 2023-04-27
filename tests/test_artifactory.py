import os

import dohq_artifactory
import pytest

import audbackend
import audeer


@pytest.fixture(scope='function', autouse=False)
def hide_credentials():

    defaults = {}

    for key in [
        'ARTIFACTORY_USERNAME',
        'ARTIFACTORY_API_KEY',
        'ARTIFACTORY_CONFIG_FILE',
    ]:
        defaults[key] = os.environ.get(key, None)

    for key, value in defaults.items():
        if value is not None:
            del os.environ[key]

    yield

    for key, value in defaults.items():
        if value is not None:
            os.environ[key] = value
        elif key in os.environ:
            del os.environ[key]


def test_authentication(tmpdir, hosts, hide_credentials):

    host = hosts['artifactory']

    # create empty config file

    config_path = audeer.path(tmpdir, 'config.cfg')
    os.environ['ARTIFACTORY_CONFIG_FILE'] = audeer.touch(config_path)

    # default credentials

    backend = audbackend.Artifactory(host, 'repository')
    assert backend._username == 'anonymous'
    assert backend._api_key == ''

    # read from config file

    username = 'bad'
    api_key = 'bad'
    with open(config_path, 'w') as fp:
        fp.write(f'[{host}]\n')
        fp.write(f'username = {username}]\n')
        fp.write(f'password = {api_key}]\n')

    with pytest.raises(dohq_artifactory.exception.ArtifactoryException):
        audbackend.Artifactory(host, 'repository')


@pytest.mark.parametrize(
    'backend',
    ['artifactory'],
    indirect=True,
)
def test_errors(tmpdir, backend):

    backend._username = 'non-existing'
    backend._api_key = 'non-existing'

    local_file = audeer.touch(
        audeer.path(tmpdir, 'file.txt')
    )
    remote_file = backend.join(
        '/',
        audeer.uid()[:8],
        'file.txt',
    )
    version = '1.0.0'

    # --- exists ---
    with pytest.raises(audbackend.BackendError):
        backend.exists(remote_file, version)
    assert backend.exists(
        remote_file,
        version,
        suppress_backend_errors=True,
    ) is False

    # --- put_file ---
    with pytest.raises(audbackend.BackendError):
        backend.put_file(
            local_file,
            remote_file,
            version,
        )

    # --- latest_version ---
    with pytest.raises(audbackend.BackendError):
        backend.latest_version(remote_file)

    # --- ls ---
    with pytest.raises(audbackend.BackendError):
        backend.ls('/')
    assert backend.ls(
        '/',
        suppress_backend_errors=True,
    ) == []

    # --- versions ---
    with pytest.raises(audbackend.BackendError):
        backend.versions(remote_file)
    assert backend.versions(
        remote_file,
        suppress_backend_errors=True,
    ) == []
