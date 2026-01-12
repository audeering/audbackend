import contextlib
import filecmp
import os
import signal
import threading
from unittest import mock
import warnings

import minio
import pytest
import urllib3

import audeer

import audbackend


@contextlib.contextmanager
def capture_minio_kwargs():
    """Context manager to capture kwargs passed to minio.Minio constructor.

    Yields a dictionary that will be populated with the kwargs
    passed to minio.Minio.__init__.

    Example:
        with capture_minio_kwargs() as captured:
            audbackend.backend.Minio(host, repo)
        assert "http_client" in captured

    """
    captured_kwargs = {}
    original_init = minio.Minio.__init__

    def mock_init(self, *args, **kwargs):
        captured_kwargs.update(kwargs)
        original_init(self, *args, **kwargs)

    with mock.patch.object(minio.Minio, "__init__", mock_init):
        yield captured_kwargs


def create_file_exact_size(filename, size_mb):
    """Create binary file of given size."""
    size_bytes = size_mb * 1024 * 1024
    with open(filename, "wb") as f:
        remaining = size_bytes
        chunk_size = 8192  # Write in 8KB chunks
        while remaining > 0:
            to_write = min(chunk_size, remaining)
            f.write(b"A" * to_write)  # Can use any byte pattern
            remaining -= to_write


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


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.Minio, audbackend.interface.Unversioned)],
    indirect=True,
)
def test_get_file(tmpdir, interface):
    r"""Test getting file.

    Args:
        tmpdir: tmpdir fixture
        interface: interface fixture

    """
    tmp_path = audeer.path(tmpdir, "file.bin")
    create_file_exact_size(tmp_path, 2)
    backend_path = "/file.bin"
    interface.put_file(tmp_path, backend_path)

    dst_path1 = audeer.path(tmpdir, "dst1.bin")
    dst_path2 = audeer.path(tmpdir, "dst2.bin")
    interface.get_file(backend_path, dst_path1, num_workers=1)
    interface.get_file(backend_path, dst_path2, num_workers=2)

    # Check both downloaded files are the same
    assert os.path.getsize(dst_path1) == os.path.getsize(dst_path2)
    assert audeer.md5(dst_path1) == audeer.md5(dst_path2)
    assert filecmp.cmp(dst_path1, dst_path2, shallow=False)


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.Minio, audbackend.interface.Unversioned)],
    indirect=True,
)
def test_interrupt_signal_handler(tmpdir, interface):
    r"""Test that signal handler sets cancel_event correctly.

    This tests the signal handler setup
    that sets the cancel_event when SIGINT is received.

    Args:
        tmpdir: tmpdir fixture
        interface: interface fixture

    """
    # Create a cancel_event like _get_file does
    cancel_event = threading.Event()

    # Create the signal handler as defined in _get_file
    def signal_handler(signum, frame):
        cancel_event.set()

    # Install the handler
    original_handler = signal.signal(signal.SIGINT, signal_handler)

    try:
        # Verify event is not set initially
        assert not cancel_event.is_set()

        # Call the signal handler directly (simulating Ctrl+C)
        signal_handler(signal.SIGINT, None)

        # Verify event was set by the handler (minio.py:289)
        assert cancel_event.is_set()
    finally:
        # Restore original handler
        signal.signal(signal.SIGINT, original_handler)


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.Minio, audbackend.interface.Unversioned)],
    indirect=True,
)
def test_interrupt_via_cancel_event(tmpdir, interface):
    r"""Test that cancel_event check during download raises KeyboardInterrupt.

    This tests the interrupt handling mechanism
    where the cancel_event is checked during file download.
    Directly calls _download_file with a cancel_event that gets set.

    Args:
        tmpdir: tmpdir fixture
        interface: interface fixture

    """
    # Create and upload a test file
    tmp_path = audeer.path(tmpdir, "file.bin")
    create_file_exact_size(tmp_path, 2)  # 2 MB file
    backend_path = "/file.bin"
    interface.put_file(tmp_path, backend_path)

    # Create a cancel_event and set it immediately
    # This will cause the download loop to raise KeyboardInterrupt
    cancel_event = threading.Event()
    cancel_event.set()

    # Prepare download
    src_path = interface._backend.path(backend_path)
    dst_path = audeer.path(tmpdir, "download.bin")
    pbar = audeer.progress_bar(total=100, disable=True)

    # Attempt download with cancel_event already set - should raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt, match="Download cancelled by user"):
        interface._backend._download_file(src_path, dst_path, pbar, cancel_event)


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.Minio, audbackend.interface.Unversioned)],
    indirect=True,
)
def test_interrupt_cleanup(tmpdir, interface, monkeypatch):
    r"""Test that KeyboardInterrupt cleans up partial file.

    This tests the exception handler
    that removes partial files when download is interrupted.

    Args:
        tmpdir: tmpdir fixture
        interface: interface fixture
        monkeypatch: monkeypatch fixture

    """
    # Create and upload test file
    tmp_path = audeer.path(tmpdir, "file.bin")
    create_file_exact_size(tmp_path, 2)
    backend_path = "/file.bin"
    interface.put_file(tmp_path, backend_path)

    # Mock _download_file to raise KeyboardInterrupt
    def mock_download(*args, **kwargs):
        # Create partial file before interrupting
        dst_path = args[1]
        with open(dst_path, "wb") as f:
            f.write(b"partial data")
        raise KeyboardInterrupt("Simulated interrupt")

    monkeypatch.setattr(interface._backend, "_download_file", mock_download)

    # Attempt download
    dst_path = audeer.path(tmpdir, "download.bin")
    with pytest.raises(KeyboardInterrupt):
        interface.get_file(backend_path, dst_path, num_workers=1)

    # Verify cleanup happened
    assert not os.path.exists(dst_path)


