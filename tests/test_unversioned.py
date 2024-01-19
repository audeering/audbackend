import datetime
import os
import platform
import re
import stat

import pytest

import audeer

import audbackend


@pytest.fixture(scope='function', autouse=False)
def tree(tmpdir, request):
    r"""Create file tree."""
    files = request.param
    paths = []

    for path in files:
        if os.name == 'nt':
            path = path.replace('/', os.path.sep)
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
    'tree, archive, files, tmp_root, expected',
    [
        (  # empty
            ['file.ext', 'dir/to/file.ext'],
            '/archive.zip',
            [],
            None,
            [],
        ),
        (  # single file
            ['file.ext', 'dir/to/file.ext'],
            '/archive.zip',
            'file.ext',
            None,
            ['file.ext'],
        ),
        (  # list
            ['file.ext', 'dir/to/file.ext'],
            '/archive.zip',
            ['file.ext'],
            None,
            ['file.ext'],
        ),
        (
            ['file.ext', 'dir/to/file.ext'],
            '/archive.zip',
            ['file.ext', 'dir/to/file.ext'],
            'tmp',
            ['file.ext', 'dir/to/file.ext'],
        ),
        (  # all files
            ['file.ext', 'dir/to/file.ext'],
            '/archive.zip',
            None,
            'tmp',
            ['dir/to/file.ext', 'file.ext'],
        ),
        (  # tar.gz
            ['file.ext', 'dir/to/file.ext'],
            '/archive.tar.gz',
            None,
            'tmp',
            ['dir/to/file.ext', 'file.ext'],
        ),
    ],
    indirect=['tree'],
)
@pytest.mark.parametrize(
    'backend',
    pytest.UNVERSIONED,
    indirect=True,
)
def test_archive(tmpdir, tree, archive, files, tmp_root, backend, expected):

    if tmp_root is not None:
        tmp_root = audeer.path(tmpdir, tmp_root)

    if os.name == 'nt':
        expected = [file.replace('/', os.sep) for file in expected]

    # if a tmp_root is given but does not exist,
    # put_archive() should fail
    if tmp_root is not None:
        if os.path.exists(tmp_root):
            os.removedirs(tmp_root)
        with pytest.raises(FileNotFoundError):
            backend.put_archive(
                tmpdir,
                archive,
                files=files,
                tmp_root=tmp_root,
            )
        audeer.mkdir(tmp_root)

    backend.put_archive(
        tmpdir,
        archive,
        files=files,
        tmp_root=tmp_root,
    )
    # operation will be skipped
    backend.put_archive(
        tmpdir,
        archive,
        files=files,
        tmp_root=tmp_root,
    )
    assert backend.exists(archive)

    # if a tmp_root is given but does not exist,
    # get_archive() should fail
    if tmp_root is not None:
        if os.path.exists(tmp_root):
            os.removedirs(tmp_root)
        with pytest.raises(FileNotFoundError):
            backend.get_archive(
                archive,
                tmpdir,
                tmp_root=tmp_root,
            )
        audeer.mkdir(tmp_root)

    assert backend.get_archive(
        archive,
        tmpdir,
        tmp_root=tmp_root,
    ) == expected


