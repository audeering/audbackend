import pytest

import audbackend
import audeer


BACKEND = audbackend.Artifactory(
    pytest.HOSTS['artifactory'],
    pytest.REPOSITORIES['artifactory'],
)


def test_errors(tmpdir, no_artifactory_access_rights):

    local_file = audeer.touch(
        audeer.path(tmpdir, 'file.txt')
    )
    remote_file = BACKEND.join(
        audeer.uid()[:8],
        'file.txt',
    )
    version = '1.0.0'

    with pytest.raises(audbackend.BackendError):
        BACKEND.exists(remote_file, version)

    with pytest.raises(audbackend.BackendError):
        BACKEND.put_file(
            local_file,
            remote_file,
            version,
        )

    with pytest.raises(audbackend.BackendError):
        BACKEND.latest_version(remote_file)

    with pytest.raises(audbackend.BackendError):
        BACKEND.versions(remote_file)


# TODO: re-enable once we have solved
#  https://github.com/audeering/audbackend/issues/86
# def test_ls(no_artifactory_access_rights):
#     assert BACKEND.ls() == []