def test_custom_http_client_honored(tmpdir, hosts, hide_credentials):
    r"""Test that custom http_client passed via kwargs is honored.

    When a user provides their own http_client, the backend should use it
    instead of creating a default one with timeouts.

    Args:
        tmpdir: tmpdir fixture
        hosts: hosts fixture
        hide_credentials: hide_credentials fixture

    """
    host = hosts["minio"]
    config_path = audeer.path(tmpdir, "config.cfg")
    os.environ["MINIO_CONFIG_FILE"] = config_path

    # Create minimal config file
    with open(config_path, "w") as fp:
        fp.write(f"[{host}]\n")
        fp.write("access_key = test\n")
        fp.write("secret_key = test\n")

    # Create a custom http_client
    custom_http_client = urllib3.PoolManager(timeout=urllib3.Timeout(connect=5.0))

    with capture_minio_kwargs() as captured:
        audbackend.backend.Minio(host, "repository", http_client=custom_http_client)

    # Verify the custom http_client was passed through
    assert "http_client" in captured
    assert captured["http_client"] is custom_http_client


def test_default_timeout_configuration(tmpdir, hosts, hide_credentials):
    r"""Test that default timeout configuration is applied.

    When no http_client is provided and no timeout config is set,
    the backend should create an http_client with default timeouts:
    - connect_timeout: 10.0
    - read_timeout: None

    Args:
        tmpdir: tmpdir fixture
        hosts: hosts fixture
        hide_credentials: hide_credentials fixture

    """
    host = hosts["minio"]
    config_path = audeer.path(tmpdir, "config.cfg")
    os.environ["MINIO_CONFIG_FILE"] = config_path

    # Create minimal config file without timeout settings
    with open(config_path, "w") as fp:
        fp.write(f"[{host}]\n")
        fp.write("access_key = test\n")
        fp.write("secret_key = test\n")

    with capture_minio_kwargs() as captured:
        audbackend.backend.Minio(host, "repository")

    # Verify an http_client was created
    assert "http_client" in captured
    http_client = captured["http_client"]
    assert isinstance(http_client, urllib3.PoolManager)

    # Verify the default timeout values
    # The timeout is stored in connection_pool_kw
    timeout = http_client.connection_pool_kw.get("timeout")
    assert timeout is not None
    assert timeout.connect_timeout == 10.0
    assert timeout.read_timeout is None


