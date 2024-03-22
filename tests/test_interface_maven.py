import os

import pytest

import audeer

import audbackend


@pytest.mark.parametrize(
    "interface",
    [("file-system", audbackend.interface.Maven)],
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
