import sys

import pytest

import audeer

import audbackend


@pytest.mark.parametrize(
    "name, host, repository, expected_class",
    [
        (
            "file-system",
            "file-system",
            f"unittest-{audeer.uid()[:8]}",
            "audbackend.backend.FileSystem",
        ),
        pytest.param(
            "artifactory",
            "artifactory",
            f"unittest-{audeer.uid()[:8]}",
            "audbackend.backend.Artifactory",
            marks=pytest.mark.skipif(
                sys.version_info >= (3, 12),
                reason="Requires Python<3.12",
            ),
        ),
        (
            "minio",
            "minio",
            f"unittest-{audeer.uid()[:8]}",
            "audbackend.backend.Minio",
        ),
        pytest.param(  # backend does not exist
            "bad-backend",
            None,
            None,
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(  # host does not exist
            "minio",
            "bad-host",
            "repo",
            None,
            marks=pytest.mark.xfail(raises=audbackend.BackendError),
        ),
        pytest.param(  # invalid repository name
            "minio",
            "minio",
            "bad/repo",
            None,
            marks=pytest.mark.xfail(raises=audbackend.BackendError),
        ),
    ],
)
def test_api(hosts, name, host, repository, expected_class):
    if host is not None and host in hosts:
        host = hosts[name]

    create_warning = (
        "create is deprecated and will be removed with version 2.2.0. "
        r"Use class method Backend.create\(\) of corresponding backend instead."
    )
    error_msg = (
        "An exception was raised by the backend, "
        "please see stack trace for further information."
    )

    # returns versioned interface for legacy reasons
    with pytest.warns(UserWarning, match=create_warning):
        interface = audbackend.create(name, host, repository)
    assert isinstance(interface, audbackend.interface.Versioned)
    assert str(interface.backend).startswith(expected_class)

    with pytest.raises(audbackend.BackendError, match=error_msg):
        with pytest.warns(UserWarning, match=create_warning):
            audbackend.create(name, host, repository)
