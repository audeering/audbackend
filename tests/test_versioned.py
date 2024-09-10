import datetime
import os
import platform
import re
import stat

from conftest import create_file_tree
import pytest

import audeer

import audbackend


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
    backend = audbackend.Versioned(filesystem)
    version = "1.0.0"

    src_dir = audeer.mkdir(tmpdir, "src")
    dst_dir = audeer.mkdir(tmpdir, "dst")

    create_file_tree(src_dir, tree)

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
            backend.put_archive(
                src_dir,
                archive,
                version,
                files=files,
                tmp_root=tmp_root,
            )
        audeer.mkdir(tmp_root)

    backend.put_archive(
        src_dir,
        archive,
        version,
        files=files,
        tmp_root=tmp_root,
    )
    # operation will be skipped
    backend.put_archive(
        src_dir,
        archive,
        version,
        files=files,
        tmp_root=tmp_root,
    )
    assert backend.exists(archive, version)

    # if a tmp_root is given but does not exist,
    # get_archive() should fail
    if tmp_root is not None:
        if os.path.exists(tmp_root):
            os.removedirs(tmp_root)
        with pytest.raises(FileNotFoundError):
            backend.get_archive(
                archive,
                dst_dir,
                version,
                tmp_root=tmp_root,
            )
        audeer.mkdir(tmp_root)

    assert (
        backend.get_archive(
            archive,
            dst_dir,
            version,
            tmp_root=tmp_root,
        )
        == expected
    )


@pytest.mark.parametrize(
    "src_path, src_versions, dst_path",
    [
        (
            "/file.ext",
            ["1.0.0", "2.0.0"],
            "/file.ext",
        ),
        (
            "/file.ext",
            ["1.0.0", "2.0.0"],
            "/dir/to/file.ext",
        ),
    ],
)
@pytest.mark.parametrize("version", [None, "2.0.0"])
def test_copy(tmpdir, filesystem, src_path, src_versions, dst_path, version):
    backend = audbackend.Versioned(filesystem)

    if version is None:
        dst_versions = src_versions
    else:
        dst_versions = [version]

    local_path = audeer.path(tmpdir, "~")
    audeer.touch(local_path)
    for v in src_versions:
        backend.put_file(local_path, src_path, v)

    # copy file

    if dst_path != src_path:
        for v in dst_versions:
            assert not backend.exists(dst_path, v)
    backend.copy_file(src_path, dst_path, version=version)
    for v in src_versions:
        assert backend.exists(src_path, v)
    for v in dst_versions:
        assert backend.exists(dst_path, v)

    # copy file again with different checksum

    with open(local_path, "w") as fp:
        fp.write("different checksum")

    for v in src_versions:
        assert audeer.md5(local_path) != backend.checksum(src_path, v)
        backend.put_file(local_path, src_path, v)
        assert audeer.md5(local_path) == backend.checksum(src_path, v)

    if dst_path != src_path:
        for v in dst_versions:
            assert audeer.md5(local_path) != backend.checksum(dst_path, v)
    backend.copy_file(src_path, dst_path, version=version)
    for v in dst_versions:
        assert audeer.md5(local_path) == backend.checksum(dst_path, v)

    # clean up

    for v in src_versions:
        backend.remove_file(src_path, v)
    if dst_path != src_path:
        for v in dst_versions:
            backend.remove_file(dst_path, v)


