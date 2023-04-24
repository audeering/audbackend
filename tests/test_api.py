import pytest

import audeer

import audbackend


@pytest.mark.parametrize(
    'name, host, repository, cls',
    [
        (
            'file-system',
            'file-system',
            f'unittest-{audeer.uid()[:8]}',
            audbackend.FileSystem,
        ),
        (
            'artifactory',
            'artifactory',
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
            'artifactory',
            'bad/repo',
            None,
            marks=pytest.mark.xfail(raises=audbackend.BackendError),
        ),
    ]
)
def test_api(hosts, name, host, repository, cls):

    if host is not None and host in hosts:
        host = hosts[name]

    error_msg = (
        "A backend class with name 'bad' does not exist."
    )

    with pytest.raises(ValueError, match=error_msg):
        audbackend.access('bad', host, repository)

    error_msg = (
        'An exception was raised by the backend, '
        'please see stack trace for further information.'
    )

    with pytest.raises(audbackend.BackendError, match=error_msg):
        audbackend.access(name, host, repository)

    backend = audbackend.create(name, host, repository)
    assert isinstance(backend, cls)

    with pytest.raises(audbackend.BackendError, match=error_msg):
        audbackend.create(name, host, repository)

    backend = audbackend.access(name, host, repository)
    assert isinstance(backend, cls)
    assert backend in audbackend.available()[name]

    audbackend.delete(name, host, repository)

    assert backend not in audbackend.available()[name]

    with pytest.raises(audbackend.BackendError, match=error_msg):
        audbackend.access(name, host, repository)
