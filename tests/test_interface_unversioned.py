import datetime
import os
import platform
import random
import re
import stat
import string

import pytest

import audeer

import audbackend

from singlefolder import SingleFolder


# Backend-interface combinations to use in all tests
backend_interface_combinations = [
    (audbackend.backend.FileSystem, audbackend.interface.Unversioned),
    (audbackend.backend.Minio, audbackend.interface.Unversioned),
    (SingleFolder, audbackend.interface.Unversioned),
]
if hasattr(audbackend.backend, "Artifactory"):
    backend_interface_combinations.append(
        (audbackend.backend.Artifactory, audbackend.interface.Unversioned)
    )


@pytest.fixture(scope="function", autouse=False)
def tree(tmpdir, request):
    r"""Create file tree."""
    files = request.param
    paths = []

    for path in files:
        if os.name == "nt":
            path = path.replace("/", os.path.sep)
        if path.endswith(os.path.sep):
            path = audeer.path(tmpdir, path)
            path = audeer.mkdir(path)
            path = path + os.path.sep
            paths.append(path)
        else:
            path = audeer.path(tmpdir, path)
            audeer.mkdir(os.path.dirname(path))
            path = audeer.touch(path)
            paths.append(path)

    yield paths


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
    indirect=["tree"],
)
@pytest.mark.parametrize(
    "interface",
    backend_interface_combinations,
    indirect=True,
)
def test_archive(tmpdir, tree, archive, files, tmp_root, interface, expected):
    if tmp_root is not None:
        tmp_root = audeer.path(tmpdir, tmp_root)

    if os.name == "nt":
        expected = [file.replace("/", os.sep) for file in expected]

    # if a tmp_root is given but does not exist,
    # put_archive() should fail
    if tmp_root is not None:
        if os.path.exists(tmp_root):
            os.removedirs(tmp_root)
        with pytest.raises(FileNotFoundError):
            interface.put_archive(
                tmpdir,
                archive,
                files=files,
                tmp_root=tmp_root,
            )
        audeer.mkdir(tmp_root)

    interface.put_archive(
        tmpdir,
        archive,
        files=files,
        tmp_root=tmp_root,
    )
    # operation will be skipped
    interface.put_archive(
        tmpdir,
        archive,
        files=files,
        tmp_root=tmp_root,
    )
    assert interface.exists(archive)

    # if a tmp_root is given but does not exist,
    # get_archive() should fail
    if tmp_root is not None:
        if os.path.exists(tmp_root):
            os.removedirs(tmp_root)
        with pytest.raises(FileNotFoundError):
            interface.get_archive(
                archive,
                tmpdir,
                tmp_root=tmp_root,
            )
        audeer.mkdir(tmp_root)

    assert (
        interface.get_archive(
            archive,
            tmpdir,
            tmp_root=tmp_root,
        )
        == expected
    )


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
@pytest.mark.parametrize(
    "interface",
    backend_interface_combinations,
    indirect=True,
)
def test_copy(tmpdir, src_path, dst_path, interface):
    local_path = audeer.path(tmpdir, "~")
    audeer.touch(local_path)
    interface.put_file(local_path, src_path)

    # copy file

    if dst_path != src_path:
        assert not interface.exists(dst_path)
    interface.copy_file(src_path, dst_path)
    assert interface.exists(src_path)
    assert interface.exists(dst_path)

    # copy file again with different checksum

    with open(local_path, "w") as fp:
        fp.write("different checksum")

    assert audeer.md5(local_path) != interface.checksum(src_path)
    interface.put_file(local_path, src_path)
    assert audeer.md5(local_path) == interface.checksum(src_path)

    if dst_path != src_path:
        assert audeer.md5(local_path) != interface.checksum(dst_path)
    interface.copy_file(src_path, dst_path)
    assert audeer.md5(local_path) == interface.checksum(dst_path)

    # clean up

    interface.remove_file(src_path)
    if dst_path != src_path:
        interface.remove_file(dst_path)