def test_errors(tmpdir, filesystem):
    backend = audbackend.Versioned(filesystem)
    # Ensure we have one file and one archive published on the backend
    archive = "/archive.zip"
    local_file = "file.txt"
    local_path = audeer.path(audeer.path(tmpdir, local_file))
    with open(local_path, "w") as fp:
        fp.write("Text")
    local_folder = audeer.mkdir(audeer.path(tmpdir, "folder"))
    remote_file = f"/{local_file}"
    version = "1.0.0"
    backend.put_file(local_path, remote_file, version)
    backend.put_archive(tmpdir, archive, version, files=[local_file])

    # Create local read-only file and folder
    file_read_only = audeer.touch(audeer.path(tmpdir, "read-only-file.txt"))
    os.chmod(file_read_only, stat.S_IRUSR)
    folder_read_only = audeer.mkdir(audeer.path(tmpdir, "read-only-folder"))
    os.chmod(folder_read_only, stat.S_IRUSR)

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
    empty_version = ""
    error_empty_version = "Version must not be empty."
    invalid_version = "1.0.?"
    error_invalid_version = re.escape(
        f"Invalid version '{invalid_version}', " f"does not match '[A-Za-z0-9._-]+'."
    )
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
        backend.checksum("/missing.txt", version)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.checksum(file_invalid_char, version)
    # `path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.checksum(file_invalid_char, version)
    # `path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        backend.checksum(file_sub_path, version)
    # invalid version
    with pytest.raises(ValueError, match=error_empty_version):
        backend.checksum(remote_file, empty_version)
    with pytest.raises(ValueError, match=error_invalid_version):
        backend.checksum(remote_file, invalid_version)

    # --- copy_file ---
    # `src_path` missing
    with pytest.raises(audbackend.BackendError, match=error_backend):
        backend.copy_file("/missing.txt", "/file.txt")
    # `src_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.copy_file(file_invalid_path, "/file.txt")
    # `src_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.copy_file(file_invalid_char, "/file.txt")
    # `src_path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        backend.copy_file(file_sub_path, "/file.txt")
    # `dst_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.copy_file("/file.txt", file_invalid_path)
    # `dst_path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        backend.copy_file("/file.txt", file_sub_path)
    # `dst_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.copy_file("/file.txt", file_invalid_char)
    # invalid version
    with pytest.raises(ValueError, match=error_empty_version):
        backend.copy_file(remote_file, "/file.txt", version=empty_version)

    # --- date ---
    # `path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.date(file_invalid_path, version)
    # `path` without trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        backend.date(file_sub_path, version)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.date(file_invalid_char, version)
    # invalid version
    with pytest.raises(ValueError, match=error_empty_version):
        backend.date(remote_file, empty_version)
    with pytest.raises(ValueError, match=error_invalid_version):
        backend.date(remote_file, invalid_version)

    # --- exists ---
    # `path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.exists(file_invalid_path, version)
    # `path` without trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        backend.exists(file_sub_path, version)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.exists(file_invalid_char, version)
    # invalid version
    with pytest.raises(ValueError, match=error_empty_version):
        backend.exists(remote_file, empty_version)
    with pytest.raises(ValueError, match=error_invalid_version):
        backend.exists(remote_file, invalid_version)

    # --- get_archive ---
    # `src_path` missing
    with pytest.raises(audbackend.BackendError, match=error_backend):
        backend.get_archive("/missing.txt", tmpdir, version)
    # `src_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.get_archive(file_invalid_path, tmpdir, version)
    # `src_path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        backend.get_archive(file_sub_path, tmpdir, version)
    # `src_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.get_archive(file_invalid_char, tmpdir, version)
    # invalid version
    with pytest.raises(ValueError, match=error_empty_version):
        backend.get_archive(archive, tmpdir, empty_version)
    with pytest.raises(ValueError, match=error_invalid_version):
        backend.get_archive(archive, tmpdir, invalid_version)
    # `tmp_root` does not exist
    if platform.system() == "Windows":
        error_msg = "The system cannot find the path specified: 'non-existing..."
    else:
        error_msg = "No such file or directory: 'non-existing/..."
    with pytest.raises(FileNotFoundError, match=error_msg):
        backend.get_archive(
            archive,
            tmpdir,
            version,
            tmp_root="non-existing",
        )
    # extension of `src_path` is not supported
    error_msg = "You can only extract ZIP and TAR.GZ files, ..."
    backend.put_file(
        audeer.touch(audeer.path(tmpdir, "archive.bad")),
        "/archive.bad",
        version,
    )
    with pytest.raises(RuntimeError, match=error_msg):
        backend.get_archive("/archive.bad", tmpdir, version)
    # `src_path` is a malformed archive
    error_msg = "Broken archive: "
    backend.put_file(
        audeer.touch(audeer.path(tmpdir, "malformed.zip")),
        "/malformed.zip",
        version,
    )
    with pytest.raises(RuntimeError, match=error_msg):
        backend.get_archive("/malformed.zip", tmpdir, version)
    # no write permissions to `dst_root`
    if not platform.system() == "Windows":
        # Currently we don't know how to provoke permission error on Windows
        with pytest.raises(PermissionError, match=error_read_only_folder):
            backend.get_archive(archive, folder_read_only, version)
    # `dst_root` is not a directory
    with pytest.raises(NotADirectoryError, match=error_not_a_folder):
        backend.get_archive(archive, local_path, version)

    # --- get_file ---
    # `src_path` missing
    with pytest.raises(audbackend.BackendError, match=error_backend):
        backend.get_file("/missing.txt", "missing.txt", version)
    # `src_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.get_file(file_invalid_path, tmpdir, version)
    # `src_path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        backend.get_file(file_sub_path, tmpdir, version)
    # `src_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.get_file(file_invalid_char, tmpdir, version)
    # invalid version
    with pytest.raises(ValueError, match=error_empty_version):
        backend.get_file(remote_file, local_file, empty_version)
    with pytest.raises(ValueError, match=error_invalid_version):
        backend.get_file(remote_file, local_file, invalid_version)
    # no write permissions to `dst_path`
    if not platform.system() == "Windows":
        # Currently we don't know how to provoke permission error on Windows
        with pytest.raises(PermissionError, match=error_read_only_file):
            backend.get_file(remote_file, file_read_only, version)
        dst_path = audeer.path(folder_read_only, "file.txt")
        with pytest.raises(PermissionError, match=error_read_only_folder):
            backend.get_file(remote_file, dst_path, version)
    # `dst_path` is an existing folder
    with pytest.raises(IsADirectoryError, match=error_is_a_folder):
        backend.get_file(remote_file, local_folder, version)

    # --- join ---
    # joined path without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.join(file_invalid_path, local_file)
    # joined path contains invalid char
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.join(file_invalid_char, local_file)

    # --- latest_version ---
    # `path` missing
    with pytest.raises(audbackend.BackendError, match=error_backend):
        backend.latest_version("/missing.txt")
    # path without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.latest_version(file_invalid_path)
    # path with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        backend.latest_version(file_sub_path)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.latest_version(file_invalid_char)

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
    # invalid version
    with pytest.raises(ValueError, match=error_empty_version):
        backend.move_file(remote_file, "/file.txt", version=empty_version)

    # --- put_archive ---
    # `src_root` missing
    error_msg = "No such file or directory: ..."
    with pytest.raises(FileNotFoundError, match=error_msg):
        backend.put_archive(
            audeer.path(tmpdir, "/missing/"),
            archive,
            version,
            files=local_file,
        )
    # `src_root` is not a directory
    with pytest.raises(NotADirectoryError, match=error_not_a_folder):
        backend.put_archive(local_path, archive, version)
    # `files` missing
    error_msg = "No such file or directory: ..."
    with pytest.raises(FileNotFoundError, match=error_msg):
        backend.put_archive(tmpdir, archive, version, files="missing.txt")
    # `dst_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.put_archive(
            tmpdir,
            file_invalid_path,
            version,
            files=local_file,
        )
    # `dst_path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        backend.put_archive(
            tmpdir,
            file_sub_path,
            version,
            files=local_file,
        )
    # `dst_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.put_archive(
            tmpdir,
            file_invalid_char,
            version,
            files=local_file,
        )
    # invalid version
    with pytest.raises(ValueError, match=error_empty_version):
        backend.put_archive(tmpdir, archive, empty_version)
    with pytest.raises(ValueError, match=error_invalid_version):
        backend.put_archive(tmpdir, archive, invalid_version)
    # extension of `dst_path` is not supported
    error_msg = "You can only create a ZIP or TAR.GZ archive, not ..."
    with pytest.raises(RuntimeError, match=error_msg):
        backend.put_archive(
            tmpdir,
            "/archive.bad",
            version,
            files=local_file,
        )

    # --- put_file ---
    # `src_path` does not exists
    error_msg = "No such file or directory: ..."
    with pytest.raises(FileNotFoundError, match=error_msg):
        backend.put_file(
            audeer.path(tmpdir, "missing.txt"),
            remote_file,
            version,
        )
    # `src_path` is a folder
    with pytest.raises(IsADirectoryError, match=error_is_a_folder):
        backend.put_file(local_folder, remote_file, version)
    # `dst_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.put_file(local_path, file_invalid_path, version)
    # `dst_path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        backend.put_file(local_path, file_sub_path, version)
    # `dst_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.put_file(local_path, file_invalid_char, version)
    # invalid version
    with pytest.raises(ValueError, match=error_empty_version):
        backend.put_file(local_path, remote_file, empty_version)
    with pytest.raises(ValueError, match=error_invalid_version):
        backend.put_file(local_path, remote_file, invalid_version)

    # --- remove_file ---
    # `path` does not exists
    with pytest.raises(audbackend.BackendError, match=error_backend):
        backend.remove_file("/missing.txt", version)
    # `path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.remove_file(file_invalid_path, version)
    # `path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        backend.remove_file(file_sub_path, version)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.remove_file(file_invalid_char, version)
    # invalid version
    with pytest.raises(ValueError, match=error_empty_version):
        backend.remove_file(remote_file, empty_version)
    with pytest.raises(ValueError, match=error_invalid_version):
        backend.remove_file(remote_file, invalid_version)

    # --- split ---
    # `path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.split(file_invalid_path)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.split(file_invalid_char)

    # --- versions ---
    # `path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.versions(file_invalid_path)
    # `path` with trailing '/'
    with pytest.raises(ValueError, match=error_sub_path):
        backend.versions(file_sub_path)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.versions(file_invalid_char)


