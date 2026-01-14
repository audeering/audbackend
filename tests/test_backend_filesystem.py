import os
import zipfile

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


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.FileSystem, audbackend.interface.Versioned)],
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
    [(audbackend.backend.FileSystem, audbackend.interface.Unversioned)],
    indirect=True,
)
def test_streaming_cleanup_existing_directory(tmpdir, interface):
    """Test cleanup removes only extracted files when dst_root already exists.

    When extracting a malformed archive to an existing directory fails,
    only the extracted files should be removed, not the entire directory
    or pre-existing files.

    """
    # Skip if stream-unzip is not available
    try:
        from stream_unzip import stream_unzip  # noqa: F401
    except ImportError:
        pytest.skip("stream-unzip not available")

    # Create destination directory with pre-existing file
    dst_root = audeer.path(tmpdir, "existing_dir")
    audeer.mkdir(dst_root)
    pre_existing_file = audeer.path(dst_root, "pre_existing.txt")
    with open(pre_existing_file, "w") as f:
        f.write("I was here before")

    # Create and upload a malformed ZIP archive
    malformed_zip = audeer.path(tmpdir, "malformed.zip")
    audeer.touch(malformed_zip)  # Empty file, not a valid ZIP
    interface.put_file(malformed_zip, "/malformed.zip")

    # Try to extract - should fail
    with pytest.raises(RuntimeError, match="Broken archive"):
        interface.get_archive("/malformed.zip", dst_root)

    # Verify pre-existing file still exists
    assert os.path.exists(pre_existing_file)
    with open(pre_existing_file) as f:
        assert f.read() == "I was here before"

    # Verify destination directory still exists
    assert os.path.isdir(dst_root)


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.FileSystem, audbackend.interface.Unversioned)],
    indirect=True,
)
def test_streaming_cleanup_extracted_files(tmpdir, interface):
    """Test cleanup removes extracted files on validation failure.

    When extracting an archive to an existing directory fails due to
    checksum validation, the extracted files should be removed but
    pre-existing files should remain.

    """
    # Skip if stream-unzip is not available
    try:
        from stream_unzip import stream_unzip  # noqa: F401
    except ImportError:
        pytest.skip("stream-unzip not available")

    # Create destination directory with pre-existing file
    dst_root = audeer.path(tmpdir, "existing_dir")
    audeer.mkdir(dst_root)
    pre_existing_file = audeer.path(dst_root, "pre_existing.txt")
    with open(pre_existing_file, "w") as f:
        f.write("I was here before")

    # Create a valid ZIP archive with content
    src_root = audeer.path(tmpdir, "src")
    audeer.mkdir(src_root)
    with open(audeer.path(src_root, "new_file.txt"), "w") as f:
        f.write("New content")

    archive_path = audeer.path(tmpdir, "archive.zip")
    audeer.create_archive(src_root, None, archive_path)
    interface.put_file(archive_path, "/archive.zip")

    # Mock checksum to force validation failure after extraction
    original_checksum = interface.backend.checksum

    def bad_checksum(path):
        if path.endswith(".zip"):
            return "bad_checksum_value"
        return original_checksum(path)

    interface.backend.checksum = bad_checksum

    # Try to extract with validation - should fail after extraction
    with pytest.raises(InterruptedError, match="checksum"):
        interface.get_archive("/archive.zip", dst_root, validate=True)

    # Restore original checksum
    interface.backend.checksum = original_checksum

    # Verify pre-existing file still exists
    assert os.path.exists(pre_existing_file)
    with open(pre_existing_file) as f:
        assert f.read() == "I was here before"

    # Verify extracted file was cleaned up
    extracted_file = audeer.path(dst_root, "new_file.txt")
    assert not os.path.exists(extracted_file)

    # Verify destination directory still exists
    assert os.path.isdir(dst_root)


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.FileSystem, audbackend.interface.Unversioned)],
    indirect=True,
)
def test_streaming_zip_with_directory_entries(tmpdir, interface):
    """Test streaming extraction handles ZIP archives with directory entries.

    Some ZIP tools create archives with explicit directory entries
    (entries ending with '/'). These should be skipped during extraction
    while still extracting the files within those directories.

    """
    # Skip if stream-unzip is not available
    try:
        from stream_unzip import stream_unzip  # noqa: F401
    except ImportError:
        pytest.skip("stream-unzip not available")

    # Create source files with subdirectory
    src_root = audeer.path(tmpdir, "src")
    audeer.mkdir(src_root)
    subdir = audeer.path(src_root, "subdir")
    audeer.mkdir(subdir)
    with open(audeer.path(src_root, "file1.txt"), "w") as f:
        f.write("content1")
    with open(audeer.path(subdir, "file2.txt"), "w") as f:
        f.write("content2")

    # Create ZIP with explicit directory entries (unlike audeer.create_archive)
    archive_path = audeer.path(tmpdir, "archive_with_dirs.zip")
    with zipfile.ZipFile(archive_path, "w") as zf:
        # Add directory entry explicitly
        zf.write(subdir, "subdir/")
        # Add files
        zf.write(audeer.path(src_root, "file1.txt"), "file1.txt")
        zf.write(audeer.path(subdir, "file2.txt"), os.path.join("subdir", "file2.txt"))

    # Verify the ZIP contains a directory entry
    with zipfile.ZipFile(archive_path, "r") as zf:
        names = zf.namelist()
        assert "subdir/" in names  # Directory entry exists

    # Upload archive
    interface.put_file(archive_path, "/archive_with_dirs.zip")

    # Extract using streaming
    dst_root = audeer.path(tmpdir, "dst")
    extracted = interface.get_archive("/archive_with_dirs.zip", dst_root)

    # Verify files were extracted (directory entry should be skipped)
    assert "file1.txt" in extracted
    assert os.path.join("subdir", "file2.txt") in extracted
    assert f"subdir{os.sep}" not in extracted  # Directory entry should not be in result

    # Verify actual files exist
    assert os.path.exists(audeer.path(dst_root, "file1.txt"))
    assert os.path.exists(audeer.path(dst_root, "subdir", "file2.txt"))
    with open(audeer.path(dst_root, "file1.txt")) as f:
        assert f.read() == "content1"
    with open(audeer.path(dst_root, "subdir", "file2.txt")) as f:
        assert f.read() == "content2"
