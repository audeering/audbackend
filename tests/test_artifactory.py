import os

import dohq_artifactory
import pytest

import audbackend
import audeer


def test_authentication():

    # read credentials from config file

    for host in [
        'https://audeering.jfrog.io/artifactory',
        'http://audeering.jfrog.io/artifactory',
        'http://audeering.jfrog.io/artifactory/',
    ]:
        backend = audbackend.Artifactory(
            host,
            'repository',
        )
        assert backend._username == 'audeering-unittest'
        assert backend._apikey != ''

    # read credentials from environment variables

    for env in ['ARTIFACTORY_USERNAME', 'ARTIFACTORY_USERNAME']:

        tmp = os.environ.get(env, False)
        os.environ[env] = 'bad'

        with pytest.raises(dohq_artifactory.exception.ArtifactoryException):
            audbackend.Artifactory(
                'https://audeering.jfrog.io/artifactory',
                'repository',
            )

        if tmp:
            os.environ[env] = tmp
        else:
            del os.environ[env]


@pytest.mark.parametrize(
    'backend',
    ['artifactory'],
    indirect=True,
)
def test_errors(tmpdir, backend):

    backend._username = 'non-existing'
    backend._apikey = 'non-existing'

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