@pytest.mark.parametrize(
    "path, version",
    [
        ("/file.txt", "1.0.0"),
        ("/folder/test.txt", "1.0.0"),
    ],
)
def test_exists(tmpdir, filesystem, path, version):
    backend = audbackend.Versioned(filesystem)
    src_path = audeer.path(tmpdir, "~")
    audeer.touch(src_path)

    assert not backend.exists(path, version)
    backend.put_file(src_path, path, version)
    assert backend.exists(path, version)


@pytest.mark.parametrize(
    "src_path, dst_path, version",
    [
        (
            "file",
            "/file",
            "1.0.0",
        ),
        (
            "file.ext",
            "/file.ext",
            "1.0.0",
        ),
        (
            os.path.join("dir", "to", "file.ext"),
            "/dir/to/file.ext",
            "1.0.0",
        ),
        (
            os.path.join("dir.to", "file.ext"),
            "/dir.to/file.ext",
            "1.0.0",
        ),
    ],
)
def test_file(tmpdir, filesystem, src_path, dst_path, version):
    backend = audbackend.Versioned(filesystem)
    src_path = audeer.path(tmpdir, src_path)
    audeer.mkdir(os.path.dirname(src_path))
    audeer.touch(src_path)

    assert not backend.exists(dst_path, version)
    backend.put_file(src_path, dst_path, version)
    # operation will be skipped
    backend.put_file(src_path, dst_path, version)
    assert backend.exists(dst_path, version)

    backend.get_file(dst_path, src_path, version)
    assert os.path.exists(src_path)
    assert backend.checksum(dst_path, version) == audeer.md5(src_path)
    date = datetime.datetime.today().strftime("%Y-%m-%d")
    assert backend.date(dst_path, version) == date

    backend.remove_file(dst_path, version)
    assert not backend.exists(dst_path, version)


