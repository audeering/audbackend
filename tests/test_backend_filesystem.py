import os

import pytest

import audeer

import audbackend

from bad_file_system import BadFileSystem


@pytest.mark.parametrize("repository", [f"unittest-{pytest.UID}-{audeer.uid()[:8]}"])
def test_create_delete_repositories(tmpdir, repository):
    host = audeer.mkdir(tmpdir, "host")
    audbackend.backend.FileSystem.create(host, repository)
    with pytest.raises(audbackend.BackendError):
        # Repository exists already
        audbackend.backend.FileSystem.create(host, repository)
    audbackend.backend.FileSystem.delete(host, repository)


@pytest.mark.parametrize(
    "interface",
    [(BadFileSystem, audbackend.interface.Versioned)],
    indirect=True,
)
def test_get_file_interrupt(tmpdir, interface):
    src_path = audeer.path(tmpdir, "~tmp")

    # put local file on backend
    with open(src_path, "w") as fp:
        fp.write("remote")
    checksum_remote = audeer.md5(src_path)
    interface.put_file(src_path, "/file", "1.0.0")

    # change content of local file
    with open(src_path, "w") as fp:
        fp.write("local")
    checksum_local = audeer.md5(src_path)
    assert checksum_local != checksum_remote

    # Try to use malfanctioning exists() method
    with pytest.raises(audbackend.BackendError):
        interface.exists("/file", "1.0.0")
    assert interface.exists("/file", "1.0.0", suppress_backend_errors=True) is False

    # try to read remote file, local file remains unchanged
    with pytest.raises(audbackend.BackendError):
        interface.get_file("/file", src_path, "1.0.0")
    assert audeer.md5(src_path) == checksum_local


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.FileSystem, audbackend.interface.Maven)],
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
            "file.tar/1.0.0/file.tar-1.0.0.gz",
        ),
        (
            "/file.tar.gz",
            "1.0.0",
            ["tar.gz"],
            False,
            "file/1.0.0/file-1.0.0.tar.gz",
        ),
        (
            "/.tar.gz",
            "1.0.0",
            ["tar.gz"],
            False,
            ".tar/1.0.0/.tar-1.0.0.gz",
        ),
        (
            "/tar.gz",
            "1.0.0",
            ["tar.gz"],
            False,
            "tar/1.0.0/tar-1.0.0.gz",
        ),
        (
            "/.tar.gz",
            "1.0.0",
            [],
            False,
            ".tar/1.0.0/.tar-1.0.0.gz",
        ),
        (
            "/.tar",
            "1.0.0",
            [],
            False,
            ".tar/1.0.0/.tar-1.0.0",
        ),
        (
            "/tar",
            "1.0.0",
            [],
            False,
            "tar/1.0.0/tar-1.0.0",
        ),
        # test regex
        (
            "/file.0.tar.gz",
            "1.0.0",
            [r"\d+.tar.gz"],
            False,
            "file.0.tar/1.0.0/file.0.tar-1.0.0.gz",
        ),
        (
            "/file.0.tar.gz",
            "1.0.0",
            [r"\d+.tar.gz"],
            True,
            "file/1.0.0/file-1.0.0.0.tar.gz",
        ),
        (
            "/file.99.tar.gz",
            "1.0.0",
            [r"\d+.tar.gz"],
            True,
            "file/1.0.0/file-1.0.0.99.tar.gz",
        ),
        (
            "/file.prediction.99.tar.gz",
            "1.0.0",
            [r"prediction.\d+.tar.gz", r"truth.tar.gz"],
            True,
            "file/1.0.0/file-1.0.0.prediction.99.tar.gz",
        ),
        (
            "/file.truth.tar.gz",
            "1.0.0",
            [r"prediction.\d+.tar.gz", r"truth.tar.gz"],
            True,
            "file/1.0.0/file-1.0.0.truth.tar.gz",
        ),
        (
            "/file.99.tar.gz",
            "1.0.0",
            [r"(\d+.)?tar.gz"],
            True,
            "file/1.0.0/file-1.0.0.99.tar.gz",
        ),
        (
            "/file.tar.gz",
            "1.0.0",
            [r"(\d+.)?tar.gz"],
            True,
            "file/1.0.0/file-1.0.0.tar.gz",
        ),
    ],
)
def test_maven_file_structure(
    tmpdir, interface, file, version, extensions, regex, expected
):
    expected = expected.replace("/", os.path.sep)

    interface.extensions = extensions
    interface.regex = regex

    src_path = audeer.touch(audeer.path(tmpdir, "tmp"))
    interface.put_file(src_path, file, version)

    path = os.path.join(interface.backend._root, expected)
    path_expected = interface.backend._expand(
        interface._path_with_version(file, version),
    )
    assert path_expected == path
    assert interface.ls(file) == [(file, version)]
    assert interface.ls() == [(file, version)]


@pytest.mark.parametrize("repository", [f"unittest-{pytest.UID}-{audeer.uid()[:8]}"])
def test_open_close(tmpdir, repository):
    host = audeer.mkdir(tmpdir, "host")
    backend = audbackend.backend.FileSystem(host, repository)
    with pytest.raises(audbackend.BackendError):
        # Repository does not exist yet
        backend.open()
    audbackend.backend.FileSystem.create(host, repository)
    backend.open()
    backend.close()
