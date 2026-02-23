"""Tests for async download functionality."""

import os

import pytest

import audeer

import audbackend


# ============================================================================
# Tests for interface.get_files() method
# ============================================================================


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.Minio, audbackend.interface.Unversioned)],
    indirect=True,
)
def test_interface_get_files_unversioned(tmpdir, interface):
    """Test Unversioned interface get_files method."""
    # Create and upload test files
    src_dir = audeer.path(tmpdir, "src")
    audeer.mkdir(src_dir)

    for i in range(3):
        src_path = audeer.path(src_dir, f"file{i}.txt")
        with open(src_path, "w") as f:
            f.write(f"Content {i}")
        interface.put_file(src_path, f"/data/file{i}.txt")

    # Download using interface method
    dst_dir = audeer.path(tmpdir, "dst")
    files_to_download = [
        (f"/data/file{i}.txt", audeer.path(dst_dir, f"file{i}.txt")) for i in range(3)
    ]

    downloaded = interface.get_files(files_to_download)

    # Verify all files were downloaded
    assert len(downloaded) == 3
    for i in range(3):
        dst_path = audeer.path(dst_dir, f"file{i}.txt")
        assert os.path.exists(dst_path)
        with open(dst_path) as f:
            assert f.read() == f"Content {i}"


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.Minio, audbackend.interface.Unversioned)],
    indirect=True,
)
def test_interface_get_files_empty_list(tmpdir, interface):
    """Test interface get_files with empty list."""
    downloaded = interface.get_files([])
    assert downloaded == []


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.Minio, audbackend.interface.Unversioned)],
    indirect=True,
)
def test_interface_get_files_with_callback(tmpdir, interface):
    """Test interface get_files with progress callback."""
    # Create and upload test files
    src_dir = audeer.path(tmpdir, "src")
    audeer.mkdir(src_dir)

    for i in range(2):
        src_path = audeer.path(src_dir, f"file{i}.txt")
        with open(src_path, "w") as f:
            f.write(f"Content {i}")
        interface.put_file(src_path, f"/data/file{i}.txt")

    # Track callback calls
    callback_calls = []

    def progress_callback(src_path, dst_path):
        callback_calls.append((src_path, dst_path))

    # Download with callback
    dst_dir = audeer.path(tmpdir, "dst")
    files_to_download = [
        (f"/data/file{i}.txt", audeer.path(dst_dir, f"file{i}.txt")) for i in range(2)
    ]

    interface.get_files(files_to_download, progress_callback=progress_callback)

    # Verify callback was called for each file
    assert len(callback_calls) == 2


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.Minio, audbackend.interface.Unversioned)],
    indirect=True,
)
def test_interface_get_files_high_concurrency(tmpdir, interface):
    """Test interface get_files with high concurrency."""
    # Create and upload many small files
    src_dir = audeer.path(tmpdir, "src")
    audeer.mkdir(src_dir)

    num_files = 20
    for i in range(num_files):
        src_path = audeer.path(src_dir, f"file{i}.txt")
        with open(src_path, "w") as f:
            f.write(f"File {i}")
        interface.put_file(src_path, f"/data/file{i}.txt")

    # Download with high concurrency
    dst_dir = audeer.path(tmpdir, "dst")
    files_to_download = [
        (f"/data/file{i}.txt", audeer.path(dst_dir, f"file{i}.txt"))
        for i in range(num_files)
    ]

    downloaded = interface.get_files(
        files_to_download,
        max_concurrent=100,  # More workers than files
    )

    assert len(downloaded) == num_files


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.Minio, audbackend.interface.Versioned)],
    indirect=True,
)
def test_interface_get_files_versioned(tmpdir, interface):
    """Test Versioned interface get_files method."""
    # Create and upload test files
    src_dir = audeer.path(tmpdir, "src")
    audeer.mkdir(src_dir)

    for i in range(3):
        src_path = audeer.path(src_dir, f"file{i}.txt")
        with open(src_path, "w") as f:
            f.write(f"Content {i}")
        interface.put_file(src_path, f"/data/file{i}.txt", "1.0.0")

    # Download using interface method
    dst_dir = audeer.path(tmpdir, "dst")
    files_to_download = [
        (f"/data/file{i}.txt", audeer.path(dst_dir, f"file{i}.txt"), "1.0.0")
        for i in range(3)
    ]

    downloaded = interface.get_files(files_to_download)

    # Verify all files were downloaded
    assert len(downloaded) == 3
    for i in range(3):
        dst_path = audeer.path(dst_dir, f"file{i}.txt")
        assert os.path.exists(dst_path)
        with open(dst_path) as f:
            assert f.read() == f"Content {i}"


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.Minio, audbackend.interface.Versioned)],
    indirect=True,
)
def test_interface_get_files_versioned_empty_list(tmpdir, interface):
    """Test Versioned interface get_files with empty list."""
    downloaded = interface.get_files([])
    assert downloaded == []


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.FileSystem, audbackend.interface.Unversioned)],
    indirect=True,
)
def test_interface_get_files_filesystem(tmpdir, interface):
    """Test interface get_files with FileSystem backend."""
    # Create and upload test files
    src_dir = audeer.path(tmpdir, "src")
    audeer.mkdir(src_dir)

    for i in range(2):
        src_path = audeer.path(src_dir, f"file{i}.txt")
        with open(src_path, "w") as f:
            f.write(f"Content {i}")
        interface.put_file(src_path, f"/data/file{i}.txt")

    # Download using interface method
    dst_dir = audeer.path(tmpdir, "dst")
    files_to_download = [
        (f"/data/file{i}.txt", audeer.path(dst_dir, f"file{i}.txt")) for i in range(2)
    ]

    downloaded = interface.get_files(files_to_download)

    # Verify all files were downloaded
    assert len(downloaded) == 2
    for i in range(2):
        dst_path = audeer.path(dst_dir, f"file{i}.txt")
        assert os.path.exists(dst_path)


