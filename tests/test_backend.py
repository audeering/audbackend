import os
import platform
import re
import stat

import pytest

import audbackend
import audeer


@pytest.mark.parametrize(
    'files, name, folder, version, tmp_root',
    [
        (
            [],
            'empty.zip',
            None,
            '1.0.0',
            None,
        ),
        (
            'file.ext',
            'not-empty.zip',
            None,
            '1.0.0',
            None,
        ),
        (
            ['file.ext', 'dir/to/file.ext'],
            'not-empty.zip',
            'group',
            '1.0.0',
            None,
        ),
        (
            ['file.ext', 'dir/to/file.ext'],
            'not-empty.zip',
            'group',
            '2.0.0',
            'tmp',
        ),
        (
            ['file.ext', 'dir/to/file.ext'],
            'not-empty.tar.gz',
            'group',
            '2.0.0',
            'tmp',
        ),
    ],
)
@pytest.mark.parametrize(
    'backend',
    pytest.BACKENDS,
    indirect=True,
)
def test_archive(tmpdir, files, name, folder, version, tmp_root, backend):

    if tmp_root is not None:
        tmp_root = audeer.path(tmpdir, tmp_root)

    if os.name == 'nt':
        if isinstance(files, str):
            files = files.replace('/', os.sep)
        elif files:
            files = [file.replace('/', os.sep) for file in files]

    files_as_list = audeer.to_list(files)
    for file in files_as_list:
        path = os.path.join(tmpdir, file)
        audeer.mkdir(os.path.dirname(path))
        with open(path, 'w'):
            pass

    archive = backend.join('/test_archive', name)

    # if a tmp_root is given but does not exist,
    # put_archive() should fail
    if tmp_root is not None:
        if os.path.exists(tmp_root):
            os.removedirs(tmp_root)
        with pytest.raises(FileNotFoundError):
            backend.put_archive(
                tmpdir,
                files,
                archive,
                version,
                tmp_root=tmp_root,
            )
        audeer.mkdir(tmp_root)

    backend.put_archive(
        tmpdir,
        files,
        archive,
        version,
        tmp_root=tmp_root,
    )
    # operation will be skipped
    backend.put_archive(
        tmpdir,
        files,
        archive,
        version,
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
    ) == files_as_list


@pytest.mark.parametrize(
    'backend',
    pytest.BACKENDS,
    indirect=True,
)
def test_errors(tmpdir, backend):

    # Ensure we have one file and one archive published on the backend
    archive = '/archive.zip'
    local_file = 'file.txt'
    remote_file = f'/{local_file}'
    version = '1.0.0'
    src_path = audeer.touch(audeer.path(tmpdir, local_file))
    backend.put_file(src_path, remote_file, version)
    backend.put_archive(tmpdir, [local_file], archive, version)

    # Create local read-only file and folder
    file_read_only = audeer.touch(audeer.path(tmpdir, 'read-only-file.txt'))
    os.chmod(file_read_only, stat.S_IRUSR)
    folder_read_only = audeer.mkdir(audeer.path(tmpdir, 'read-only-folder'))
    os.chmod(folder_read_only, stat.S_IRUSR)

    # File names and error messages
    # for common errors
    file_invalid_path = 'invalid/path.txt'
    error_invalid_path = re.escape(
        f"Invalid backend path '{file_invalid_path}', "
        f"must start with '/'."
    )
    file_invalid_char = '/invalid/char.txt?'
    error_invalid_char = re.escape(
        f"Invalid backend path '{file_invalid_char}', "
        f"allowed characters are '[A-Za-z0-9/._-]+'."
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

    # --- checksum ---
    # `path` missing
    with pytest.raises(audbackend.BackendError, match=error_backend):
        backend.checksum('/missing.txt', version)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.checksum(file_invalid_char, version)

    # --- exists ---
    # `path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.exists(file_invalid_path, version)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.exists(file_invalid_char, version)

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
    # no write permissions to `dst_path`
    if not platform.system() == 'Windows':
        # Currently we don't know how to provoke permission error on Windows
        with pytest.raises(PermissionError, match=error_read_only_folder):
            backend.get_archive(archive, folder_read_only, version)

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
    # no write permissions to `dst_path`
    if not platform.system() == 'Windows':
        # Currently we don't know how to provoke permission error on Windows
        with pytest.raises(PermissionError, match=error_read_only_file):
            backend.get_file(remote_file, file_read_only, version)
        dst_path = audeer.path(folder_read_only, 'file.txt')
        with pytest.raises(PermissionError, match=error_read_only_folder):
            backend.get_file(remote_file, dst_path, version)

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
    # `path` missing
    with pytest.raises(audbackend.BackendError, match=error_backend):
        backend.ls('/missing/')
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
            local_file,
            archive,
            version,
        )
    # `files` missing
    error_msg = 'No such file or directory: ...'
    with pytest.raises(FileNotFoundError, match=error_msg):
        backend.put_archive(tmpdir, 'missing.txt', archive, version)
    # `dst_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.put_archive(tmpdir, local_file, file_invalid_path, version)
    # `dst_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.put_archive(tmpdir, local_file, file_invalid_char, version)
    # extension of `dst_path` is not supported
    error_msg = 'You can only create a ZIP or TAR.GZ archive, not ...'
    with pytest.raises(RuntimeError, match=error_msg):
        backend.put_archive(tmpdir, local_file, '/archive.bad', version)

    # --- put_file ---
    # `src_path` does not exists
    error_msg = 'No such file or directory: ...'
    with pytest.raises(FileNotFoundError, match=error_msg):
        backend.put_file(
            audeer.path(tmpdir, 'missing.txt'),
            remote_file,
            version,
        )
    # `dst_path` without leading '/'
    with pytest.raises(ValueError, match=error_invalid_path):
        backend.put_file(src_path, file_invalid_path, version)
    # `dst_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.put_file(src_path, file_invalid_char, version)

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
    'backend',
    pytest.BACKENDS,
    indirect=True,
)
def test_file(tmpdir, src_path, dst_path, version, backend):

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
