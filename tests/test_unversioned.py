import datetime
import os
import platform
import re
import stat

import pytest

import audeer

import audbackend
from tests.conftest import create_file_tree


@pytest.mark.parametrize(
    "tree, archive, files, tmp_root, expected",
    [
        (  # empty
            ["file.ext", "dir/to/file.ext"],
            "/archive.zip",
            [],
            None,
            [],
        ),
        (  # single file
            ["file.ext", "dir/to/file.ext"],
            "/archive.zip",
            "file.ext",
            None,
            ["file.ext"],
        ),
        (  # list
            ["file.ext", "dir/to/file.ext"],
            "/archive.zip",
            ["file.ext"],
            None,
            ["file.ext"],
        ),
        (
            ["file.ext", "dir/to/file.ext"],
            "/archive.zip",
            ["file.ext", "dir/to/file.ext"],
            "tmp",
            ["file.ext", "dir/to/file.ext"],
        ),
        (  # all files
            ["file.ext", "dir/to/file.ext"],
            "/archive.zip",
            None,
            "tmp",
            ["dir/to/file.ext", "file.ext"],
        ),
        (  # tar.gz
            ["file.ext", "dir/to/file.ext"],
            "/archive.tar.gz",
            None,
            "tmp",
            ["dir/to/file.ext", "file.ext"],
        ),
    ],
)
def test_archive(tmpdir, filesystem, tree, archive, files, tmp_root, expected):
    r"""Test handling of archives.

    Args:
        tmpdir: tmpdir fixture
        filesystem: filesystem fixture
        tree: file tree in the source folder
        archive: name of archive on backend
        files: files to include from ``tree`` in archive
        tmp_root: temporary directory
            to be used by ``put_archive()`` and ``get_archive()``
        expected: expected files in destination folder
            after extracting the archive

    """
    backend = audbackend.Unversioned(filesystem)

    src_dir = audeer.mkdir(tmpdir, "src")
    dst_dir = audeer.mkdir(tmpdir, "dst")

    create_file_tree(src_dir, tree)

    if tmp_root is not None:
        tmp_root = audeer.path(tmpdir, tmp_root)

    if os.name == "nt":
        expected = [file.replace("/", os.sep) for file in expected]

    # If a tmp_root is given but does not exist,
    # put_archive() should fail
    if tmp_root is not None:
        audeer.rmdir(tmp_root)
        with pytest.raises(FileNotFoundError):
            backend.put_archive(src_dir, archive, files=files, tmp_root=tmp_root)
        audeer.mkdir(tmp_root)

    # Upload archive
    backend.put_archive(src_dir, archive, files=files, tmp_root=tmp_root)
    assert backend.exists(archive)
    # Repeated upload
    backend.put_archive(src_dir, archive, files=files, tmp_root=tmp_root)
    assert backend.exists(archive)

    # If a tmp_root is given but does not exist,
    # get_archive() should fail
    if tmp_root is not None:
        audeer.rmdir(tmp_root)
        with pytest.raises(FileNotFoundError):
            backend.get_archive(archive, dst_dir, tmp_root=tmp_root)
        audeer.mkdir(tmp_root)

    files_in_archive = backend.get_archive(archive, dst_dir, tmp_root=tmp_root)
    assert files_in_archive == expected


@pytest.mark.parametrize(
    "src_path, dst_path",
    [
        (
            "/file.ext",
            "/file.ext",
        ),
        (
            "/file.ext",
            "/dir/to/file.ext",
        ),
    ],
)
def test_copy(tmpdir, filesystem, src_path, dst_path):
    backend = audbackend.Unversioned(filesystem)

    local_path = audeer.path(tmpdir, "file.ext")
    audeer.touch(local_path)
    backend.put_file(local_path, src_path)

    # copy file

    if dst_path != src_path:
        assert not backend.exists(dst_path)
    backend.copy_file(src_path, dst_path)
    assert backend.exists(src_path)
    assert backend.exists(dst_path)

    # copy file again with different checksum

    with open(local_path, "w") as fp:
        fp.write("different checksum")

    assert audeer.md5(local_path) != backend.checksum(src_path)
    backend.put_file(local_path, src_path)
    assert audeer.md5(local_path) == backend.checksum(src_path)

    if dst_path != src_path:
        assert audeer.md5(local_path) != backend.checksum(dst_path)
    backend.copy_file(src_path, dst_path)
    assert audeer.md5(local_path) == backend.checksum(dst_path)


