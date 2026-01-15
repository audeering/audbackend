import os
import re

import pytest

import audeer

import audbackend


@pytest.mark.parametrize(
    "paths, expected",
    [
        (["/"], "/"),
        (["/", ""], "/"),
        (["/file"], "/file"),
        (["/file/"], "/file/"),
        (["/root", "file"], "/root/file"),
        (["/root", "file/"], "/root/file/"),
        (["/", "root", None, "", "file", ""], "/root/file"),
        (["/", "root", None, "", "file", "/"], "/root/file/"),
        (["/", "root", None, "", "file", "/", ""], "/root/file/"),
        pytest.param(
            [""],
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(
            ["file"],
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(
            ["sub/file"],
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(
            ["", "/file"],
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
    ],
)
@pytest.mark.parametrize(
    "backend",
    [
        audbackend.backend.Base("host", "repository"),
    ],
)
def test_join(paths, expected, backend):
    assert backend.join(*paths) == expected


@pytest.mark.parametrize(
    "path, expected",
    [
        ("/", ("/", "")),
        ("/file", ("/", "file")),
        ("/root/", ("/root/", "")),
        ("/root/file", ("/root/", "file")),
        ("/root/file/", ("/root/file/", "")),
        ("//root///file", ("/root/", "file")),
        pytest.param(
            "",
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(
            "file",
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(
            "sub/file",
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
    ],
)
@pytest.mark.parametrize(
    "backend",
    [
        audbackend.backend.Base("host", "repository"),
    ],
)
def test_split(path, expected, backend):
    assert backend.split(path) == expected


@pytest.mark.parametrize(
    "backend",
    [
        audbackend.backend.Base("host", "repository"),
    ],
)
def test_errors(tmpdir, backend):
    # Check errors when backend is not opened
    error_msg = re.escape(
        "Call 'Backend.open()' to establish a connection to the repository first."
    )
    path = "file.txt"
    src_path = "src.txt"
    dst_path = "dst.txt"
    src_root = "."
    with pytest.raises(RuntimeError, match=error_msg):
        backend.checksum(path)
    with pytest.raises(RuntimeError, match=error_msg):
        backend.copy_file(src_path, dst_path)
    with pytest.raises(RuntimeError, match=error_msg):
        backend.date(path)
    with pytest.raises(RuntimeError, match=error_msg):
        backend.exists(path)
    with pytest.raises(RuntimeError, match=error_msg):
        backend.get_archive(src_path, dst_path)
    with pytest.raises(RuntimeError, match=error_msg):
        backend.get_file(src_path, dst_path)
    with pytest.raises(RuntimeError, match=error_msg):
        backend.ls(path)
    with pytest.raises(RuntimeError, match=error_msg):
        backend.move_file(src_path, dst_path)
    with pytest.raises(RuntimeError, match=error_msg):
        backend.owner(path)
    with pytest.raises(RuntimeError, match=error_msg):
        backend.put_archive(src_root, dst_path)
    with pytest.raises(RuntimeError, match=error_msg):
        backend.put_file(src_path, dst_path)
    with pytest.raises(RuntimeError, match=error_msg):
        backend.remove_file(path)


# Build backend-interface combinations for test_size
_size_test_backends = [
    (audbackend.backend.FileSystem, audbackend.interface.Versioned),
    (audbackend.backend.Minio, audbackend.interface.Versioned),
]
if hasattr(audbackend.backend, "Artifactory"):
    _size_test_backends.append(
        (audbackend.backend.Artifactory, audbackend.interface.Versioned)
    )


@pytest.mark.parametrize(
    "interface",
    _size_test_backends,
    indirect=True,
)
def test_size(tmpdir, interface):
    """Test _size method returns correct file size.

    This test verifies that the backend's _size method
    returns the correct file size for uploaded files.

    """
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
