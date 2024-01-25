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

    backend = audbackend.backend.Artifactory(host, 'repository')
    assert backend._username == 'anonymous'
    assert backend._api_key == ''

    # config file is empty

    audeer.touch(config_path)
    backend = audbackend.backend.Artifactory(host, 'repository')
    assert backend._username == 'anonymous'
    assert backend._api_key == ''

    # config file entry without username and password

    with open(config_path, 'w') as fp:
        fp.write(f'[{host}]\n')

    backend = audbackend.backend.Artifactory(host, 'repository')
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
        audbackend.backend.Artifactory(host, 'repository')


@pytest.mark.parametrize(
    'interface',
    [('artifactory', audbackend.interface.Versioned)],
    indirect=True,
)
def test_errors(tmpdir, interface):

    interface.backend._username = 'non-existing'
    interface.backend._api_key = 'non-existing'

    local_file = audeer.touch(audeer.path(tmpdir, 'file.txt'))
    remote_file = interface.join(
        '/',
        audeer.uid()[:8],
        'file.txt',
    )
    version = '1.0.0'

    # --- exists ---
    with pytest.raises(audbackend.BackendError):
        interface.exists(remote_file, version)
    assert interface.exists(
        remote_file,
        version,
        suppress_backend_errors=True,
    ) is False

    # --- put_file ---
    with pytest.raises(audbackend.BackendError):
        interface.put_file(
            local_file,
            remote_file,
            version,
        )

    # --- latest_version ---
    with pytest.raises(audbackend.BackendError):
        interface.latest_version(remote_file)

    # --- ls ---
    with pytest.raises(audbackend.BackendError):
        interface.ls('/')
    assert interface.ls(
        '/',
        suppress_backend_errors=True,
    ) == []

    # --- versions ---
    with pytest.raises(audbackend.BackendError):
        interface.versions(remote_file)
    assert interface.versions(
        remote_file,
        suppress_backend_errors=True,
    ) == []


@pytest.mark.parametrize(
    'interface',
    [('artifactory', audbackend.interface.Versioned)],
    indirect=True,
)
@pytest.mark.parametrize(
    'file, version, extensions, regex, expected',
    [
        (
            '/file.tar.gz', '1.0.0', None, False,
            'file.tar/1.0.0/file.tar-1.0.0.gz',
        ),
        (
            '/file.tar.gz', '1.0.0', [], False,
            'file.tar/1.0.0/file.tar-1.0.0.gz',
        ),
        (
            '/file.tar.gz', '1.0.0', ['tar.gz'], False,
            'file/1.0.0/file-1.0.0.tar.gz',
        ),
        (
            '/.tar.gz', '1.0.0', ['tar.gz'], False,
            '.tar/1.0.0/.tar-1.0.0.gz',
        ),
        (
            '/tar.gz', '1.0.0', ['tar.gz'], False,
            'tar/1.0.0/tar-1.0.0.gz',
        ),
        (
            '/.tar.gz', '1.0.0', None, False,
            '.tar/1.0.0/.tar-1.0.0.gz',
        ),
        (
            '/.tar', '1.0.0', None, False,
            '.tar/1.0.0/.tar-1.0.0',
        ),
        (
            '/tar', '1.0.0', None, False,
            'tar/1.0.0/tar-1.0.0',
        ),
        # test regex
        (
            '/file.0.tar.gz', '1.0.0', [r'\d+.tar.gz'], False,
            'file.0.tar/1.0.0/file.0.tar-1.0.0.gz',
        ),
        (
            '/file.0.tar.gz', '1.0.0', [r'\d+.tar.gz'], True,
            'file/1.0.0/file-1.0.0.0.tar.gz',
        ),
        (
            '/file.99.tar.gz', '1.0.0', [r'\d+.tar.gz'], True,
            'file/1.0.0/file-1.0.0.99.tar.gz',
        ),
        (
            '/file.prediction.99.tar.gz', '1.0.0',
            [r'prediction.\d+.tar.gz', r'truth.tar.gz'], True,
            'file/1.0.0/file-1.0.0.prediction.99.tar.gz',
        ),
        (
            '/file.truth.tar.gz', '1.0.0',
            [r'prediction.\d+.tar.gz', r'truth.tar.gz'], True,
            'file/1.0.0/file-1.0.0.truth.tar.gz',
        ),
        (
            '/file.99.tar.gz', '1.0.0', [r'(\d+.)?tar.gz'], True,
            'file/1.0.0/file-1.0.0.99.tar.gz',
        ),
        (
            '/file.tar.gz', '1.0.0', [r'(\d+.)?tar.gz'], True,
            'file/1.0.0/file-1.0.0.tar.gz',
        ),
    ]
)
def test_legacy_file_structure(tmpdir, interface, file, version, extensions,
                               regex, expected):

    interface._use_legacy_file_structure(extensions=extensions, regex=regex)

    src_path = audeer.touch(audeer.path(tmpdir, 'tmp'))
    interface.put_file(src_path, file, version)

    url = f'{str(interface.backend._repo.path)}{expected}'
    url_expected = interface.backend._expand(
        interface._path_with_version(file, version),
    )
    assert url_expected == url
    assert interface.ls(file) == [(file, version)]
    assert interface.ls() == [(file, version)]