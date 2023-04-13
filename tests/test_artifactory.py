import pytest

import audbackend
import audeer


BACKEND = audbackend.Artifactory(
    pytest.HOSTS['artifactory'],
    pytest.REPOSITORIES['artifactory'],
)


def test_exists(no_artifactory_access_rights):
    remote_file = BACKEND.join(
        audeer.uid()[:8],
        'file.txt',
    )
    version = '1.0.0'
    assert not BACKEND.exists(remote_file, version)


def test_ls(no_artifactory_access_rights):
    assert BACKEND.ls() == []
