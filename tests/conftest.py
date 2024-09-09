import getpass
import os

import fsspec
import minio
import pytest

import audeer

import audbackend


# UID for test session
# Repositories on the host will be named
# unittest-<session-uid>-<repository-uid>
pytest.UID = audeer.uid()[:8]


@pytest.fixture(scope="function")
def filesystem(tmpdir):
    root = audeer.mkdir(tmpdir, f"unittest-{pytest.UID}-{audeer.uid()[:8]}")
    # Wrap "local" filesystem in "dir" filesystem
    # to return paths relatiove to root
    yield fsspec.filesystem(
        "dir",
        path=root,
        fs=fsspec.filesystem("local"),
    )


@pytest.fixture(scope="function")
def minio_filesystem():
    bucket = f"unittest-{pytest.UID}-{audeer.uid()[:8]}"

    # Use MinIO playground, compare
    # https://min.io/docs/minio/linux/developers/python/API.html
    url = "play.minio.io:9000"
    access = "Q3AM3UQ867SPQQA43P2F"
    secret = "zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG"

    # Create bucket
    client = minio.Minio(url, access_key=access, secret_key=secret)
    client.make_bucket(bucket)

    fs = fsspec.filesystem(
        "s3",
        endpoint_url=f"https://{url}",
        key=access,
        secret=secret,
    )
    fs.bucket = bucket

    yield fs

    # Delete all objects in bucket
    objects = client.list_objects(bucket, recursive=True)
    for obj in objects:
        client.remove_object(bucket, obj.object_name)

    # Delete bucket
    client.remove_bucket(bucket)


# @pytest.fixture(scope="package", autouse=True)
# def authentication():
#     """Provide authentication tokens for supported backends."""
#     if pytest.HOSTS["minio"] == "play.min.io":
#         defaults = {}
#         for key in [
#             "MINIO_ACCESS_KEY",
#             "MINIO_SECRET_KEY",
#         ]:
#             defaults[key] = os.environ.get(key, None)
#
#         os.environ["MINIO_ACCESS_KEY"] = "Q3AM3UQ867SPQQA43P2F"
#         os.environ["MINIO_SECRET_KEY"] = "zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG"
#
#         yield
#
#         for key, value in defaults.items():
#             if value is not None:
#                 os.environ[key] = value
#             elif key in os.environ:
#                 del os.environ[key]


# @pytest.fixture(scope="package", autouse=False)
# def hosts(tmpdir_factory):
#     return {
#         # For tests based on backend names (deprecated),
#         # like audbackend.access()
#         "artifactory": pytest.HOSTS["artifactory"],
#         "file-system": str(tmpdir_factory.mktemp("host")),
#         "minio": pytest.HOSTS["minio"],
#         "single-folder": str(tmpdir_factory.mktemp("host")),
#     }


@pytest.fixture(scope="function", autouse=False)
def owner(request):
    r"""Return expected owner value."""
    backend_cls = request.param
    if (
        hasattr(audbackend.backend, "Artifactory")
        and backend_cls == audbackend.backend.Artifactory
    ):
        host_wo_https = pytest.HOSTS["artifactory"][8:]
        owner = backend_cls.get_authentication(host_wo_https)[0]
    elif (
        hasattr(audbackend.backend, "Minio") and backend_cls == audbackend.backend.Minio
    ):
        # There seems to be a MinIO bug here
        owner = None
    else:
        if os.name == "nt":
            owner = "Administrators"
        else:
            owner = getpass.getuser()

    yield owner


@pytest.fixture(scope="package", autouse=True)
def cleanup_coverage():
    # clean up old coverage files
    path = audeer.path(
        os.path.dirname(os.path.realpath(__file__)),
        ".coverage.*",
    )
    for file in audeer.list_file_names(path):
        os.remove(file)
