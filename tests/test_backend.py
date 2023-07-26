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
    pytest.BACKENDS,
    indirect=True,
)
def test_archive(tmpdir, tree, archive, files, tmp_root, backend, expected):

    version = '1.0.0'

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
                version,
                files=files,
                tmp_root=tmp_root,
            )
        audeer.mkdir(tmp_root)

    backend.put_archive(
        tmpdir,
        archive,
        version,
        files=files,
        tmp_root=tmp_root,
    )
    # operation will be skipped
    backend.put_archive(
        tmpdir,
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
                tmpdir,
                version,
                tmp_root=tmp_root,
            )
        audeer.mkdir(tmp_root)

    assert backend.get_archive(
        archive,
        tmpdir,
        version,
        tmp_root=tmp_root,
    ) == expected


@pytest.mark.parametrize(
    'backend',
    pytest.BACKENDS,
    indirect=True,
)
def test_errors(tmpdir, backend):

    # Ensure we have one file and one archive published on the backend
    archive = '/archive.zip'
    local_file = 'file.txt'
    local_path = audeer.touch(audeer.path(tmpdir, local_file))
    local_folder = audeer.mkdir(audeer.path(tmpdir, 'folder'))
    remote_file = f'/{local_file}'
    version = '1.0.0'
    backend.put_file(local_path, remote_file, version)
    backend.put_archive(tmpdir, archive, version, files=[local_file])

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
    empty_version = ''
    error_empty_version = 'Version must not be empty.'
    invalid_version = '1.0.?'
    error_invalid_version = re.escape(
        f"Invalid version '{invalid_version}', "
        f"does not match '[A-Za-z0-9._-]+'."
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
        backend.checksum('/missing.txt', version)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.checksum(file_invalid_char, version)
    # invalid version
    with pytest.raises(ValueError, match=error_empty_version):
        backend.checksum(remote_file, empty_version)
    with pytest.raises(ValueError, match=error_invalid_version):
        backend.checksum(remote_file, invalid_version)

    # --- exists ---
    # `path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.exists(file_invalid_path, version)
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
        backend.get_archive('/missing.txt', tmpdir, version)
    # `src_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.get_archive(file_invalid_path, tmpdir, version)
    # `src_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.get_archive(file_invalid_char, tmpdir, version)
    # invalid version
    with pytest.raises(ValueError, match=error_empty_version):
        backend.get_archive(archive, tmpdir, empty_version)
    with pytest.raises(ValueError, match=error_invalid_version):
        backend.get_archive(archive, tmpdir, invalid_version)
    # `tmp_root` does not exist
    if platform.system() == 'Windows':
        error_msg = (
            "The system cannot find the path specified: 'non-existing..."
        )
    else:
        error_msg = "No such file or directory: 'non-existing/..."
    with pytest.raises(FileNotFoundError, match=error_msg):
        backend.get_archive(archive, tmpdir, version, tmp_root='non-existing')
    # extension of `src_path` is not supported
    error_msg = 'You can only extract ZIP and TAR.GZ files, ...'
    backend.put_file(
        audeer.touch(audeer.path(tmpdir, 'archive.bad')),
        '/archive.bad',
        version,
    )
    with pytest.raises(RuntimeError, match=error_msg):
        backend.get_archive('/archive.bad', tmpdir, version)
    # `src_path` is a malformed archive
    error_msg = 'Broken archive: '
    backend.put_file(
        audeer.touch(audeer.path(tmpdir, 'malformed.zip')),
        '/malformed.zip',
        version,
    )
    with pytest.raises(RuntimeError, match=error_msg):
        backend.get_archive('/malformed.zip', tmpdir, version)
    # no write permissions to `dst_root`
    if not platform.system() == 'Windows':
        # Currently we don't know how to provoke permission error on Windows
        with pytest.raises(PermissionError, match=error_read_only_folder):
            backend.get_archive(archive, folder_read_only, version)
    # `dst_root` is not a directory
    with pytest.raises(NotADirectoryError, match=error_not_a_folder):
        backend.get_archive(archive, local_path, version)

    # --- get_file ---
    # `src_path` missing
    with pytest.raises(audbackend.BackendError, match=error_backend):
        backend.get_file('/missing.txt', 'missing.txt', version)
    # `src_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.get_file(file_invalid_path, tmpdir, version)
    # `src_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.get_file(file_invalid_char, tmpdir, version)
    # invalid version
    with pytest.raises(ValueError, match=error_empty_version):
        backend.get_file(remote_file, local_file, empty_version)
    with pytest.raises(ValueError, match=error_invalid_version):
        backend.get_file(remote_file, local_file, invalid_version)
    # no write permissions to `dst_path`
    if not platform.system() == 'Windows':
        # Currently we don't know how to provoke permission error on Windows
        with pytest.raises(PermissionError, match=error_read_only_file):
            backend.get_file(remote_file, file_read_only, version)
        dst_path = audeer.path(folder_read_only, 'file.txt')
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
        backend.latest_version('/missing.txt')
    # joined path without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.latest_version(file_invalid_path)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.latest_version(file_invalid_char)

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
            version,
            files=local_file,
        )
    # `src_root` is not a directory
    with pytest.raises(NotADirectoryError, match=error_not_a_folder):
        backend.put_archive(local_path, archive, version)
    # `files` missing
    error_msg = 'No such file or directory: ...'
    with pytest.raises(FileNotFoundError, match=error_msg):
        backend.put_archive(tmpdir, archive, version, files='missing.txt')
    # `dst_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.put_archive(
            tmpdir,
            file_invalid_path,
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
    error_msg = 'You can only create a ZIP or TAR.GZ archive, not ...'
    with pytest.raises(RuntimeError, match=error_msg):
        backend.put_archive(tmpdir, '/archive.bad', version, files=local_file)

    # --- put_file ---
    # `src_path` does not exists
    error_msg = 'No such file or directory: ...'
    with pytest.raises(FileNotFoundError, match=error_msg):
        backend.put_file(
            audeer.path(tmpdir, 'missing.txt'),
            remote_file,
            version,
        )
    # `src_path` is a folder
    with pytest.raises(IsADirectoryError, match=error_is_a_folder):
        backend.put_file(local_folder, remote_file, version)
    # `dst_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.put_file(local_path, file_invalid_path, version)
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
        backend.remove_file('/missing.txt', version)
    # `path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.remove_file(file_invalid_path, version)
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
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.versions(file_invalid_char)


