import os

import dohq_artifactory
import pytest

import audeer

import audbackend


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
    config_path = audeer.path(tmpdir, 'config.cfg')
    os.environ['ARTIFACTORY_CONFIG_FILE'] = config_path

    # config file does not exist

    backend = audbackend.Artifactory(host, 'repository')
    assert backend._username == 'anonymous'
    assert backend._api_key == ''

    # config file is empty

    audeer.touch(config_path)
    backend = audbackend.Artifactory(host, 'repository')
    assert backend._username == 'anonymous'
    assert backend._api_key == ''

    # config file entry without username and password

    with open(config_path, 'w') as fp:
        fp.write(f'[{host}]\n')

    backend = audbackend.Artifactory(host, 'repository')
    assert backend._username == 'anonymous'
    assert backend._api_key == ''

    # config file entry with username and password

    username = 'bad'
    api_key = 'bad'
    with open(config_path, 'w') as fp:
        fp.write(f'[{host}]\n')
        fp.write(f'username = {username}\n')
        fp.write(f'password = {api_key}\n')

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

    local_file = audeer.touch(audeer.path(tmpdir, 'file.txt'))
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


@pytest.mark.parametrize(
    'backend',
    ['artifactory'],
    indirect=True,
)
@pytest.mark.parametrize(
    'file, version, extensions, expected',
    [
        ('/file.tar.gz', '1.0.0', None, 'file.tar/1.0.0/file.tar-1.0.0.gz'),
        ('/file.tar.gz', '1.0.0', [], 'file.tar/1.0.0/file.tar-1.0.0.gz'),
        ('/file.tar.gz', '1.0.0', ['tar.gz'], 'file/1.0.0/file-1.0.0.tar.gz'),
        ('/.tar.gz', '1.0.0', ['tar.gz'], '.tar/1.0.0/.tar-1.0.0.gz'),
        ('/tar.gz', '1.0.0', ['tar.gz'], 'tar/1.0.0/tar-1.0.0.gz'),
        ('/.tar.gz', '1.0.0', None, '.tar/1.0.0/.tar-1.0.0.gz'),
        ('/.tar', '1.0.0', None, '.tar/1.0.0/.tar-1.0.0'),
        ('/tar', '1.0.0', None, 'tar/1.0.0/tar-1.0.0'),
    ]
)
def test_legacy_file_structure(tmpdir, backend, file, version, extensions,
                               expected):

    backend._use_legacy_file_structure(extensions=extensions)

    src_path = audeer.touch(audeer.path(tmpdir, 'tmp'))
    backend.put_file(src_path, file, version)

    url = f'{str(backend._repo.path)}{expected}'
    assert str(backend._path(file, version)) == url
    assert backend.ls(file) == [(file, version)]
    assert backend.ls() == [(file, version)]
