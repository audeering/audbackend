import re

import pytest

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