@pytest.mark.parametrize(
    'backend',
    pytest.UNVERSIONED,
    indirect=True,
)
def test_errors(tmpdir, backend):

    # Ensure we have one file and one archive published on the backend
    archive = '/archive.zip'
    local_file = 'file.txt'
    local_path = audeer.touch(audeer.path(tmpdir, local_file))
    local_folder = audeer.mkdir(audeer.path(tmpdir, 'folder'))
    remote_file = f'/{local_file}'
    backend.put_file(local_path, remote_file)
    backend.put_archive(tmpdir, archive, files=[local_file])

    # Create local read-only file and folder
    file_read_only = audeer.touch(audeer.path(tmpdir, 'read-only-file.txt'))
    os.chmod(file_read_only, stat.S_IRUSR)
    folder_read_only = audeer.mkdir(audeer.path(tmpdir, 'read-only-folder'))
    os.chmod(folder_read_only, stat.S_IRUSR)

    # Invalid file names / versions and error messages
    file_invalid_path = 'invalid/path.txt'
    error_invalid_path = re.escape(
        f"Invalid backend path '{file_invalid_path}', "
        f"must start with '/'."
    )
    file_invalid_char = '/invalid/char.txt?'
    error_invalid_char = re.escape(
        f"Invalid backend path '{file_invalid_char}', "
        f"does not match '[A-Za-z0-9/._-]+'."
    )
    error_backend = (
        'An exception was raised by the backend, '
        'please see stack trace for further information.'
    )
    error_read_only_folder = (
        f"Permission denied: '{os.path.join(folder_read_only, local_file)}'"
    )
    error_read_only_file = (
        f"Permission denied: '{file_read_only}'"
    )
    if platform.system() == 'Windows':
        error_is_a_folder = "Is a directory: "
    else:
        error_is_a_folder = f"Is a directory: '{local_folder}'"
    if platform.system() == 'Windows':
        error_not_a_folder = "Not a directory: "
    else:
        error_not_a_folder = f"Not a directory: '{local_path}'"

    # --- checksum ---
    # `path` missing
    with pytest.raises(audbackend.BackendError, match=error_backend):
        backend.checksum('/missing.txt')
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.checksum(file_invalid_char)

    # --- exists ---
    # `path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.exists(file_invalid_path)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.exists(file_invalid_char)

    # --- get_archive ---
    # `src_path` missing
    with pytest.raises(audbackend.BackendError, match=error_backend):
        backend.get_archive('/missing.txt', tmpdir)
    # `src_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.get_archive(file_invalid_path, tmpdir)
    # `src_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.get_archive(file_invalid_char, tmpdir)
    # `tmp_root` does not exist
    if platform.system() == 'Windows':
        error_msg = (
            "The system cannot find the path specified: 'non-existing..."
        )
    else:
        error_msg = "No such file or directory: 'non-existing/..."
    with pytest.raises(FileNotFoundError, match=error_msg):
        backend.get_archive(archive, tmpdir, tmp_root='non-existing')
    # extension of `src_path` is not supported
    error_msg = 'You can only extract ZIP and TAR.GZ files, ...'
    backend.put_file(
        audeer.touch(audeer.path(tmpdir, 'archive.bad')),
        '/archive.bad',
    )
    with pytest.raises(RuntimeError, match=error_msg):
        backend.get_archive('/archive.bad', tmpdir)
    # `src_path` is a malformed archive
    error_msg = 'Broken archive: '
    backend.put_file(
        audeer.touch(audeer.path(tmpdir, 'malformed.zip')),
        '/malformed.zip',
    )
    with pytest.raises(RuntimeError, match=error_msg):
        backend.get_archive('/malformed.zip', tmpdir)
    # no write permissions to `dst_root`
    if not platform.system() == 'Windows':
        # Currently we don't know how to provoke permission error on Windows
        with pytest.raises(PermissionError, match=error_read_only_folder):
            backend.get_archive(archive, folder_read_only)
    # `dst_root` is not a directory
    with pytest.raises(NotADirectoryError, match=error_not_a_folder):
        backend.get_archive(archive, local_path)

    # --- get_file ---
    # `src_path` missing
    with pytest.raises(audbackend.BackendError, match=error_backend):
        backend.get_file('/missing.txt', 'missing.txt')
    # `src_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.get_file(file_invalid_path, tmpdir)
    # `src_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.get_file(file_invalid_char, tmpdir)
    # no write permissions to `dst_path`
    if not platform.system() == 'Windows':
        # Currently we don't know how to provoke permission error on Windows
        with pytest.raises(PermissionError, match=error_read_only_file):
            backend.get_file(remote_file, file_read_only)
        dst_path = audeer.path(folder_read_only, 'file.txt')
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
        backend.ls('/missing/')
    with pytest.raises(audbackend.BackendError, match=error_backend):
        backend.ls('/missing.txt')
    remote_file_with_wrong_ext = audeer.replace_file_extension(
        remote_file,
        'missing',
    )
    with pytest.raises(audbackend.BackendError, match=error_backend):
        backend.ls(remote_file_with_wrong_ext)
    # joined path without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.ls(file_invalid_path)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.ls(file_invalid_char)

    # --- put_archive ---
    # `src_root` missing
    error_msg = 'No such file or directory: ...'
    with pytest.raises(FileNotFoundError, match=error_msg):
        backend.put_archive(
            audeer.path(tmpdir, '/missing/'),
            archive,
            files=local_file,
        )
    # `src_root` is not a directory
    with pytest.raises(NotADirectoryError, match=error_not_a_folder):
        backend.put_archive(local_path, archive)
    # `files` missing
    error_msg = 'No such file or directory: ...'
    with pytest.raises(FileNotFoundError, match=error_msg):
        backend.put_archive(tmpdir, archive, files='missing.txt')
    # `dst_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.put_archive(
            tmpdir,
            file_invalid_path,
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
    error_msg = 'You can only create a ZIP or TAR.GZ archive, not ...'
    with pytest.raises(RuntimeError, match=error_msg):
        backend.put_archive(tmpdir, '/archive.bad', files=local_file)

    # --- put_file ---
    # `src_path` does not exists
    error_msg = 'No such file or directory: ...'
    with pytest.raises(FileNotFoundError, match=error_msg):
        backend.put_file(
            audeer.path(tmpdir, 'missing.txt'),
            remote_file,
        )
    # `src_path` is a folder
    with pytest.raises(IsADirectoryError, match=error_is_a_folder):
        backend.put_file(local_folder, remote_file)
    # `dst_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.put_file(local_path, file_invalid_path)
    # `dst_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.put_file(local_path, file_invalid_char)

    # --- remove_file ---
    # `path` does not exists
    with pytest.raises(audbackend.BackendError, match=error_backend):
        backend.remove_file('/missing.txt')
    # `path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.remove_file(file_invalid_path)
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
    'path',
    [
        '/file.txt',
        '/folder/test.txt',
    ]
)
@pytest.mark.parametrize(
    'backend',
    pytest.UNVERSIONED,
    indirect=True,
)
def test_exists(tmpdir, path, backend):

    src_path = audeer.path(tmpdir, '~')
    audeer.touch(src_path)

    assert not backend.exists(path)
    backend.put_file(src_path, path)
    assert backend.exists(path)