@pytest.mark.parametrize(
    "interface",
    backend_interface_combinations,
    indirect=True,
)
def test_errors(tmpdir, interface):
    # Ensure we have one file and one archive published on the backend
    archive = "/archive.zip"
    local_file = "file.txt"
    local_path = audeer.touch(audeer.path(tmpdir, local_file))
    local_folder = audeer.mkdir(audeer.path(tmpdir, "folder"))
    remote_file = f"/{local_file}"
    interface.put_file(local_path, remote_file)
    interface.put_archive(tmpdir, archive, files=[local_file])

    # Create local read-only file and folder
    file_read_only = audeer.touch(audeer.path(tmpdir, "read-only-file.txt"))
    os.chmod(file_read_only, stat.S_IRUSR)
    folder_read_only = audeer.mkdir(audeer.path(tmpdir, "read-only-folder"))
    os.chmod(folder_read_only, stat.S_IRUSR)

    # Invalid file names / versions and error messages
    file_invalid_path = "invalid/path.txt"
    error_invalid_path = re.escape(
        f"Invalid backend path '{file_invalid_path}', must start with '/'."
    )
    file_sub_path = "/sub/"
    error_sub_path = re.escape(
        f"Invalid backend path '{file_sub_path}', must not end on '/'."
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
        interface.checksum("/missing.txt")
    # `path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_char):
        interface.checksum(file_invalid_char)
    # `path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        interface.checksum(file_sub_path)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        interface.checksum(file_invalid_char)

    # --- copy_file ---
    # `src_path` missing
    with pytest.raises(audbackend.BackendError, match=error_backend):
        interface.copy_file("/missing.txt", "/file.txt")
    # `src_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        interface.copy_file(file_invalid_path, "/file.txt")
    # `src_path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        interface.copy_file(file_sub_path, "/file.txt")
    # `src_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        interface.copy_file(file_invalid_char, "/file.txt")
    # `dst_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        interface.copy_file("/file.txt", file_invalid_path)
    # `dst_path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        interface.copy_file("/file.txt", file_sub_path)
    # `dst_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        interface.copy_file("/file.txt", file_invalid_char)

    # --- date ---
    # `path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        interface.date(file_invalid_path)
    # `path` without trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        interface.date(file_sub_path)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        interface.date(file_invalid_char)

    # --- exists ---
    # `path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        interface.exists(file_invalid_path)
    # `path` without trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        interface.exists(file_sub_path)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        interface.exists(file_invalid_char)

    # --- get_archive ---
    # `src_path` missing
    with pytest.raises(audbackend.BackendError, match=error_backend):
        interface.get_archive("/missing.txt", tmpdir)
    # `src_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        interface.get_archive(file_invalid_path, tmpdir)
    # `src_path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        interface.get_archive(file_sub_path, tmpdir)
    # `src_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        interface.get_archive(file_invalid_char, tmpdir)
    # `tmp_root` does not exist
    if platform.system() == "Windows":
        error_msg = "The system cannot find the path specified: 'non-existing..."
    else:
        error_msg = "No such file or directory: 'non-existing/..."
    with pytest.raises(FileNotFoundError, match=error_msg):
        interface.get_archive(archive, tmpdir, tmp_root="non-existing")
    # extension of `src_path` is not supported
    error_msg = "You can only extract ZIP and TAR files, ..."
    interface.put_file(
        audeer.touch(audeer.path(tmpdir, "archive.bad")),
        "/archive.bad",
    )
    with pytest.raises(RuntimeError, match=error_msg):
        interface.get_archive("/archive.bad", tmpdir)
    # `src_path` is a malformed archive
    error_msg = "Broken archive: "
    interface.put_file(
        audeer.touch(audeer.path(tmpdir, "malformed.zip")),
        "/malformed.zip",
    )
    with pytest.raises(RuntimeError, match=error_msg):
        interface.get_archive("/malformed.zip", tmpdir)
    # no write permissions to `dst_root`
    if not platform.system() == "Windows":
        # Currently we don't know how to provoke permission error on Windows
        with pytest.raises(PermissionError, match=error_read_only_folder):
            interface.get_archive(archive, folder_read_only)
    # `dst_root` is not a directory
    with pytest.raises(NotADirectoryError, match=error_not_a_folder):
        interface.get_archive(archive, local_path)

    # --- get_file ---
    # `src_path` missing
    with pytest.raises(audbackend.BackendError, match=error_backend):
        interface.get_file("/missing.txt", "missing.txt")
    # `src_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        interface.get_file(file_invalid_path, tmpdir)
    # `src_path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        interface.get_file(file_sub_path, tmpdir)
    # `src_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        interface.get_file(file_invalid_char, tmpdir)
    # no write permissions to `dst_path`
    if not platform.system() == "Windows":
        # Currently we don't know how to provoke permission error on Windows
        with pytest.raises(PermissionError, match=error_read_only_file):
            interface.get_file(remote_file, file_read_only)
        dst_path = audeer.path(folder_read_only, "file.txt")
        with pytest.raises(PermissionError, match=error_read_only_folder):
            interface.get_file(remote_file, dst_path)
    # `dst_path` is an existing folder
    with pytest.raises(IsADirectoryError, match=error_is_a_folder):
        interface.get_file(remote_file, local_folder)

    # --- join ---
    # joined path without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        interface.join(file_invalid_path, local_file)
    # joined path contains invalid char
    with pytest.raises(ValueError, match=error_invalid_char):
        interface.join(file_invalid_char, local_file)

    # --- ls ---
    # `path` does not exist
    with pytest.raises(audbackend.BackendError, match=error_backend):
        interface.ls("/missing/")
    interface.ls("/missing/", suppress_backend_errors=True)
    with pytest.raises(audbackend.BackendError, match=error_backend):
        interface.ls("/missing.txt")
    interface.ls("/missing.txt", suppress_backend_errors=True)
    remote_file_with_wrong_ext = audeer.replace_file_extension(
        remote_file,
        "missing",
    )
    with pytest.raises(audbackend.BackendError, match=error_backend):
        interface.ls(remote_file_with_wrong_ext)
    interface.ls(remote_file_with_wrong_ext, suppress_backend_errors=True)
    # joined path without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        interface.ls(file_invalid_path)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        interface.ls(file_invalid_char)

    # --- move_file ---
    # `src_path` missing
    with pytest.raises(audbackend.BackendError, match=error_backend):
        interface.move_file("/missing.txt", "/file.txt")
    # `src_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        interface.move_file(file_invalid_path, "/file.txt")
    # `src_path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        interface.move_file(file_sub_path, "/file.txt")
    # `src_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        interface.move_file(file_invalid_char, "/file.txt")
    # `dst_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        interface.move_file("/file.txt", file_invalid_path)
    # `dst_path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        interface.move_file("/file.txt", file_sub_path)
    # `dst_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        interface.move_file("/file.txt", file_invalid_char)

    # --- owner ---
    # `path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        interface.owner(file_invalid_path)
    # `path` without trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        interface.owner(file_sub_path)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        interface.owner(file_invalid_char)

    # --- put_archive ---
    # `src_root` missing
    error_msg = "No such file or directory: ..."
    with pytest.raises(FileNotFoundError, match=error_msg):
        interface.put_archive(
            audeer.path(tmpdir, "/missing/"),
            archive,
            files=local_file,
        )
    # `src_root` is not a directory
    with pytest.raises(NotADirectoryError, match=error_not_a_folder):
        interface.put_archive(local_path, archive)
    # `files` missing
    error_msg = "No such file or directory: ..."
    with pytest.raises(FileNotFoundError, match=error_msg):
        interface.put_archive(tmpdir, archive, files="missing.txt")
    # `dst_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        interface.put_archive(
            tmpdir,
            file_invalid_path,
            files=local_file,
        )
    # `dst_path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        interface.put_archive(
            tmpdir,
            file_sub_path,
            files=local_file,
        )
    # `dst_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        interface.put_archive(
            tmpdir,
            file_invalid_char,
            files=local_file,
        )
    # extension of `dst_path` is not supported
    error_msg = "Unsupported archive format. Supported formats: ..."
    with pytest.raises(RuntimeError, match=error_msg):
        interface.put_archive(tmpdir, "/archive.bad", files=local_file)

    # --- put_file ---
    # `src_path` does not exists
    error_msg = "No such file or directory: ..."
    with pytest.raises(FileNotFoundError, match=error_msg):
        interface.put_file(
            audeer.path(tmpdir, "missing.txt"),
            remote_file,
        )
    # `src_path` is a folder
    with pytest.raises(IsADirectoryError, match=error_is_a_folder):
        interface.put_file(local_folder, remote_file)
    # `dst_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        interface.put_file(local_path, file_invalid_path)
    # `dst_path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        interface.put_file(local_path, file_sub_path)
    # `dst_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        interface.put_file(local_path, file_invalid_char)

    # --- remove_file ---
    # `path` does not exists
    with pytest.raises(audbackend.BackendError, match=error_backend):
        interface.remove_file("/missing.txt")
    # `path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        interface.remove_file(file_invalid_path)
    # `path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        interface.remove_file(file_sub_path)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        interface.remove_file(file_invalid_char)

    # --- split ---
    # `path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        interface.split(file_invalid_path)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        interface.split(file_invalid_char)


