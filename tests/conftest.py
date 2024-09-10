import os

import fsspec
import minio
import pytest

import audeer


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


@pytest.fixture(scope="package", autouse=True)
def cleanup_coverage():
    # clean up old coverage files
    path = audeer.path(
        os.path.dirname(os.path.realpath(__file__)),
        ".coverage.*",
    )
    for file in audeer.list_file_names(path):
        os.remove(file)
