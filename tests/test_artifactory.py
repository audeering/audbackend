import pytest

import audbackend


BACKEND = audbackend.Artifactory(
    pytest.ARTIFACTORY_HOST,
    pytest.REPOSITORY_NAME,
)


def test_exists(no_artifactory_access_rights):
    remote_file = BACKEND.join(
        pytest.ID,
        'file.txt',
    )
    version = '1.0.0'
    assert not BACKEND.exists(remote_file, version)


def test_glob(no_artifactory_access_rights):
    assert BACKEND.glob('file*') == []