def test_errors(tmpdir, filesystem):
    backend = audbackend.Unversioned(filesystem)

    # Ensure we have one file and one archive published on the backend
    archive = "/archive.zip"
    local_file = "file.txt"
    local_path = audeer.path(audeer.path(tmpdir, local_file))
    with open(local_path, "w") as fp:
        fp.write("Text")
    local_folder = audeer.mkdir(audeer.path(tmpdir, "folder"))
    remote_file = f"/{local_file}"
    backend.put_file(local_path, remote_file)
    backend.put_archive(tmpdir, archive, files=[local_file])

    # Create local read-only file and folder
    file_read_only = audeer.touch(audeer.path(tmpdir, "read-only-file.txt"))
    os.chmod(file_read_only, stat.S_IRUSR)
    folder_read_only = audeer.mkdir(audeer.path(tmpdir, "read-only-folder"))
    os.chmod(folder_read_only, stat.S_IRUSR)

    # Invalid archive
    archive_invalid_type = "/archive.txt"
    error_invalid_archive = "You can only create a ZIP or TAR.GZ archive, not "

    # Invalid file names / versions and error messages
    file_invalid_path = "invalid/path.txt"
    error_invalid_path = re.escape(
        f"Invalid backend path '{file_invalid_path}', " f"must start with '/'."
    )
    file_sub_path = "/sub/"
    error_sub_path = re.escape(
        f"Invalid backend path '{file_sub_path}', " f"must not end on '/'."
    )
    file_invalid_char = "/invalid/char.txt?"
    error_invalid_char = re.escape(
        f"Invalid backend path '{file_invalid_char}', "
        f"does not match '[A-Za-z0-9/._-]+'."
    )
    error_backend = (
        "An exception was raised by the backend, "
        "please see stack trace for further information."
    )
    error_read_only_folder = (
        f"Permission denied: '{os.path.join(folder_read_only, local_file)}'"
    )
    error_read_only_file = f"Permission denied: '{file_read_only}'"
    if platform.system() == "Windows":
        error_is_a_folder = "Is a directory: "
    else:
        error_is_a_folder = f"Is a directory: '{local_folder}'"
    if platform.system() == "Windows":
        error_not_a_folder = "Not a directory: "
    else:
        error_not_a_folder = f"Not a directory: '{local_path}'"

    # --- checksum ---
    # `path` missing
    with pytest.raises(audbackend.BackendError, match=error_backend):
        backend.checksum("/missing.txt")
    # `path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.checksum(file_invalid_char)
    # `path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        backend.checksum(file_sub_path)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.checksum(file_invalid_char)

    # --- copy_file ---
    # `src_path` missing
    with pytest.raises(audbackend.BackendError, match=error_backend):
        backend.copy_file("/missing.txt", "/file.txt")
    # `src_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.copy_file(file_invalid_path, "/file.txt")
    # `src_path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        backend.copy_file(file_sub_path, "/file.txt")
    # `src_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.copy_file(file_invalid_char, "/file.txt")
    # `dst_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.copy_file("/file.txt", file_invalid_path)
    # `dst_path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        backend.copy_file("/file.txt", file_sub_path)
    # `dst_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.copy_file("/file.txt", file_invalid_char)

    # --- date ---
    # `path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.date(file_invalid_path)
    # `path` without trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        backend.date(file_sub_path)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.date(file_invalid_char)

    # --- exists ---
    # `path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.exists(file_invalid_path)
    # `path` without trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        backend.exists(file_sub_path)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.exists(file_invalid_char)

    # --- get_archive ---
    # `src_path` missing
    with pytest.raises(audbackend.BackendError, match=error_backend):
        backend.get_archive("/missing.txt", tmpdir)
    # `src_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.get_archive(file_invalid_path, tmpdir)
    # `src_path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        backend.get_archive(file_sub_path, tmpdir)
    # `src_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.get_archive(file_invalid_char, tmpdir)
    # `tmp_root` does not exist
    if platform.system() == "Windows":
        error_msg = "The system cannot find the path specified: 'non-existing..."
    else:
        error_msg = "No such file or directory: 'non-existing/..."
    with pytest.raises(FileNotFoundError, match=error_msg):
        backend.get_archive(archive, tmpdir, tmp_root="non-existing")
    # extension of `src_path` is not supported
    error_msg = "You can only extract ZIP and TAR.GZ files, ..."
    backend.put_file(
        audeer.touch(audeer.path(tmpdir, "archive.bad")),
        "/archive.bad",
    )
    with pytest.raises(RuntimeError, match=error_msg):
        backend.get_archive("/archive.bad", tmpdir)
    # `src_path` is a malformed archive
    error_msg = "Broken archive: "
    backend.put_file(
        audeer.touch(audeer.path(tmpdir, "malformed.zip")),
        "/malformed.zip",
    )
    with pytest.raises(RuntimeError, match=error_msg):
        backend.get_archive("/malformed.zip", tmpdir)
    # no write permissions to `dst_root`
    if not platform.system() == "Windows":
        # Currently we don't know how to provoke permission error on Windows
        with pytest.raises(PermissionError, match=error_read_only_folder):
            backend.get_archive(archive, folder_read_only)
    # `dst_root` is not a directory
    with pytest.raises(NotADirectoryError, match=error_not_a_folder):
        backend.get_archive(archive, local_path)

    # --- get_file ---
    # `src_path` missing
    with pytest.raises(audbackend.BackendError, match=error_backend):
        backend.get_file("/missing.txt", "missing.txt")
    # `src_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.get_file(file_invalid_path, tmpdir)
    # `src_path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        backend.get_file(file_sub_path, tmpdir)
    # `src_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.get_file(file_invalid_char, tmpdir)
    # no write permissions to `dst_path`
    if not platform.system() == "Windows":
        # Currently we don't know how to provoke permission error on Windows
        with pytest.raises(PermissionError, match=error_read_only_file):
            backend.get_file(remote_file, file_read_only)
        dst_path = audeer.path(folder_read_only, "file.txt")
        with pytest.raises(PermissionError, match=error_read_only_folder):
            backend.get_file(remote_file, dst_path)
    # `dst_path` is an existing folder
    with pytest.raises(IsADirectoryError, match=error_is_a_folder):
        backend.get_file(remote_file, local_folder)

    # --- join ---
    # joined path without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.join(file_invalid_path, local_file)
    # joined path contains invalid char
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.join(file_invalid_char, local_file)

    # --- ls ---
    # `path` does not exist
    with pytest.raises(audbackend.BackendError, match=error_backend):
        backend.ls("/missing/")
    backend.ls("/missing/", suppress_backend_errors=True)
    with pytest.raises(audbackend.BackendError, match=error_backend):
        backend.ls("/missing.txt")
    backend.ls("/missing.txt", suppress_backend_errors=True)
    remote_file_with_wrong_ext = audeer.replace_file_extension(
        remote_file,
        "missing",
    )
    with pytest.raises(audbackend.BackendError, match=error_backend):
        backend.ls(remote_file_with_wrong_ext)
    backend.ls(remote_file_with_wrong_ext, suppress_backend_errors=True)
    # joined path without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.ls(file_invalid_path)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.ls(file_invalid_char)

    # --- move_file ---
    # `src_path` missing
    with pytest.raises(audbackend.BackendError, match=error_backend):
        backend.move_file("/missing.txt", "/file.txt")
    # `src_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.move_file(file_invalid_path, "/file.txt")
    # `src_path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        backend.move_file(file_sub_path, "/file.txt")
    # `src_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.move_file(file_invalid_char, "/file.txt")
    # `dst_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.move_file("/file.txt", file_invalid_path)
    # `dst_path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        backend.move_file("/file.txt", file_sub_path)
    # `dst_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.move_file("/file.txt", file_invalid_char)

    # --- put_archive ---
    # `src_root` missing
    error_msg = "No such file or directory: ..."
    with pytest.raises(FileNotFoundError, match=error_msg):
        backend.put_archive(
            audeer.path(tmpdir, "/missing/"),
            archive,
            files=local_file,
        )
    # `src_root` is not a directory
    with pytest.raises(NotADirectoryError, match=error_not_a_folder):
        backend.put_archive(local_path, archive)
    # `files` missing
    error_msg = "No such file or directory: ..."
    with pytest.raises(FileNotFoundError, match=error_msg):
        backend.put_archive(tmpdir, archive, files="missing.txt")
    # `dst_path` no valid archive
    with pytest.raises(RuntimeError, match=error_invalid_archive):
        backend.put_archive(
            tmpdir,
            archive_invalid_type,
            files=local_file,
        )
    # `dst_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.put_archive(
            tmpdir,
            file_invalid_path,
            files=local_file,
        )
    # `dst_path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        backend.put_archive(
            tmpdir,
            file_sub_path,
            files=local_file,
        )
    # `dst_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.put_archive(
            tmpdir,
            file_invalid_char,
            files=local_file,
        )
    # extension of `dst_path` is not supported
    error_msg = "You can only create a ZIP or TAR.GZ archive, not ..."
    with pytest.raises(RuntimeError, match=error_msg):
        backend.put_archive(tmpdir, "/archive.bad", files=local_file)

    # --- put_file ---
    # `src_path` does not exists
    error_msg = "No such file or directory: ..."
    with pytest.raises(FileNotFoundError, match=error_msg):
        backend.put_file(
            audeer.path(tmpdir, "missing.txt"),
            remote_file,
        )
    # `src_path` is a folder
    with pytest.raises(IsADirectoryError, match=error_is_a_folder):
        backend.put_file(local_folder, remote_file)
    # `dst_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.put_file(local_path, file_invalid_path)
    # `dst_path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        backend.put_file(local_path, file_sub_path)
    # `dst_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.put_file(local_path, file_invalid_char)

    # --- remove_file ---
    # `path` does not exists
    with pytest.raises(audbackend.BackendError, match=error_backend):
        backend.remove_file("/missing.txt")
    # `path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.remove_file(file_invalid_path)
    # `path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        backend.remove_file(file_sub_path)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.remove_file(file_invalid_char)

    # --- split ---
    # `path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.split(file_invalid_path)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.split(file_invalid_char)


