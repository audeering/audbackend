import os
from unittest import mock

import pytest

import audeer

import audbackend
from audbackend.core.backend._artifactory_rest import ArtifactoryRestClient


@pytest.fixture(scope="function", autouse=False)
def hide_credentials():
    defaults = {}

    for key in [
        "ARTIFACTORY_USERNAME",
        "ARTIFACTORY_API_KEY",
        "ARTIFACTORY_CONFIG_FILE",
        "ARTIFACTORY_TIMEOUT",
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


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.Artifactory, audbackend.interface.Versioned)],
    indirect=True,
)
def test_size(tmpdir, interface):
    """Test _size method returns correct file size."""
    # Create a file with known content
    content = "Hello World!" * 1000  # ~12KB
    src_path = audeer.path(tmpdir, "test.txt")
    with open(src_path, "w") as f:
        f.write(content)
    expected_size = os.path.getsize(src_path)

    # Upload file to backend
    interface.put_file(src_path, "/test.txt", "1.0.0")

    # Get size from backend
    backend_path = interface._path_with_version("/test.txt", "1.0.0")
    actual_size = interface.backend._size(backend_path)

    assert actual_size == expected_size


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.Artifactory, audbackend.interface.Unversioned)],
    indirect=True,
)
def test_copy_move_into_missing_subdir(tmpdir, interface):
    """Test that copy_file and move_file create missing parent directories.

    JFrog ``/api/copy`` and ``/api/move`` endpoints
    auto-create intermediate folders.
    This test locks in that behavior
    so a regression on the server side
    or a change to the request shape
    would be caught.

    """
    src_path = audeer.touch(audeer.path(tmpdir, "file.txt"))
    interface.put_file(src_path, "/file.txt")

    # copy into a not-yet-existing subdirectory
    copy_dst = "/new-copy-dir/sub/copied.txt"
    assert not interface.exists(copy_dst)
    interface.copy_file("/file.txt", copy_dst)
    assert interface.exists("/file.txt")
    assert interface.exists(copy_dst)

    # move into a different not-yet-existing subdirectory
    move_dst = "/new-move-dir/sub/moved.txt"
    assert not interface.exists(move_dst)
    interface.move_file("/file.txt", move_dst)
    assert not interface.exists("/file.txt")
    assert interface.exists(move_dst)


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.Artifactory, audbackend.interface.Unversioned)],
    indirect=True,
)
def test_get_archive_streaming(tmpdir, interface):
    """Test get_archive with streaming extraction verifies _get_file_stream.

    This test verifies that _get_file_stream() returns bytes correctly,
    which is required for streaming ZIP extraction and checksum computation.

    """
    # Create source files
    src_root = audeer.path(tmpdir, "src")
    audeer.mkdir(src_root)
    with open(audeer.path(src_root, "file1.txt"), "w") as f:
        f.write("content of file 1")
    with open(audeer.path(src_root, "file2.txt"), "w") as f:
        f.write("content of file 2")

    # Create ZIP archive
    archive_path = audeer.path(tmpdir, "archive.zip")
    audeer.create_archive(src_root, None, archive_path)

    # Upload archive to backend
    interface.put_file(archive_path, "/archive.zip")

    # Extract using streaming (this exercises _get_file_stream)
    dst_root = audeer.path(tmpdir, "dst")
    extracted = interface.get_archive("/archive.zip", dst_root)

    # Verify files were extracted correctly
    assert sorted(extracted) == ["file1.txt", "file2.txt"]
    with open(audeer.path(dst_root, "file1.txt")) as f:
        assert f.read() == "content of file 1"
    with open(audeer.path(dst_root, "file2.txt")) as f:
        assert f.read() == "content of file 2"

    # Also test with validation to verify checksum computation works
    # (requires _get_file_stream to return bytes for md5.update())
    dst_root_validated = audeer.path(tmpdir, "dst_validated")
    extracted_validated = interface.get_archive(
        "/archive.zip", dst_root_validated, validate=True
    )
    assert sorted(extracted_validated) == ["file1.txt", "file2.txt"]


def test_default_timeout(hide_credentials):
    """Default HTTP timeout is 60 seconds."""
    backend = audbackend.backend.Artifactory("https://example.com", "repository")
    assert backend.timeout == 60.0


def test_constructor_timeout(hide_credentials):
    """Constructor argument overrides the default."""
    backend = audbackend.backend.Artifactory(
        "https://example.com", "repository", timeout=30.0
    )
    assert backend.timeout == 30.0


def test_constructor_timeout_disables(hide_credentials):
    """``timeout=None`` disables the HTTP timeout, even if the env var is set."""
    os.environ["ARTIFACTORY_TIMEOUT"] = "30"
    backend = audbackend.backend.Artifactory(
        "https://example.com", "repository", timeout=None
    )
    assert backend.timeout is None


def test_env_timeout(hide_credentials):
    """``ARTIFACTORY_TIMEOUT`` env var sets the timeout."""
    os.environ["ARTIFACTORY_TIMEOUT"] = "45"
    backend = audbackend.backend.Artifactory("https://example.com", "repository")
    assert backend.timeout == 45.0


def test_env_timeout_none(hide_credentials):
    """``ARTIFACTORY_TIMEOUT=none`` disables the timeout."""
    os.environ["ARTIFACTORY_TIMEOUT"] = "None"
    backend = audbackend.backend.Artifactory("https://example.com", "repository")
    assert backend.timeout is None