@pytest.mark.parametrize(
    "path",
    [
        "/file.txt",
        "/folder/test.txt",
    ],
)
@pytest.mark.parametrize(
    "interface",
    backend_interface_combinations,
    indirect=True,
)
def test_exists(tmpdir, path, interface):
    src_path = audeer.path(tmpdir, "~")
    audeer.touch(src_path)

    assert not interface.exists(path)
    interface.put_file(src_path, path)
    assert interface.exists(path)


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
@pytest.mark.parametrize(
    "interface, owner",
    [
        ((backend, interface), backend)
        for backend, interface in backend_interface_combinations
    ],
    indirect=True,
)
def test_file(tmpdir, src_path, dst_path, owner, interface):
    src_path = audeer.path(tmpdir, src_path)
    audeer.mkdir(os.path.dirname(src_path))
    audeer.touch(src_path)

    assert not interface.exists(dst_path)
    interface.put_file(src_path, dst_path)
    # operation will be skipped
    interface.put_file(src_path, dst_path)
    assert interface.exists(dst_path)

    # Download with already existing src_path
    interface.get_file(dst_path, src_path)
    assert os.path.exists(src_path)
    assert interface.checksum(dst_path) == audeer.md5(src_path)
    assert interface.owner(dst_path) == owner
    date = datetime.datetime.today().strftime("%Y-%m-%d")
    assert interface.date(dst_path) == date

    # Repeat, but remove src_path first
    os.remove(src_path)
    assert not os.path.exists(src_path)
    interface.get_file(dst_path, src_path)
    assert os.path.exists(src_path)
    assert interface.checksum(dst_path) == audeer.md5(src_path)
    assert interface.owner(dst_path) == owner
    date = datetime.datetime.today().strftime("%Y-%m-%d")
    assert interface.date(dst_path) == date

    interface.remove_file(dst_path)
    assert not interface.exists(dst_path)