@pytest.mark.parametrize(
    "path",
    [
        "/file.txt",
        "/folder/test.txt",
    ],
)
def test_exists(tmpdir, filesystem, path):
    backend = audbackend.Unversioned(filesystem)

    src_path = audeer.path(tmpdir, "~")
    audeer.touch(src_path)

    assert not backend.exists(path)
    backend.put_file(src_path, path)
    assert backend.exists(path)


@pytest.mark.parametrize(
    "src_path, dst_path",
    [
        (
            "file",
            "/file",
        ),
        (
            "file.ext",
            "/file.ext",
        ),
        (
            os.path.join("dir", "to", "file.ext"),
            "/dir/to/file.ext",
        ),
        (
            os.path.join("dir.to", "file.ext"),
            "/dir.to/file.ext",
        ),
    ],
)
def test_file(tmpdir, filesystem, src_path, dst_path):
    backend = audbackend.Unversioned(filesystem)

    src_path = audeer.path(tmpdir, src_path)
    audeer.mkdir(os.path.dirname(src_path))
    audeer.touch(src_path)

    assert not backend.exists(dst_path)
    backend.put_file(src_path, dst_path)
    # operation will be skipped
    backend.put_file(src_path, dst_path)
    assert backend.exists(dst_path)

    backend.get_file(dst_path, src_path)
    assert os.path.exists(src_path)
    assert backend.checksum(dst_path) == audeer.md5(src_path)
    date = datetime.datetime.today().strftime("%Y-%m-%d")
    assert backend.date(dst_path) == date

    backend.remove_file(dst_path)
    assert not backend.exists(dst_path)