@pytest.mark.parametrize(
    "files",
    [
        [
            ("/file.bar", "1.0.0"),
            ("/file.bar", "2.0.0"),
            ("/file.foo", "1.0.0"),
            ("/sub/file.foo", "1.0.0"),
            ("/sub/file.foo", "2.0.0"),
            ("/sub/sub.ext", "1.0.0"),
            ("/sub/sub/sub.ext", "1.0.0"),
            ("/.sub/.file.foo", "1.0.0"),
            ("/.sub/.file.foo", "2.0.0"),
        ],
    ],
)
@pytest.mark.parametrize(
    "path, latest, pattern, expected",
    [
        (
            "/",
            False,
            None,
            [
                ("/file.bar", "1.0.0"),
                ("/file.bar", "2.0.0"),
                ("/file.foo", "1.0.0"),
                ("/sub/file.foo", "1.0.0"),
                ("/sub/file.foo", "2.0.0"),
                ("/sub/sub.ext", "1.0.0"),
                ("/sub/sub/sub.ext", "1.0.0"),
                ("/.sub/.file.foo", "1.0.0"),
                ("/.sub/.file.foo", "2.0.0"),
            ],
        ),
        (
            "/",
            True,
            None,
            [
                ("/file.bar", "2.0.0"),
                ("/file.foo", "1.0.0"),
                ("/sub/file.foo", "2.0.0"),
                ("/sub/sub.ext", "1.0.0"),
                ("/sub/sub/sub.ext", "1.0.0"),
                ("/.sub/.file.foo", "2.0.0"),
            ],
        ),
        (
            "/",
            False,
            "*.foo",
            [
                ("/file.foo", "1.0.0"),
                ("/sub/file.foo", "1.0.0"),
                ("/sub/file.foo", "2.0.0"),
                ("/.sub/.file.foo", "1.0.0"),
                ("/.sub/.file.foo", "2.0.0"),
            ],
        ),
        (
            "/",
            True,
            "*.foo",
            [
                ("/file.foo", "1.0.0"),
                ("/sub/file.foo", "2.0.0"),
                ("/.sub/.file.foo", "2.0.0"),
            ],
        ),
        (
            "/sub/",
            False,
            None,
            [
                ("/sub/file.foo", "1.0.0"),
                ("/sub/file.foo", "2.0.0"),
                ("/sub/sub.ext", "1.0.0"),
                ("/sub/sub/sub.ext", "1.0.0"),
            ],
        ),
        (
            "/sub/",
            True,
            None,
            [
                ("/sub/file.foo", "2.0.0"),
                ("/sub/sub.ext", "1.0.0"),
                ("/sub/sub/sub.ext", "1.0.0"),
            ],
        ),
        (
            "/sub/",
            False,
            "*.bar",
            [],
        ),
        (
            "/sub/",
            True,
            "*.bar",
            [],
        ),
        (
            "/sub/",
            False,
            "file.*",
            [
                ("/sub/file.foo", "1.0.0"),
                ("/sub/file.foo", "2.0.0"),
            ],
        ),
        (
            "/sub/",
            True,
            "file.*",
            [
                ("/sub/file.foo", "2.0.0"),
            ],
        ),
        (
            "/.sub/",
            False,
            None,
            [
                ("/.sub/.file.foo", "1.0.0"),
                ("/.sub/.file.foo", "2.0.0"),
            ],
        ),
        (
            "/.sub/",
            True,
            None,
            [
                ("/.sub/.file.foo", "2.0.0"),
            ],
        ),
        (
            "/file.bar",
            False,
            None,
            [
                ("/file.bar", "1.0.0"),
                ("/file.bar", "2.0.0"),
            ],
        ),
        (
            "/file.bar",
            True,
            None,
            [
                ("/file.bar", "2.0.0"),
            ],
        ),
        (
            "/sub/file.foo",
            False,
            None,
            [
                ("/sub/file.foo", "1.0.0"),
                ("/sub/file.foo", "2.0.0"),
            ],
        ),
        (
            "/sub/file.foo",
            True,
            None,
            [
                ("/sub/file.foo", "2.0.0"),
            ],
        ),
        (
            "/sub/file.foo",
            False,
            "file.*",
            [
                ("/sub/file.foo", "1.0.0"),
                ("/sub/file.foo", "2.0.0"),
            ],
        ),
        (
            "/sub/file.foo",
            True,
            "file.*",
            [
                ("/sub/file.foo", "2.0.0"),
            ],
        ),
        (
            "/sub/file.foo",
            False,
            "*.bar",
            [],
        ),
        (
            "/sub/file.foo",
            True,
            "*.bar",
            [],
        ),
        (
            "/.sub/.file.foo",
            False,
            None,
            [
                ("/.sub/.file.foo", "1.0.0"),
                ("/.sub/.file.foo", "2.0.0"),
            ],
        ),
        (
            "/.sub/.file.foo",
            True,
            None,
            [
                ("/.sub/.file.foo", "2.0.0"),
            ],
        ),
        (
            "/sub/sub/",
            False,
            None,
            [
                ("/sub/sub/sub.ext", "1.0.0"),
            ],
        ),
        (
            "/sub/sub/",
            True,
            None,
            [
                ("/sub/sub/sub.ext", "1.0.0"),
            ],
        ),
    ],
)
def test_ls(tmpdir, filesystem, files, path, latest, pattern, expected):
    backend = audbackend.Versioned(filesystem)
    assert backend.ls() == []
    assert backend.ls("/") == []

    # create content
    tmp_file = audeer.touch(tmpdir, "~")
    for file_path, file_version in files:
        backend.put_file(tmp_file, file_path, file_version)

    # test
    assert backend.ls(
        path,
        latest_version=latest,
        pattern=pattern,
    ) == sorted(expected)


