import pytest

import audbackend
import audeer


@pytest.fixture(scope='function')
def backend(request):

    backend = audbackend.Artifactory(
        pytest.HOSTS['artifactory'],
        f'unittest-{audeer.uid()[:8]}',
    )

    yield backend

    # TODO: replace with audbackend.delete() when available
    backend._repo.delete()


def test_errors(tmpdir, backend, no_artifactory_access_rights):

    local_file = audeer.touch(
        audeer.path(tmpdir, 'file.txt')
    )
    remote_file = backend.join(
        audeer.uid()[:8],
        'file.txt',
    )
    version = '1.0.0'

    with pytest.raises(audbackend.BackendError):
        backend.exists(remote_file, version)

    with pytest.raises(audbackend.BackendError):
        backend.put_file(
            local_file,
            remote_file,
            version,
        )

    with pytest.raises(audbackend.BackendError):
        backend.latest_version(remote_file)

    with pytest.raises(audbackend.BackendError):
        backend.ls('/')

    with pytest.raises(audbackend.BackendError):
        backend.versions(remote_file)
