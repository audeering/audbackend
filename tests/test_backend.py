import os
import platform
import re
import stat

import pytest

import audbackend
import audeer


@pytest.fixture(scope='function')
def backend(request):

    name = request.param
    host = pytest.HOSTS[name]
    repository = pytest.REPOSITORIES[name] + audeer.uid()[:8]
    backend = audbackend.create(name, host, repository)

    yield backend


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

    files_as_list = [files] if isinstance(files, str) else files
    for file in files_as_list:
        path = os.path.join(tmpdir, file)
        audeer.mkdir(os.path.dirname(path))
        with open(path, 'w'):
            pass

    archive = backend.join('test_archive', name)

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
    'name, cls',
    [
        (
            'file-system',
            audbackend.FileSystem,
        ),
        (
            'artifactory',
            audbackend.Artifactory,
        ),
        pytest.param(  # backend does not exist
            'does-not-exist',
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        )
    ]
)
def test_create(name, cls):
    backend = audbackend.create(name, 'host', 'repository')
    assert isinstance(backend, cls)


@pytest.mark.parametrize(
    'backend',
    pytest.BACKENDS,
    indirect=True,
)
def test_errors(tmpdir, backend):

    # Ensure we have one file and one archive published on the backend
    archive = 'archive.zip'
    file = 'file.txt'
    version = '1.0.0'
    src_path = audeer.touch(audeer.path(tmpdir, file))
    backend.put_file(src_path, file, version)
    backend.put_archive(tmpdir, [file], archive, version)

    # Create local read-only folder
    folder_read_only = audeer.mkdir(audeer.path(tmpdir, 'read-only-folder'))
    os.chmod(folder_read_only, stat.S_IRUSR)

    # File names and error messages
    # for common errors
    archive_invalid_extension = 'archive.bad'
    file_missing = 'missing.txt'
    file_invalid_char = 'missing.txt?'
    folder_missing = 'missing/'
    error_invalid_char = re.escape(
        f"Invalid path name '{file_invalid_char}', "
        "allowed characters are '[A-Za-z0-9/._-]+'."
    )
    error_missing = (
        f"No such file or directory: '{file_missing} with version {version}'"
    )
    error_missing_folder = (
        f"No such file or directory: '{folder_missing}'"
    )
    error_read_only = (
        f"Permission denied: '{os.path.join(folder_read_only, file)}'"
    )

    # --- checksum ---
    # `path` missing
    with pytest.raises(FileNotFoundError, match=error_missing):
        backend.checksum(file_missing, version)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.checksum(file_invalid_char, version)

    # --- exists ---
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.exists(file_invalid_char, version)

    # --- get_archive ---
    # `src_path` missing
    with pytest.raises(FileNotFoundError, match=error_missing):
        backend.get_archive(file_missing, tmpdir, version)
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
        audeer.touch(audeer.path(tmpdir, archive_invalid_extension)),
        archive_invalid_extension,
        version,
    )
    with pytest.raises(RuntimeError, match=error_msg):
        backend.get_archive(archive_invalid_extension, tmpdir, version)
    # `src_path` is a malformed archive
    error_msg = 'Broken archive: '
    backend.put_file(
        audeer.touch(audeer.path(tmpdir, 'malformed.zip')),
        'malformed.zip',
        version,
    )
    with pytest.raises(RuntimeError, match=error_msg):
        backend.get_archive('malformed.zip', tmpdir, version)
    # no write permissions to `dst_path`
    if not platform.system() == 'Windows':
        # Currently we don't know how to provoke permission error on Windows
        with pytest.raises(PermissionError, match=error_read_only):
            backend.get_archive(archive, folder_read_only, version)

    # --- get_file ---
    # `src_path` missing
    with pytest.raises(FileNotFoundError, match=error_missing):
        backend.get_file(file_missing, file_missing, version)
    # `src_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.get_file(file_invalid_char, tmpdir, version)
    # no write permissions to `dst_path`
    if not platform.system() == 'Windows':
        # Currently we don't know how to provoke permission error on Windows
        with pytest.raises(PermissionError, match=error_read_only):
            backend.get_file(file, folder_read_only, version)

    # --- join ---
    # joined path contains invalid char
    error_msg = re.escape(
        f"Invalid path name '{file_invalid_char}/{file}', "
        "allowed characters are '[A-Za-z0-9/._-]+'."
    )
    with pytest.raises(ValueError, match=error_msg):
        backend.join(file_invalid_char, file)
    error_msg = re.escape(
        f"Invalid path name '{file}/{file_invalid_char}', "
        "allowed characters are '[A-Za-z0-9/._-]+'."
    )
    with pytest.raises(ValueError, match=error_msg):
        backend.join(file, file_invalid_char)

    # --- latest_version ---
    # `path` missing
    error_msg = re.escape(
        f"Cannot find a version for '{file_missing}' "
        f"in '{backend.repository}'"
    )
    with pytest.raises(RuntimeError, match=error_msg):
        backend.latest_version(file_missing)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.latest_version(file_invalid_char)

    # --- ls ---
    # `path` missing
    with pytest.raises(FileNotFoundError, match=error_missing_folder):
        backend.ls(folder_missing)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.ls(file_invalid_char)

    # --- put_archive ---
    # `src_root` missing
    error_msg = 'No such file or directory: ...'
    with pytest.raises(FileNotFoundError, match=error_msg):
        backend.put_archive(
            audeer.path(tmpdir, folder_missing),
            file,
            archive,
            version,
        )
    # `files` missing
    error_msg = 'No such file or directory: ...'
    with pytest.raises(FileNotFoundError, match=error_msg):
        backend.put_archive(tmpdir, file_missing, archive, version)
    # `dst_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.put_archive(tmpdir, file, file_invalid_char, version)
    # extension of `dst_path` is not supported
    error_msg = 'You can only create a ZIP or TAR.GZ archive, not ...'
    with pytest.raises(RuntimeError, match=error_msg):
        backend.put_archive(tmpdir, file, archive_invalid_extension, version)

    # --- put_file ---
    # `src_path` does not exists
    error_msg = 'No such file or directory: ...'
    with pytest.raises(FileNotFoundError, match=error_msg):
        backend.put_file(audeer.path(tmpdir, file_missing), file, version)
    # `dst_path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.put_file(src_path, file_invalid_char, version)

    # --- remove_file ---
    # `path` does not exists
    with pytest.raises(FileNotFoundError, match=error_missing):
        backend.remove_file(file_missing, version)
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.remove_file(file_invalid_char, version)

    # --- split ---
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.split(file_invalid_char)

    # --- versions ---
    # `path` contains invalid character
    with pytest.raises(ValueError, match=error_invalid_char):
        backend.versions(file_invalid_char)