@pytest.mark.parametrize(
    "src_path, src_versions, dst_path",
    [
        (
            "/file.ext",
            ["1.0.0", "2.0.0"],
            "/file.ext",
        ),
        (
            "/file.ext",
            ["1.0.0", "2.0.0"],
            "/dir/to/file.ext",
        ),
    ],
)
@pytest.mark.parametrize("version", [None, "2.0.0"])
def test_move(tmpdir, filesystem, src_path, src_versions, dst_path, version):
    backend = audbackend.Versioned(filesystem)
    if version is None:
        dst_versions = src_versions
    else:
        dst_versions = [version]

    local_path = audeer.path(tmpdir, "~")
    audeer.touch(local_path)

    # move file

    for v in src_versions:
        backend.put_file(local_path, src_path, v)

    if dst_path != src_path:
        for v in dst_versions:
            assert not backend.exists(dst_path, v)
    backend.move_file(src_path, dst_path, version=version)
    if dst_path != src_path:
        for v in dst_versions:
            assert not backend.exists(src_path, v)
    for v in dst_versions:
        assert backend.exists(dst_path, v)

    # move file again with same checksum

    for v in src_versions:
        backend.put_file(local_path, src_path, v)

    backend.move_file(src_path, dst_path, version=version)
    if dst_path != src_path:
        for v in dst_versions:
            assert not backend.exists(src_path, v)
    for v in dst_versions:
        assert backend.exists(dst_path, v)

    # move file again with different checksum

    with open(local_path, "w") as fp:
        fp.write("different checksum")

    for v in src_versions:
        backend.put_file(local_path, src_path, v)

    if dst_path != src_path:
        for v in dst_versions:
            assert audeer.md5(local_path) != backend.checksum(dst_path, v)
    backend.move_file(src_path, dst_path, version=version)
    for v in dst_versions:
        assert audeer.md5(local_path) == backend.checksum(dst_path, v)

    # clean up

    for v in dst_versions:
        backend.remove_file(dst_path, v)


