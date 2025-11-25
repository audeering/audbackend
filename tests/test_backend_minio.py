import os

import pytest

import audeer

import audbackend


@pytest.fixture(scope="function", autouse=False)
def hide_credentials():
    defaults = {
        key: os.environ.get(key, None)
        for key in [
            "MINIO_ACCESS_KEY",
            "MINIO_SECRET_KEY",
            "MINIO_CONFIG_FILE",
        ]
    }
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
    host = hosts["minio"]
    config_path = audeer.path(tmpdir, "config.cfg")
    os.environ["MINIO_CONFIG_FILE"] = config_path

    # config file does not exist

    backend = audbackend.backend.Minio(host, "repository")
    assert backend.authentication == (None, None)

    # config file is empty

    audeer.touch(config_path)
    backend = audbackend.backend.Minio(host, "repository")
    assert backend.authentication == (None, None)

    # config file entry without username and password

    with open(config_path, "w") as fp:
        fp.write(f"[{host}]\n")

    backend = audbackend.backend.Minio(host, "repository")
    assert backend.authentication == (None, None)

    # config file entry with username and password

    access_key = "bad"
    secret_key = "bad"
    with open(config_path, "w") as fp:
        fp.write(f"[{host}]\n")
        fp.write(f"access_key = {access_key}\n")
        fp.write(f"secret_key = {secret_key}\n")

    backend = audbackend.backend.Minio(host, "repository")
    assert backend.authentication == ("bad", "bad")
    with pytest.raises(audbackend.BackendError):
        backend.open()


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.Minio, audbackend.interface.Unversioned)],
    indirect=True,
)
@pytest.mark.parametrize(
    "path, expected,",
    [
        ("/text.txt", "text/plain"),
    ],
)
def test_content_type(tmpdir, interface, path, expected):
    r"""Test setting of content type.

    Args:
        tmpdir: tmpdir fixture
        interface: interface fixture
        path: path of file on backend
        expected: expected content type

    """
    tmp_path = audeer.touch(audeer.path(tmpdir, path[1:]))
    interface.put_file(tmp_path, path)
    stats = interface._backend._client.stat_object(
        bucket_name=interface.repository,
        object_name=path,
    )
    assert stats.content_type == expected


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.Minio, audbackend.interface.Unversioned)],
    indirect=True,
)
@pytest.mark.parametrize(
    "src_path, dst_path,",
    [
        (
            "/big.1.txt",
            "/big.2.txt",
        ),
    ],
)
def test_copy_large_file(tmpdir, interface, src_path, dst_path):
    r"""Test copying of large files.

    ``minio.Minio.copy_object()`` has a limit of 5 GB.
    We mock the ``audbackend.backend.Minio._size()`` method
    to return a value equivalent to 5 GB.
    to trigger the fall back copy mechanism for large files,
    without having to create a large file.

    Args:
        tmpdir: tmpdir fixture
        interface: interface fixture
        src_path: source path of file on backend
        dst_path: destination of copy operation on backend

    """
    tmp_path = audeer.touch(audeer.path(tmpdir, "big.1.txt"))
    interface.put_file(tmp_path, src_path)
    interface._backend._size = lambda x: 5 * 1024 * 1024 * 1024
    interface.copy_file(src_path, dst_path)
    assert interface.exists(src_path)
    assert interface.exists(dst_path)


@pytest.mark.parametrize("host", [pytest.HOSTS["minio"]])
@pytest.mark.parametrize("repository", [f"unittest-{pytest.UID}-{audeer.uid()[:8]}"])
def test_create_delete_repositories(host, repository):
    audbackend.backend.Minio.create(host, repository)
    with pytest.raises(audbackend.BackendError):
        # Repository exists already
        audbackend.backend.Minio.create(host, repository)
    audbackend.backend.Minio.delete(host, repository)


@pytest.mark.parametrize("host", [pytest.HOSTS["minio"]])
@pytest.mark.parametrize("repository", [f"unittest-{pytest.UID}-{audeer.uid()[:8]}"])
@pytest.mark.parametrize("authentication", [("bad-access", "bad-secret")])
def test_errors(host, repository, authentication):
    backend = audbackend.backend.Minio(host, repository, authentication=authentication)
    with pytest.raises(audbackend.BackendError):
        backend.open()


def test_get_config(tmpdir, hosts, hide_credentials):
    r"""Test parsing of configuration.

    The `get_config()` class method is responsible
    for parsing a Minio backend config file.

    Args:
        tmpdir: tmpdir fixture
        hosts: hosts fixture
        hide_credentials: hide_credentials fixture

    """
    host = hosts["minio"]
    config_path = audeer.path(tmpdir, "config.cfg")
    os.environ["MINIO_CONFIG_FILE"] = config_path

    # config file does not exist
    config = audbackend.backend.Minio.get_config(host)
    assert config == {}

    # config file is empty
    audeer.touch(config_path)
    config = audbackend.backend.Minio.get_config(host)
    assert config == {}

    # config file has different host
    with open(config_path, "w") as fp:
        fp.write(f"[{host}.abc]\n")
    config = audbackend.backend.Minio.get_config(host)
    assert config == {}

    # config file entry without variables
    with open(config_path, "w") as fp:
        fp.write(f"[{host}]\n")
    config = audbackend.backend.Minio.get_config(host)
    assert config == {}

    # config file entry with variables
    access_key = "user"
    secret_key = "pass"
    secure = True
    with open(config_path, "w") as fp:
        fp.write(f"[{host}]\n")
        fp.write(f"access_key = {access_key}\n")
        fp.write(f"secret_key = {secret_key}\n")
        fp.write(f"secure = {secure}\n")
    config = audbackend.backend.Minio.get_config(host)
    assert config["access_key"] == access_key
    assert config["secret_key"] == secret_key
    assert config["secure"]


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.Minio, audbackend.interface.Maven)],
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
    """Test using the Maven interface with a Minio backend.

    Args:
        tmpdir: tmpdir fixture
        interface: interface fixture,
            which needs to be called with the Minio backend
            and the Maven interface
        file: file name
        version: file version
        extensions: extensions considered by the Maven interface
        regex: if ``True``,
            ``extensions`` are considered as a regex
        expected: expected file structure on backend

    """
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


@pytest.mark.parametrize("host", [pytest.HOSTS["minio"]])
@pytest.mark.parametrize("repository", [f"unittest-{pytest.UID}-{audeer.uid()[:8]}"])
def test_open_close(host, repository):
    backend = audbackend.backend.Minio(host, repository)
    with pytest.raises(audbackend.BackendError):
        # Repository does not exist yet
        backend.open()
    audbackend.backend.Minio.create(host, repository)
    backend.open()
    backend.close()
