import os

import pytest

import audeer

import audbackend


@pytest.fixture(scope="function", autouse=False)
def hide_credentials():
    defaults = {}

    for key in [
        "ARTIFACTORY_USERNAME",
        "ARTIFACTORY_API_KEY",
        "ARTIFACTORY_CONFIG_FILE",
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
    host = hosts["artifactory"]
    config_path = audeer.path(tmpdir, "config.cfg")
    os.environ["ARTIFACTORY_CONFIG_FILE"] = config_path

    # config file does not exist

    backend = audbackend.backend.Artifactory(host, "repository")
    assert backend.authentication == ("anonymous", "")

    # config file is empty

    audeer.touch(config_path)
    backend = audbackend.backend.Artifactory(host, "repository")
    assert backend.authentication == ("anonymous", "")

    # config file entry without username and password

    with open(config_path, "w") as fp:
        fp.write(f"[{host}]\n")

    backend = audbackend.backend.Artifactory(host, "repository")
    assert backend.authentication == ("anonymous", "")

    # config file entry with username and password

    username = "bad"
    api_key = "bad"
    with open(config_path, "w") as fp:
        fp.write(f"[{host}]\n")
        fp.write(f"username = {username}\n")
        fp.write(f"password = {api_key}\n")

    backend = audbackend.backend.Artifactory(host, "repository")
    assert backend.authentication == ("bad", "bad")
    with pytest.raises(audbackend.BackendError):
        backend.open()


@pytest.mark.parametrize("host", [pytest.HOSTS["artifactory"]])
@pytest.mark.parametrize("repository", [f"unittest-{pytest.UID}-{audeer.uid()[:8]}"])
def test_create_delete_repositories(host, repository):
    audbackend.backend.Artifactory.create(host, repository)
    with pytest.raises(audbackend.BackendError):
        # Repository exists already
        audbackend.backend.Artifactory.create(host, repository)
    audbackend.backend.Artifactory.delete(host, repository)


@pytest.mark.parametrize("host", [pytest.HOSTS["artifactory"]])
@pytest.mark.parametrize("repository", [f"unittest-{pytest.UID}-{audeer.uid()[:8]}"])
@pytest.mark.parametrize("authentication", [("non-existing", "non-existing")])
def test_errors(host, repository, authentication):
    backend = audbackend.backend.Artifactory(
        host, repository, authentication=authentication
    )
    with pytest.raises(audbackend.BackendError):
        backend.open()


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.Artifactory, audbackend.interface.Maven)],
    indirect=True,
)
@pytest.mark.parametrize(
    "file, version, extensions, regex, expected",
    [
        (
            "/file.tar.gz",
            "1.0.0",
            [],
            False,
            "/file.tar/1.0.0/file.tar-1.0.0.gz",
        ),
        (
            "/file.tar.gz",
            "1.0.0",
            ["tar.gz"],
            False,
            "/file/1.0.0/file-1.0.0.tar.gz",
        ),
        (
            "/.tar.gz",
            "1.0.0",
            ["tar.gz"],
            False,
            "/.tar/1.0.0/.tar-1.0.0.gz",
        ),
        (
            "/tar.gz",
            "1.0.0",
            ["tar.gz"],
            False,
            "/tar/1.0.0/tar-1.0.0.gz",
        ),
        (
            "/.tar.gz",
            "1.0.0",
            [],
            False,
            "/.tar/1.0.0/.tar-1.0.0.gz",
        ),
        (
            "/.tar",
            "1.0.0",
            [],
            False,
            "/.tar/1.0.0/.tar-1.0.0",
        ),
        (
            "/tar",
            "1.0.0",
            [],
            False,
            "/tar/1.0.0/tar-1.0.0",
        ),
        # test regex
        (
            "/file.0.tar.gz",
            "1.0.0",
            [r"\d+.tar.gz"],
            False,
            "/file.0.tar/1.0.0/file.0.tar-1.0.0.gz",
        ),
        (
            "/file.0.tar.gz",
            "1.0.0",
            [r"\d+.tar.gz"],
            True,
            "/file/1.0.0/file-1.0.0.0.tar.gz",
        ),
        (
            "/file.99.tar.gz",
            "1.0.0",
            [r"\d+.tar.gz"],
            True,
            "/file/1.0.0/file-1.0.0.99.tar.gz",
        ),
        (
            "/file.prediction.99.tar.gz",
            "1.0.0",
            [r"prediction.\d+.tar.gz", r"truth.tar.gz"],
            True,
            "/file/1.0.0/file-1.0.0.prediction.99.tar.gz",
        ),
        (
            "/file.truth.tar.gz",
            "1.0.0",
            [r"prediction.\d+.tar.gz", r"truth.tar.gz"],
            True,
            "/file/1.0.0/file-1.0.0.truth.tar.gz",
        ),
        (
            "/file.99.tar.gz",
            "1.0.0",
            [r"(\d+.)?tar.gz"],
            True,
            "/file/1.0.0/file-1.0.0.99.tar.gz",
        ),
        (
            "/file.tar.gz",
            "1.0.0",
            [r"(\d+.)?tar.gz"],
            True,
            "/file/1.0.0/file-1.0.0.tar.gz",
        ),
    ],
)
def test_maven_file_structure(
    tmpdir, interface, file, version, extensions, regex, expected
):
    interface.extensions = extensions
    interface.regex = regex

    src_path = audeer.touch(audeer.path(tmpdir, "tmp"))
    interface.put_file(src_path, file, version)

    url = str(interface.backend.path(expected))
    url_expected = str(
        interface.backend.path(interface._path_with_version(file, version))
    )
    assert url_expected == url
    assert interface.ls(file) == [(file, version)]
    assert interface.ls() == [(file, version)]


@pytest.mark.parametrize("host", [pytest.HOSTS["artifactory"]])
@pytest.mark.parametrize("repository", [f"unittest-{pytest.UID}-{audeer.uid()[:8]}"])
def test_open_close(host, repository):
    backend = audbackend.backend.Artifactory(host, repository)
    with pytest.raises(audbackend.BackendError):
        # Repository does not exist yet
        backend.open()
    audbackend.backend.Artifactory.create(host, repository)
    backend.open()
    backend.close()


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.Artifactory, audbackend.interface.Maven)],
    indirect=True,
)
def test_parquet_file(interface, parquet_file):
    """Test uploading a parquet file with hash in metadata.

    We need to make sure to hand the MD5 sum
    to the deploy method of Artifactory,
    not the checksum hash of the parquet file metadata.
    See https://github.com/audeering/audbackend/issues/254.

    """
    dst_file = f"/{os.path.basename(parquet_file)}"
    version = "1.0.0"
    interface.put_file(parquet_file, dst_file, version)
    assert interface.exists(dst_file, version)