@pytest.mark.parametrize(
    'path, version',
    [
        ('/file.txt', '1.0.0'),
        ('/folder/test.txt', '1.0.0'),
    ]
)
@pytest.mark.parametrize(
    'backend',
    pytest.BACKENDS,
    indirect=True,
)
def test_exists(tmpdir, path, version, backend):

    src_path = audeer.path(tmpdir, '~')
    audeer.touch(src_path)

    assert not backend.exists(path, version)
    backend.put_file(src_path, path, version)
    assert backend.exists(path, version)


@pytest.mark.parametrize(
    'src_path, dst_path, version',
    [
        (
            'file',
            '/file',
            '1.0.0',
        ),
        (
            'file.ext',
            '/file.ext',
            '1.0.0',
        ),
        (
            os.path.join('dir', 'to', 'file.ext'),
            '/dir/to/file.ext',
            '1.0.0',
        ),
        (
            os.path.join('dir.to', 'file.ext'),
            '/dir.to/file.ext',
            '1.0.0',
        ),
    ],
)
@pytest.mark.parametrize(
    'backend, owner',
    [(name, name) for name in pytest.BACKENDS],
    indirect=True,
)
def test_file(tmpdir, src_path, dst_path, version, backend, owner):

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
    assert backend.owner(dst_path, version) == owner
    date = datetime.datetime.today().strftime('%Y-%m-%d')
    assert backend.date(dst_path, version) == date

    backend.remove_file(dst_path, version)
    assert not backend.exists(dst_path, version)


