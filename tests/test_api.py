import pytest

import audeer

import audbackend


@pytest.mark.parametrize(
    "name, host, repository, cls",
    [
        (
            "file-system",
            "file-system",
            f"unittest-{audeer.uid()[:8]}",
            audbackend.backend.FileSystem,
        ),
        (
            "artifactory",
            "artifactory",
            f"unittest-{audeer.uid()[:8]}",
            audbackend.backend.Artifactory,
        ),
        pytest.param(  # backend does not exist
            "bad-backend",
            None,
            None,
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(  # host does not exist
            "artifactory",
            "bad-host",
            "repo",
            None,
            marks=pytest.mark.xfail(raises=audbackend.BackendError),
        ),
        pytest.param(  # invalid repository name
            "artifactory",
            "artifactory",
            "bad/repo",
            None,
            marks=pytest.mark.xfail(raises=audbackend.BackendError),
        ),
    ],
)
def test_api(hosts, name, host, repository, cls):
    if host is not None and host in hosts:
        host = hosts[name]

    access_warning = (
        "access is deprecated and will be removed with version 2.2.0. "
        r"Use Backend.__init__\(\) of corresponding backend instead."
    )
    create_warning = (
        "create is deprecated and will be removed with version 2.2.0. "
        r"Use class method Backend.create\(\) of corresponding backend instead."
    )
    delete_warning = (
        "delete is deprecated and will be removed with version 2.2.0. "
        r"Use class method Backend.delete\(\) of corresponding backend instead."
    )

    error_msg = "A backend class with name 'bad' does not exist."
    with pytest.raises(ValueError, match=error_msg):
        with pytest.warns(UserWarning, match=access_warning):
            audbackend.access("bad", host, repository)

    error_msg = (
        "An exception was raised by the backend, "
        "please see stack trace for further information."
    )

    with pytest.raises(audbackend.BackendError, match=error_msg):
        with pytest.warns(UserWarning, match=access_warning):
            audbackend.access(name, host, repository)

    # returns versioned interface for legacy reasons
    with pytest.warns(UserWarning, match=create_warning):
        interface = audbackend.create(name, host, repository)
    assert isinstance(interface, audbackend.interface.Versioned)
    assert isinstance(interface.backend, cls)

    with pytest.raises(audbackend.BackendError, match=error_msg):
        with pytest.warns(UserWarning, match=create_warning):
            audbackend.create(name, host, repository)

    with pytest.warns(UserWarning, match=access_warning):
        interface = audbackend.access(name, host, repository)
    assert isinstance(interface.backend, cls)

    with pytest.warns(UserWarning, match=delete_warning):
        audbackend.delete(name, host, repository)

    with pytest.raises(audbackend.BackendError, match=error_msg):
        with pytest.warns(UserWarning, match=access_warning):
            audbackend.access(name, host, repository)