@pytest.mark.parametrize(
    "expected",
    ["audbackend.Versioned(DirFileSystem)"],
)
def test_repr(filesystem, expected):
    backend = audbackend.Versioned(filesystem)
    assert repr(backend) == expected


@pytest.mark.parametrize("dst_path", ["/file.ext", "/sub/file.ext"])
def test_versions(tmpdir, filesystem, dst_path):
    backend = audbackend.Versioned(filesystem)
    src_path = audeer.path(tmpdir, "~")
    audeer.touch(src_path)

    # empty backend
    with pytest.raises(audbackend.BackendError):
        backend.versions(dst_path)
    assert not backend.versions(dst_path, suppress_backend_errors=True)
    with pytest.raises(audbackend.BackendError):
        backend.latest_version(dst_path)

    # v1
    backend.put_file(src_path, dst_path, "1.0.0")
    assert backend.versions(dst_path) == ["1.0.0"]
    assert backend.latest_version(dst_path) == "1.0.0"

    # v2
    backend.put_file(src_path, dst_path, "2.0.0")
    assert backend.versions(dst_path) == ["1.0.0", "2.0.0"]
    assert backend.latest_version(dst_path) == "2.0.0"

    # v3 with a different extension
    other_ext = "other"
    other_remote_file = audeer.replace_file_extension(dst_path, other_ext)
    backend.put_file(src_path, other_remote_file, "3.0.0")
    assert backend.versions(dst_path) == ["1.0.0", "2.0.0"]
    assert backend.latest_version(dst_path) == "2.0.0"