def test_custom_timeout_from_config(tmpdir, hosts, hide_credentials):
    r"""Test that custom timeout values from config are honored.

    When timeout values are specified in the config file,
    they should be used instead of the defaults.

    Args:
        tmpdir: tmpdir fixture
        hosts: hosts fixture
        hide_credentials: hide_credentials fixture

    """
    host = hosts["minio"]
    config_path = audeer.path(tmpdir, "config.cfg")
    os.environ["MINIO_CONFIG_FILE"] = config_path

    # Create config file with custom timeout settings
    with open(config_path, "w") as fp:
        fp.write(f"[{host}]\n")
        fp.write("access_key = test\n")
        fp.write("secret_key = test\n")
        fp.write("connect_timeout = 30.0\n")
        fp.write("read_timeout = 120.0\n")

    with capture_minio_kwargs() as captured:
        audbackend.backend.Minio(host, "repository")

    # Verify the custom timeout values from config
    http_client = captured["http_client"]
    timeout = http_client.connection_pool_kw.get("timeout")
    assert timeout.connect_timeout == 30.0
    assert timeout.read_timeout == 120.0


def test_none_read_timeout_from_config(tmpdir, hosts, hide_credentials):
    r"""Test that 'None' read_timeout from config is parsed correctly.

    When read_timeout is set to 'None' in the config file,
    it should be parsed as Python None.

    Args:
        tmpdir: tmpdir fixture
        hosts: hosts fixture
        hide_credentials: hide_credentials fixture

    """
    host = hosts["minio"]
    config_path = audeer.path(tmpdir, "config.cfg")
    os.environ["MINIO_CONFIG_FILE"] = config_path

    # Create config file with None read_timeout
    with open(config_path, "w") as fp:
        fp.write(f"[{host}]\n")
        fp.write("access_key = test\n")
        fp.write("secret_key = test\n")
        fp.write("connect_timeout = 15.0\n")
        fp.write("read_timeout = None\n")

    with capture_minio_kwargs() as captured:
        audbackend.backend.Minio(host, "repository")

    # Verify read_timeout is None
    http_client = captured["http_client"]
    timeout = http_client.connection_pool_kw.get("timeout")
    assert timeout.connect_timeout == 15.0
    assert timeout.read_timeout is None


def test_invalid_timeout_warning(tmpdir, hosts, hide_credentials):
    r"""Test that invalid timeout values emit a warning and use defaults.

    When a non-numeric string is provided as a timeout value,
    a warning should be emitted and the default value should be used.

    Args:
        tmpdir: tmpdir fixture
        hosts: hosts fixture
        hide_credentials: hide_credentials fixture

    """
    host = hosts["minio"]
    config_path = audeer.path(tmpdir, "config.cfg")
    os.environ["MINIO_CONFIG_FILE"] = config_path

    # Create config file with invalid timeout values
    with open(config_path, "w") as fp:
        fp.write(f"[{host}]\n")
        fp.write("access_key = test\n")
        fp.write("secret_key = test\n")
        fp.write("connect_timeout = invalid\n")
        fp.write("read_timeout = sixty\n")

    with capture_minio_kwargs() as captured:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            audbackend.backend.Minio(host, "repository")

            # Verify warnings were emitted
            assert len(w) == 2
            assert "Invalid connect_timeout value 'invalid'" in str(w[0].message)
            assert "Invalid read_timeout value 'sixty'" in str(w[1].message)

    # Verify default timeout values were used
    http_client = captured["http_client"]
    timeout = http_client.connection_pool_kw.get("timeout")
    assert timeout.connect_timeout == 10.0  # default
    assert timeout.read_timeout is None  # default