@pytest.mark.parametrize(
    "interface",
    backend_interface_combinations,
    indirect=True,
)
def test_ls(tmpdir, interface):
    assert interface.ls() == []
    assert interface.ls("/") == []

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
        interface.put_file(
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
        assert interface.ls(
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
@pytest.mark.parametrize(
    "interface",
    backend_interface_combinations,
    indirect=True,
)
def test_move(tmpdir, src_path, dst_path, interface):
    local_path = audeer.path(tmpdir, "~")
    audeer.touch(local_path)

    # move file

    interface.put_file(local_path, src_path)

    if dst_path != src_path:
        assert not interface.exists(dst_path)
    interface.move_file(src_path, dst_path)
    if dst_path != src_path:
        assert not interface.exists(src_path)
    assert interface.exists(dst_path)

    # move file again with same checksum

    interface.put_file(local_path, src_path)

    interface.move_file(src_path, dst_path)
    if dst_path != src_path:
        assert not interface.exists(src_path)
    assert interface.exists(dst_path)

    # move file again with different checksum

    with open(local_path, "w") as fp:
        fp.write("different checksum")

    interface.put_file(local_path, src_path)

    if dst_path != src_path:
        assert audeer.md5(local_path) != interface.checksum(dst_path)
    interface.move_file(src_path, dst_path)
    assert audeer.md5(local_path) == interface.checksum(dst_path)

    # clean up

    interface.remove_file(dst_path)


def test_repr():
    interface = audbackend.interface.Unversioned(
        audbackend.backend.FileSystem("host", "repo")
    )
    assert interface.__repr__() == (
        "audbackend.interface.Unversioned("
        "audbackend.backend.FileSystem('host', 'repo')"
        ")"
    )


def test_validate(tmpdir):
    class BadChecksumBackend(audbackend.backend.FileSystem):
        r"""Return random checksum."""

        def _checksum(
            self,
            path: str,
        ) -> str:
            return "".join(
                random.choices(
                    string.ascii_uppercase + string.digits,
                    k=33,
                )
            )

    path = audeer.touch(tmpdir, "~.txt")
    error_msg = "Execution is interrupted because"

    audbackend.backend.FileSystem.create(tmpdir, "repo")
    file_system_backend = audbackend.backend.FileSystem(tmpdir, "repo")
    file_system_backend.open()
    bad_checksum_backend = BadChecksumBackend(tmpdir, "repo")
    bad_checksum_backend.open()

    interface = audbackend.interface.Unversioned(file_system_backend)
    interface_bad = audbackend.interface.Unversioned(bad_checksum_backend)

    with pytest.raises(InterruptedError, match=error_msg):
        interface_bad.put_file(path, "/remote.txt", validate=True)
    assert not interface.exists("/remote.txt")
    interface.put_file(path, "/remote.txt", validate=True)
    assert interface.exists("/remote.txt")

    local_file = audeer.path(tmpdir, "local.txt")
    with pytest.raises(InterruptedError, match=error_msg):
        interface_bad.get_file("/remote.txt", local_file, validate=True)
    assert not os.path.exists(local_file)
    interface.get_file("/remote.txt", local_file, validate=True)
    assert os.path.exists(local_file)

    with pytest.raises(InterruptedError, match=error_msg):
        interface_bad.copy_file("/remote.txt", "/copy.txt", validate=True)
    assert not interface.exists("/copy.txt")
    interface.copy_file("/remote.txt", "/copy.txt", validate=True)
    assert interface.exists("/copy.txt")

    with pytest.raises(InterruptedError, match=error_msg):
        interface_bad.move_file("/remote.txt", "/move.txt", validate=True)
    assert not interface.exists("/move.txt")
    assert interface.exists("/remote.txt")
    interface.move_file("/remote.txt", "/move.txt", validate=True)
    assert interface.exists("/move.txt")
    assert not interface.exists("/remote.txt")

    with pytest.raises(InterruptedError, match=error_msg):
        interface_bad.put_archive(tmpdir, "/remote.zip", validate=True)
    assert not interface.exists("/remote.zip")
    interface.put_archive(".", "/remote.zip", validate=True)
    assert interface.exists("/remote.zip")

    dst_root = os.path.join(tmpdir, "extract")
    with pytest.raises(InterruptedError, match=error_msg):
        interface_bad.get_archive("/remote.zip", dst_root, validate=True)
    assert not os.path.exists(dst_root)
    interface.get_archive("/remote.zip", dst_root, validate=True)
    assert os.path.exists(dst_root)