def test_env_timeout_invalid(hide_credentials):
    """Invalid ``ARTIFACTORY_TIMEOUT`` falls back to the default."""
    os.environ["ARTIFACTORY_TIMEOUT"] = "not-a-number"
    backend = audbackend.backend.Artifactory("https://example.com", "repository")
    assert backend.timeout == 60.0


@pytest.mark.parametrize(
    "method, args",
    [
        ("stat", ("/path",)),
        ("exists", ("/path",)),
        ("delete", ("/path",)),
        ("copy", ("/src", "/dst")),
        ("move", ("/src", "/dst")),
        ("list_files", ("/sub",)),
        ("repository_exists", ()),
        ("create_repository", ()),
        ("delete_repository", ()),
    ],
)
def test_rest_client_timeout_propagated(method, args):
    """Every REST call forwards ``timeout`` to the underlying session."""
    session = mock.MagicMock()
    response = mock.MagicMock()
    response.status_code = 200
    response.json.return_value = {"size": 0, "checksums": {}, "files": []}
    session.get.return_value = response
    session.head.return_value = response
    session.put.return_value = response
    session.post.return_value = response
    session.delete.return_value = response

    client = ArtifactoryRestClient("https://example.com", "repo", session, timeout=42.0)
    getattr(client, method)(*args)

    # Exactly one of the verbs is invoked per method; check that one.
    invoked = [
        verb
        for verb in (
            session.get,
            session.head,
            session.put,
            session.post,
            session.delete,
        )
        if verb.called
    ]
    assert len(invoked) == 1
    assert invoked[0].call_args.kwargs["timeout"] == 42.0


def test_rest_client_timeout_propagated_streaming():
    """Streaming reads forward ``timeout`` to the session."""
    session = mock.MagicMock()
    response = mock.MagicMock()
    response.status_code = 200
    response.iter_content.return_value = iter([])
    session.get.return_value.__enter__.return_value = response

    client = ArtifactoryRestClient("https://example.com", "repo", session, timeout=42.0)
    list(client.stream("/path"))

    assert session.get.call_args.kwargs["timeout"] == 42.0


def test_rest_client_timeout_propagated_download(tmpdir):
    """``download`` forwards ``timeout`` to the session."""
    session = mock.MagicMock()
    response = mock.MagicMock()
    response.status_code = 200
    response.iter_content.return_value = iter([b"data"])
    session.get.return_value.__enter__.return_value = response

    client = ArtifactoryRestClient("https://example.com", "repo", session, timeout=42.0)
    dst = audeer.path(tmpdir, "out.bin")
    client.download("/path", dst)

    assert session.get.call_args.kwargs["timeout"] == 42.0


def test_rest_client_timeout_propagated_upload(tmpdir):
    """``upload`` forwards ``timeout`` to the session."""
    session = mock.MagicMock()
    response = mock.MagicMock()
    response.status_code = 200
    session.put.return_value = response

    src = audeer.touch(audeer.path(tmpdir, "src.bin"))
    client = ArtifactoryRestClient("https://example.com", "repo", session, timeout=42.0)
    client.upload(src, "/path")

    assert session.put.call_args.kwargs["timeout"] == 42.0


@pytest.mark.parametrize("method", ["stat", "delete"])
def test_rest_client_404_raises_file_not_found(method):
    """``stat`` and ``delete`` map a 404 to :class:`FileNotFoundError`."""
    session = mock.MagicMock()
    response = mock.MagicMock()
    response.status_code = 404
    session.get.return_value = response
    session.delete.return_value = response

    client = ArtifactoryRestClient("https://example.com", "repo", session)
    with pytest.raises(FileNotFoundError, match="/missing"):
        getattr(client, method)("/missing")


def test_rest_client_404_raises_file_not_found_download(tmpdir):
    """``download`` maps a 404 to :class:`FileNotFoundError`."""
    session = mock.MagicMock()
    response = mock.MagicMock()
    response.status_code = 404
    session.get.return_value.__enter__.return_value = response

    client = ArtifactoryRestClient("https://example.com", "repo", session)
    dst = audeer.path(tmpdir, "out.bin")
    with pytest.raises(FileNotFoundError, match="/missing"):
        client.download("/missing", dst)


def test_rest_client_404_raises_file_not_found_stream():
    """``stream`` maps a 404 to :class:`FileNotFoundError`."""
    session = mock.MagicMock()
    response = mock.MagicMock()
    response.status_code = 404
    session.get.return_value.__enter__.return_value = response

    client = ArtifactoryRestClient("https://example.com", "repo", session)
    with pytest.raises(FileNotFoundError, match="/missing"):
        list(client.stream("/missing"))


@pytest.mark.parametrize("action", ["copy", "move"])
def test_rest_client_404_raises_file_not_found_copy_move(action):
    """``copy`` and ``move`` map a 404 to :class:`FileNotFoundError` for the source."""
    session = mock.MagicMock()
    response = mock.MagicMock()
    response.status_code = 404
    session.post.return_value = response

    client = ArtifactoryRestClient("https://example.com", "repo", session)
    with pytest.raises(FileNotFoundError, match="/missing-src"):
        getattr(client, action)("/missing-src", "/dst")
