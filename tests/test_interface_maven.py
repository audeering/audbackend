import os
import re
import stat

import pytest

import audeer

import audbackend

from singlefolder import SingleFolder


@pytest.mark.parametrize(
    "interface",
    [
        (audbackend.backend.FileSystem, audbackend.interface.Maven),
        (SingleFolder, audbackend.interface.Maven),
    ],
    indirect=True,
)
def test_errors(tmpdir, interface):
    # Ensure we have one file and one archive published on the backend
    archive = "/archive.zip"
    local_file = "file.txt"
    local_path = audeer.touch(audeer.path(tmpdir, local_file))
    remote_file = f"/{local_file}"
    version = "1.0.0"
    interface.put_file(local_path, remote_file, version)
    interface.put_archive(tmpdir, archive, version, files=[local_file])

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
    file_invalid_char = "/invalid/char.txt?"
    error_invalid_char = re.escape(
        f"Invalid backend path '{file_invalid_char}', "
        f"does not match '[A-Za-z0-9/._-]+'."
    )
    error_backend = (
        "An exception was raised by the backend, "
        "please see stack trace for further information."
    )

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


@pytest.mark.parametrize(
    "interface",
    [
        (audbackend.backend.FileSystem, audbackend.interface.Maven),
        (SingleFolder, audbackend.interface.Maven),
    ],
    indirect=True,
)
def test_ls(tmpdir, interface):
    assert interface.ls() == []
    assert interface.ls("/") == []

    root = [
        ("/file.bar", "1.0.0"),
        ("/file.bar", "2.0.0"),
        ("/file.foo", "1.0.0"),
    ]
    root_latest = [
        ("/file.bar", "2.0.0"),
        ("/file.foo", "1.0.0"),
    ]
    root_foo = [
        ("/file.foo", "1.0.0"),
    ]
    root_bar = [
        ("/file.bar", "1.0.0"),
        ("/file.bar", "2.0.0"),
    ]
    root_bar_latest = [
        ("/file.bar", "2.0.0"),
    ]
    sub = [
        ("/sub/file.foo", "1.0.0"),
        ("/sub/file.foo", "2.0.0"),
    ]
    sub_latest = [
        ("/sub/file.foo", "2.0.0"),
    ]
    hidden = [
        ("/.sub/.file.foo", "1.0.0"),
        ("/.sub/.file.foo", "2.0.0"),
    ]
    hidden_latest = [
        ("/.sub/.file.foo", "2.0.0"),
    ]

    # create content

    tmp_file = os.path.join(tmpdir, "~")
    for path, version in root + sub + hidden:
        audeer.touch(tmp_file)
        interface.put_file(
            tmp_file,
            path,
            version,
        )

    # test

    for path, latest, pattern, expected in [
        ("/", False, None, root + sub + hidden),
        ("/", True, None, root_latest + sub_latest + hidden_latest),
        ("/", False, "*.foo", root_foo + sub + hidden),
        ("/", True, "*.foo", root_foo + sub_latest + hidden_latest),
        ("/sub/", False, None, sub),
        ("/sub/", True, None, sub_latest),
        ("/sub/", False, "*.bar", []),
        ("/sub/", True, "*.bar", []),
        ("/sub/", False, "file.*", sub),
        ("/sub/", True, "file.*", sub_latest),
        ("/.sub/", False, None, hidden),
        ("/.sub/", True, None, hidden_latest),
        ("/file.bar", False, None, root_bar),
        ("/file.bar", True, None, root_bar_latest),
        ("/sub/file.foo", False, None, sub),
        ("/sub/file.foo", True, None, sub_latest),
        ("/sub/file.foo", False, "file.*", sub),
        ("/sub/file.foo", True, "file.*", sub_latest),
        ("/sub/file.foo", False, "*.bar", []),
        ("/sub/file.foo", True, "*.bar", []),
        ("/.sub/.file.foo", False, None, hidden),
        ("/.sub/.file.foo", True, None, hidden_latest),
    ]:
        assert interface.ls(
            path,
            latest_version=latest,
            pattern=pattern,
        ) == sorted(expected)


def test_repr():
    interface = audbackend.interface.Maven(
        audbackend.backend.FileSystem("host", "repo")
    )
    assert interface.__repr__() == (
        "audbackend.interface.Maven(audbackend.backend.FileSystem('host', 'repo')"
    )
