import re

import pytest

import audbackend
from audbackend.core.backend.base import Base


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
        backend.ls_dirs("/")
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


class DummyLsBackend(Base):
    """Dummy backend that only implements _ls to exercise Base._ls_dirs."""

    def __init__(self, listings):
        super().__init__("host", "repo")
        self._listings = listings

    def _ls(self, path):
        return self._listings.get(path, [])

    def _open(self):
        pass

    def _close(self):
        pass


def test_default_ls_dirs_root_and_nested():
    """Directories are correctly listed for root and nested paths."""
    backend = DummyLsBackend(
        {
            "/": [
                "/a/file1.txt",
                "/a/file2.txt",
                "/b/c/file3.txt",
                "/d/file4.txt",
            ],
            "/a/": [
                "/a/file1.txt",
                "/a/subdir/file4.txt",
            ],
            "/b/": [
                "/b/c/file3.txt",
            ],
        }
    )
    backend.open()
    assert sorted(backend.ls_dirs("/")) == ["a", "b", "d"]
    assert sorted(backend.ls_dirs("/a/")) == ["subdir"]
    assert sorted(backend.ls_dirs("/b/")) == ["c"]


def test_default_ls_dirs_derived_from_deeper_paths():
    """Immediate directory names are derived from deeper nested paths."""
    backend = DummyLsBackend(
        {
            "/": [
                "/a/file1.txt",
                "/a/b/c/file2.txt",
                "/x/y/z/file3",
            ],
            "/a/": [
                "/a/b/c/file2.txt",
            ],
        }
    )
    backend.open()
    assert sorted(backend.ls_dirs("/")) == ["a", "x"]
    assert backend.ls_dirs("/a/") == ["b"]


def test_default_ls_dirs_edge_cases():
    """Cover edge cases: non-matching prefix and path itself in _ls results."""
    backend = DummyLsBackend(
        {
            "/sub/": [
                "/sub/",
                "/other/file.txt",
                "/sub/a/file.txt",
            ],
        }
    )
    backend.open()
    assert backend.ls_dirs("/sub/") == ["a"]


def test_default_ls_dirs_raises_file_not_found():
    """_ls_dirs raises FileNotFoundError when _ls returns an empty list."""
    backend = DummyLsBackend(
        {
            "/empty/": [],
        }
    )
    backend.open()
    with pytest.raises(audbackend.BackendError):
        backend.ls_dirs("/empty/")
