import getpass
import os

import pytest

import audeer
import audformat

import audbackend


# Config file marking a local MinIO server as plain HTTP.
# Shared with CI, so both run against the same settings.
MINIO_CONFIG_FILE = audeer.path(
    os.path.dirname(__file__),
    "..",
    ".github",
    "minio-test.cfg",
)

# UID for test session
# Repositories on the host will be named
# unittest-<session-uid>-<repository-uid>
pytest.UID = audeer.uid()[:8]

# MinIO shut down its public playground at play.min.io
# when it archived the community server,
# so tests run against a MinIO on your own machine,
# started by compose.yaml, see CONTRIBUTING.rst.
# CI points ``AUDBACKEND_TEST_MINIO_HOST`` at its own instance.
#
# 127.0.0.1 rather than localhost:
# compose publishes the port on the IPv4 loopback only,
# while localhost resolves to IPv6 ``::1`` first on some systems,
# which makes every connection attempt fail.
pytest.HOSTS = {
    "minio": os.environ.get("AUDBACKEND_TEST_MINIO_HOST", "127.0.0.1:9000"),
}


@pytest.fixture(scope="package", autouse=True)
def authentication():
    """Provide authentication tokens for supported backends."""
    keys = ["MINIO_ACCESS_KEY", "MINIO_SECRET_KEY", "MINIO_CONFIG_FILE"]
    defaults = {key: os.environ.get(key, None) for key in keys}

    # Defaults of a local MinIO server, see CONTRIBUTING.rst.
    # Nothing already set is overwritten,
    # so CI and anyone running their own server keep their settings.
    #
    # A local server speaks plain HTTP,
    # which the backend can only learn from a config file.
    # This has to come first,
    # as ``get_config()`` reads ``MINIO_CONFIG_FILE``.
    os.environ.setdefault("MINIO_CONFIG_FILE", MINIO_CONFIG_FILE)

    # Only fill in credentials the config file does not provide:
    # ``get_authentication()`` prefers the environment over the config file,
    # so setting them unconditionally would shadow
    # the credentials of a user provided server.
    config = audbackend.backend.Minio.get_config(pytest.HOSTS["minio"])
    if "access_key" not in config:
        os.environ.setdefault("MINIO_ACCESS_KEY", "minioadmin")
    if "secret_key" not in config:
        os.environ.setdefault("MINIO_SECRET_KEY", "minioadmin")

    yield

    for key, value in defaults.items():
        if value is not None:
            os.environ[key] = value
        elif key in os.environ:
            del os.environ[key]


@pytest.fixture(scope="package", autouse=False)
def hosts(tmpdir_factory):
    return {
        # For tests based on backend names (deprecated),
        # like audbackend.access()
        "file-system": str(tmpdir_factory.mktemp("host")),
        "minio": pytest.HOSTS["minio"],
        "single-folder": str(tmpdir_factory.mktemp("host")),
    }


@pytest.fixture(scope="function", autouse=False)
def owner(request):
    r"""Return expected owner value."""
    backend_cls = request.param
    if hasattr(audbackend.backend, "Minio") and backend_cls == audbackend.backend.Minio:
        if os.name == "nt":
            owner = "runneradmin"
        else:
            owner = getpass.getuser()
    else:
        if os.name == "nt":
            owner = "Administrators"
        else:
            owner = getpass.getuser()

    yield owner


@pytest.fixture(scope="function")
def parquet_file(tmpdir):
    r"""Provide a parquet file with checksum stored in metadata.

    ``audformat`` provides the possibility
    to store a checksum,
    based on the content of a parquet file,
    in the metadata of that file.
    The motivation is that a parquet file
    cannot be written in a deterministic way
    and the checksum is a way to track,
    if the content has changed.

    """
    db = audformat.Database("mydb")
    db.schemes["age"] = audformat.Scheme("int")
    db["files"] = audformat.Table(audformat.filewise_index(["f1"]))
    db["files"]["age"] = audformat.Column(scheme_id="age")
    db["files"]["age"].set([40])
    path = audeer.path(tmpdir, "files.parquet")
    db["files"].save(
        audeer.replace_file_extension(path, ""),
        storage_format="parquet",
    )

    yield path


@pytest.fixture(scope="function", autouse=False)
def interface(tmpdir_factory, request):
    r"""Create a backend with interface.

    This fixture should be called indirectly
    providing a list of ``(backend, interface)`` tuples.
    For example, to create a file-system backend
    and access it with a versioned interface:

    .. code-block:: python

        @pytest.mark.parametrize(
            "interface",
            [(audbackend.backend.FileSystem, audbackend.interface.Versioned)],
            indirect=True,
        )

    At the end of the test the backend is deleted.

    """
    backend_cls, interface_cls = request.param
    if hasattr(audbackend.backend, "Minio") and backend_cls == audbackend.backend.Minio:
        host = pytest.HOSTS["minio"]
    else:
        host = str(tmpdir_factory.mktemp("host"))
    repository = f"unittest-{pytest.UID}-{audeer.uid()[:8]}"

    backend_cls.create(host, repository)
    with backend_cls(host, repository) as backend:
        interface = interface_cls(backend)

        yield interface

    backend_cls.delete(host, repository)


@pytest.fixture(scope="package", autouse=True)
def cleanup_coverage():
    # clean up old coverage files
    path = audeer.path(
        os.path.dirname(os.path.realpath(__file__)),
        ".coverage.*",
    )
    for file in audeer.list_file_names(path):
        os.remove(file)