@pytest.mark.parametrize(
    'src_path, dst_path',
    [
        (
            'file',
            '/file',
        ),
        (
            'file.ext',
            '/file.ext',
        ),
        (
            os.path.join('dir', 'to', 'file.ext'),
            '/dir/to/file.ext',
        ),
        (
            os.path.join('dir.to', 'file.ext'),
            '/dir.to/file.ext',
        ),
    ],
)
@pytest.mark.parametrize(
    'backend, owner',
    [(name, name) for name in pytest.UNVERSIONED],
    indirect=True,
)
def test_file(tmpdir, src_path, dst_path, backend, owner):

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
    assert backend.owner(dst_path) == owner
    date = datetime.datetime.today().strftime('%Y-%m-%d')
    assert backend.date(dst_path) == date

    backend.remove_file(dst_path)
    assert not backend.exists(dst_path)


@pytest.mark.parametrize(
    'backend',
    pytest.UNVERSIONED,
    indirect=True,
)
def test_ls(tmpdir, backend):

    assert backend.ls() == []
    assert backend.ls('/') == []

    root = [
        '/file.bar',
        '/file.foo',
    ]
    root_latest = [
        '/file.bar',
        '/file.foo',
    ]
    root_foo = [
        '/file.foo',
    ]
    root_bar = [
        '/file.bar',
    ]
    root_bar_latest = [
        '/file.bar',
    ]
    sub = [
        '/sub/file.foo',
    ]
    sub_latest = [
        '/sub/file.foo',
    ]
    hidden = [
        '/.sub/.file.foo',
    ]
    hidden_latest = [
        '/.sub/.file.foo',
    ]

    # create content

    tmp_file = os.path.join(tmpdir, '~')
    for path in root + sub + hidden:
        audeer.touch(tmp_file)
        backend.put_file(
            tmp_file,
            path,
        )

    # test

    for path, pattern, expected in [
        ('/', None, root + sub + hidden),
        ('/', '*.foo', root_foo + sub + hidden),
        ('/sub/', None, sub),
        ('/sub/', '*.bar', []),
        ('/sub/', 'file.*', sub),
        ('/.sub/', None, hidden),
        ('/file.bar', None, root_bar),
        ('/sub/file.foo', None, sub),
        ('/.sub/.file.foo', None, hidden),
    ]:
        assert backend.ls(
            path,
            pattern=pattern,
        ) == sorted(expected)