@pytest.mark.parametrize(
    'backend',
    pytest.BACKENDS,
    indirect=True,
)
def test_ls(tmpdir, backend):

    assert backend.ls() == []
    assert backend.ls('/') == []

    root = [
        ('/file.bar', '1.0.0'),
        ('/file.bar', '2.0.0'),
        ('/file.foo', '1.0.0'),
    ]
    root_latest = [
        ('/file.bar', '2.0.0'),
        ('/file.foo', '1.0.0'),
    ]
    root_foo = [
        ('/file.foo', '1.0.0'),
    ]
    root_bar = [
        ('/file.bar', '1.0.0'),
        ('/file.bar', '2.0.0'),
    ]
    root_bar_latest = [
        ('/file.bar', '2.0.0'),
    ]
    sub = [
        ('/sub/file.foo', '1.0.0'),
        ('/sub/file.foo', '2.0.0'),
    ]
    sub_latest = [
        ('/sub/file.foo', '2.0.0'),
    ]
    hidden = [
        ('/.sub/.file.foo', '1.0.0'),
        ('/.sub/.file.foo', '2.0.0'),
    ]
    hidden_latest = [
        ('/.sub/.file.foo', '2.0.0'),
    ]

    # create content

    tmp_file = os.path.join(tmpdir, '~')
    for path, version in root + sub + hidden:
        audeer.touch(tmp_file)
        backend.put_file(
            tmp_file,
            path,
            version,
        )

    # test

    for path, latest, pattern, expected in [
        ('/', False, None, root + sub + hidden),
        ('/', True, None, root_latest + sub_latest + hidden_latest),
        ('/', False, '*.foo', root_foo + sub + hidden),
        ('/', True, '*.foo', root_foo + sub_latest + hidden_latest),
        ('/sub/', False, None, sub),
        ('/sub/', True, None, sub_latest),
        ('/sub/', False, '*.bar', []),
        ('/sub/', True, '*.bar', []),
        ('/.sub/', False, None, hidden),
        ('/.sub/', True, None, hidden_latest),
        ('/file.bar', False, None, root_bar),
        ('/file.bar', True, None, root_bar_latest),
        ('/sub/file.foo', False, None, sub),
        ('/sub/file.foo', True, None, sub_latest),
        ('/.sub/.file.foo', False, None, hidden),
        ('/.sub/.file.foo', True, None, hidden_latest),
    ]:
        assert backend.ls(
            path,
            latest_version=latest,
            pattern=pattern,
        ) == sorted(expected)


@pytest.mark.parametrize(
    'paths, expected',
    [
        (['/'], '/'),
        (['/', ''], '/'),
        (['/file'], '/file'),
        (['/file/'], '/file/'),
        (['/root', 'file'], '/root/file'),
        (['/root', 'file/'], '/root/file/'),
        (['/', 'root', None, '', 'file', ''], '/root/file'),
        (['/', 'root', None, '', 'file', '/'], '/root/file/'),
        (['/', 'root', None, '', 'file', '/', ''], '/root/file/'),
        pytest.param(
            [''],
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(
            ['file'],
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(
            ['sub/file'],
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(
            ['', '/file'],
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
    ]
)
@pytest.mark.parametrize(
    'backend',
    [
        audbackend.Backend('host', 'repository'),
    ]
)
def test_join(paths, expected, backend):
    assert backend.join(*paths) == expected


@pytest.mark.parametrize(
    'path, expected',
    [
        ('/', ('/', '')),
        ('/file', ('/', 'file')),
        ('/root/', ('/root/', '')),
        ('/root/file', ('/root/', 'file')),
        ('/root/file/', ('/root/file/', '')),
        ('//root///file', ('/root/', 'file')),
        pytest.param(
            '',
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(
            'file',
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(
            'sub/file',
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
    ]
)
@pytest.mark.parametrize(
    'backend',
    [
        audbackend.Backend('host', 'repository'),
    ]
)
def test_split(path, expected, backend):
    assert backend.split(path) == expected


@pytest.mark.parametrize(
    'dst_path',
    [
        '/file.ext',
        '/sub/file.ext'
    ]
)
@pytest.mark.parametrize(
    'backend',
    pytest.BACKENDS,
    indirect=True,
)
def test_versions(tmpdir, dst_path, backend):

    src_path = audeer.path(tmpdir, '~')
    audeer.touch(src_path)

    # empty backend
    with pytest.raises(audbackend.BackendError):
        backend.versions(dst_path)
    assert not backend.versions(dst_path, suppress_backend_errors=True)
    with pytest.raises(audbackend.BackendError):
        backend.latest_version(dst_path)

    # v1
    backend.put_file(src_path, dst_path, '1.0.0')
    assert backend.versions(dst_path) == ['1.0.0']
    assert backend.latest_version(dst_path) == '1.0.0'

    # v2
    backend.put_file(src_path, dst_path, '2.0.0')
    assert backend.versions(dst_path) == ['1.0.0', '2.0.0']
    assert backend.latest_version(dst_path) == '2.0.0'

    # v3 with a different extension
    other_ext = 'other'
    other_remote_file = audeer.replace_file_extension(dst_path, other_ext)
    backend.put_file(src_path, other_remote_file, '3.0.0')
    assert backend.versions(dst_path) == ['1.0.0', '2.0.0']
    assert backend.latest_version(dst_path) == '2.0.0'