def test_ls(tmpdir, filesystem):
    backend = audbackend.Unversioned(filesystem)

    assert backend.ls() == []
    assert backend.ls("/") == []

    root = [
        "/file.bar",
        "/file.foo",
    ]
    root_foo = [
        "/file.foo",
    ]
    root_bar = [
        "/file.bar",
    ]
    sub = [
        "/sub/file.foo",
    ]
    hidden = [
        "/.sub/.file.foo",
    ]

    # create content

    tmp_file = os.path.join(tmpdir, "~")
    for path in root + sub + hidden:
        audeer.touch(tmp_file)
        backend.put_file(
            tmp_file,
            path,
        )

    # test

    for path, pattern, expected in [
        ("/", None, root + sub + hidden),
        ("/", "*.foo", root_foo + sub + hidden),
        ("/sub/", None, sub),
        ("/sub/", "*.bar", []),
        ("/sub/", "file.*", sub),
        ("/.sub/", None, hidden),
        ("/file.bar", None, root_bar),
        ("/sub/file.foo", None, sub),
        ("/sub/file.foo", "file.*", sub),
        ("/sub/file.foo", "*.bar", []),
        ("/.sub/.file.foo", None, hidden),
    ]:
        assert backend.ls(
            path,
            pattern=pattern,
        ) == sorted(expected)


@pytest.mark.parametrize(
    "src_path, dst_path",
    [
        (
            "/file.ext",
            "/file.ext",
        ),
        (
            "/file.ext",
            "/dir/to/file.ext",
        ),
    ],
)
def test_move(tmpdir, filesystem, src_path, dst_path):
    backend = audbackend.Unversioned(filesystem)

    local_path = audeer.path(tmpdir, "~")
    audeer.touch(local_path)

    # move file

    backend.put_file(local_path, src_path)

    if dst_path != src_path:
        assert not backend.exists(dst_path)
    backend.move_file(src_path, dst_path)
    if dst_path != src_path:
        assert not backend.exists(src_path)
    assert backend.exists(dst_path)

    # move file again with same checksum

    backend.put_file(local_path, src_path)

    backend.move_file(src_path, dst_path)
    if dst_path != src_path:
        assert not backend.exists(src_path)
    assert backend.exists(dst_path)

    # move file again with different checksum

    with open(local_path, "w") as fp:
        fp.write("different checksum")

    backend.put_file(local_path, src_path)

    if dst_path != src_path:
        assert audeer.md5(local_path) != backend.checksum(dst_path)
    backend.move_file(src_path, dst_path)
    assert audeer.md5(local_path) == backend.checksum(dst_path)


@pytest.mark.parametrize(
    "expected",
    ["audbackend.Unversioned(DirFileSystem)"],
)
def test_repr(filesystem, expected):
    backend = audbackend.Unversioned(filesystem)
    assert repr(backend) == expected