# ============================================================================
# Tests for interface.get_archives() method
# ============================================================================


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.Minio, audbackend.interface.Unversioned)],
    indirect=True,
)
def test_interface_get_archives_unversioned(tmpdir, interface):
    """Test Unversioned interface get_archives method."""
    # Create source files and upload as archives
    src_dir = audeer.path(tmpdir, "src")
    audeer.mkdir(src_dir)

    for i in range(3):
        file_path = audeer.path(src_dir, f"file{i}.txt")
        with open(file_path, "w") as f:
            f.write(f"Content {i}")
        interface.put_archive(src_dir, f"/archive{i}.zip", files=[f"file{i}.txt"])

    # Download and extract using interface method
    archives_to_download = [
        (f"/archive{i}.zip", audeer.path(tmpdir, f"dst{i}")) for i in range(3)
    ]

    results = interface.get_archives(archives_to_download)

    # Verify all archives were downloaded and extracted
    assert len(results) == 3
    for i in range(3):
        dst_dir = audeer.path(tmpdir, f"dst{i}")
        file_path = audeer.path(dst_dir, f"file{i}.txt")
        assert os.path.exists(file_path)
        with open(file_path) as f:
            assert f.read() == f"Content {i}"


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.Minio, audbackend.interface.Unversioned)],
    indirect=True,
)
def test_interface_get_archives_empty_list(tmpdir, interface):
    """Test interface get_archives with empty list."""
    results = interface.get_archives([])
    assert results == []


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.Minio, audbackend.interface.Unversioned)],
    indirect=True,
)
def test_interface_get_archives_with_callback(tmpdir, interface):
    """Test interface get_archives with progress callback."""
    # Create source files and upload as archives
    src_dir = audeer.path(tmpdir, "src")
    audeer.mkdir(src_dir)

    for i in range(2):
        file_path = audeer.path(src_dir, f"file{i}.txt")
        with open(file_path, "w") as f:
            f.write(f"Content {i}")
        interface.put_archive(src_dir, f"/archive{i}.zip", files=[f"file{i}.txt"])

    # Track callback calls
    callback_calls = []

    def progress_callback(src_path, dst_root):
        callback_calls.append((src_path, dst_root))

    # Download with callback
    archives_to_download = [
        (f"/archive{i}.zip", audeer.path(tmpdir, f"dst{i}")) for i in range(2)
    ]

    interface.get_archives(archives_to_download, progress_callback=progress_callback)

    # Verify callback was called for each archive
    assert len(callback_calls) == 2


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.Minio, audbackend.interface.Versioned)],
    indirect=True,
)
def test_interface_get_archives_versioned(tmpdir, interface):
    """Test Versioned interface get_archives method."""
    # Create source files and upload as archives
    src_dir = audeer.path(tmpdir, "src")
    audeer.mkdir(src_dir)

    for i in range(3):
        file_path = audeer.path(src_dir, f"file{i}.txt")
        with open(file_path, "w") as f:
            f.write(f"Content {i}")
        interface.put_archive(
            src_dir, f"/archive{i}.zip", "1.0.0", files=[f"file{i}.txt"]
        )

    # Download and extract using interface method
    archives_to_download = [
        (f"/archive{i}.zip", audeer.path(tmpdir, f"dst{i}"), "1.0.0") for i in range(3)
    ]

    results = interface.get_archives(archives_to_download)

    # Verify all archives were downloaded and extracted
    assert len(results) == 3
    for i in range(3):
        dst_dir = audeer.path(tmpdir, f"dst{i}")
        file_path = audeer.path(dst_dir, f"file{i}.txt")
        assert os.path.exists(file_path)
        with open(file_path) as f:
            assert f.read() == f"Content {i}"


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.Minio, audbackend.interface.Versioned)],
    indirect=True,
)
def test_interface_get_archives_versioned_empty_list(tmpdir, interface):
    """Test Versioned interface get_archives with empty list."""
    results = interface.get_archives([])
    assert results == []


@pytest.mark.parametrize(
    "interface",
    [(audbackend.backend.FileSystem, audbackend.interface.Unversioned)],
    indirect=True,
)
def test_interface_get_archives_filesystem(tmpdir, interface):
    """Test interface get_archives with FileSystem backend."""
    # Create source files and upload as archives
    src_dir = audeer.path(tmpdir, "src")
    audeer.mkdir(src_dir)

    for i in range(2):
        file_path = audeer.path(src_dir, f"file{i}.txt")
        with open(file_path, "w") as f:
            f.write(f"Content {i}")
        interface.put_archive(src_dir, f"/archive{i}.zip", files=[f"file{i}.txt"])

    # Download and extract using interface method
    archives_to_download = [
        (f"/archive{i}.zip", audeer.path(tmpdir, f"dst{i}")) for i in range(2)
    ]

    results = interface.get_archives(archives_to_download)

    # Verify all archives were downloaded and extracted
    assert len(results) == 2
    for i in range(2):
        dst_dir = audeer.path(tmpdir, f"dst{i}")
        file_path = audeer.path(dst_dir, f"file{i}.txt")
        assert os.path.exists(file_path)
