import pytest

import audeer

import audbackend


@pytest.mark.parametrize(
    'name, host, repository, cls',
    [
        (
            'file-system',
            pytest.HOSTS['file-system'],
            f'unittest-{audeer.uid()[:8]}',
            audbackend.FileSystem,
        ),
        (
            'artifactory',
            pytest.HOSTS['artifactory'],
            f'unittest-{audeer.uid()[:8]}',
            audbackend.Artifactory,
        ),
        pytest.param(  # backend does not exist
            'bad-backend',
            None,
            None,
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(  # host does not exist
            'artifactory',
            'bad-host',
            'repo',
            None,
            marks=pytest.mark.xfail(raises=audbackend.BackendError),
        ),
        pytest.param(  # invalid repository name
            'artifactory',
            pytest.HOSTS['artifactory'],
            'bad/repo',
            None,
            marks=pytest.mark.xfail(raises=audbackend.BackendError),
        ),
    ]
)
def test_api(name, host, repository, cls):

    backend = audbackend.create(name, host, repository)

    assert isinstance(backend, cls)
    assert backend in audbackend.available()[name]

    audbackend.delete(name, host, repository)

    assert backend not in audbackend.available()[name]