@pytest.mark.parametrize(
    'path, version',
    [
        ('file.txt', '1.0.0'),
        ('folder/test.txt', '1.0.0'),
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
            'file',
            '1.0.0',
        ),
        (
            'file.ext',
            'file.ext',
            '1.0.0',
        ),
        (
            os.path.join('dir', 'to', 'file.ext'),
            'dir/to/file.ext',
            '1.0.0',
        ),
        (
            os.path.join('dir.to', 'file.ext'),
            'dir.to/file.ext',
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
    assert backend.checksum(dst_path, version) == audbackend.md5(src_path)

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

    sub_content = [  # files in sub directory
        ('sub/file.foo', '1.0.0'),
        ('sub/file.foo', '2.0.0'),
    ]
    sub_content_latest = sub_content[-1:]

    content = [  # files in root directory
        ('file.bar', '1.0.0'),
        ('file.bar', '2.0.0'),
    ]
    content_latest = content[-1:] + sub_content_latest
    content += sub_content

    # create content

    tmp_file = os.path.join(tmpdir, '~')
    for path, version in content:
        audeer.touch(tmp_file)
        backend.put_file(
            tmp_file,
            path,
            version,
        )

    # test

    for folder, latest, pattern, expected in [
        ('/', False, None, content),
        ('/', True, None, content_latest),
        ('/', False, '*.foo', sub_content),
        ('/', True, '*.foo', sub_content_latest),
        ('sub', False, None, sub_content),
        ('sub', True, None, sub_content_latest),
        ('sub', False, '*.bar', []),
        ('sub', True, '*.bar', []),
    ]:
        assert backend.ls(
            folder,
            latest_version=latest,
            pattern=pattern,
        ) == sorted(expected)


@pytest.mark.parametrize(
    'paths, expected',
    [
        ([''], ''),
        (['', ''], ''),
        (['file'], 'file'),
        (['root', 'file'], 'root/file'),
        (['', 'root', None, '', 'file', ''], 'root/file'),
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
    'dst_path',
    [
        'file.ext',
        'sub/file.ext'
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
    assert not backend.versions(dst_path)
    with pytest.raises(RuntimeError):
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
