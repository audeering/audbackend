import hashlib
import os
import typing

import pytest

import audbackend
import audeer


def md5(
        file: str,
        chunk_size: int = 8192,
) -> str:
    r"""Create MD5 checksum."""
    file = audeer.safe_path(file)
    with open(file, 'rb') as fp:
        hasher = hashlib.md5()
        for chunk in md5_read_chunk(fp, chunk_size):
            hasher.update(chunk)
        return hasher.hexdigest()


def md5_read_chunk(
        fp: typing.IO,
        chunk_size: int = 8192,
):
    while True:
        data = fp.read(chunk_size)
        if not data:
            break
        yield data


@pytest.mark.parametrize(
    'files, name, folder, version, tmp_root',
    [
        (
            [],
            'empty',
            None,
            '1.0.0',
            None,
        ),
        (
            'file.ext',
            'not-empty',
            None,
            '1.0.0',
            None,
        ),
        (
            ['file.ext', 'dir/to/file.ext'],
            'not-empty',
            'group',
            '1.0.0',
            None,
        ),
        (
            ['file.ext', 'dir/to/file.ext'],
            'not-empty',
            'group',
            '2.0.0',
            'tmp',
        ),
    ],
)
@pytest.mark.parametrize(
    'backend',
    [
        audbackend.FileSystem(
            pytest.FILE_SYSTEM_HOST,
            pytest.REPOSITORY_NAME,
        ),
        audbackend.Artifactory(
            pytest.ARTIFACTORY_HOST,
            pytest.REPOSITORY_NAME,
        ),
    ]
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

    archive = backend.join(
        pytest.ID,
        'test_archive',
        name,
    )

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
    assert backend.exists(archive + '.zip', version)

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
    'name, host, cls',
    [
        (
            'file-system',
            pytest.FILE_SYSTEM_HOST,
            audbackend.FileSystem,
        ),
        (
            'artifactory',
            pytest.ARTIFACTORY_HOST,
            audbackend.Artifactory,
        ),
        pytest.param(  # backend does not exist
            'does-not-exist',
            '',
            None,
            marks=pytest.mark.xfail(raises=ValueError)
        )
    ]
)
def test_create(name, host, cls):
    backend = audbackend.create(name, host, pytest.REPOSITORY_NAME)
    assert isinstance(backend, cls)


@pytest.mark.parametrize(
    'backend',
    [
        audbackend.FileSystem(
            pytest.FILE_SYSTEM_HOST,
            pytest.REPOSITORY_NAME,
        ),
        audbackend.Artifactory(
            pytest.ARTIFACTORY_HOST,
            pytest.REPOSITORY_NAME,
        ),
    ]
)
def test_errors(tmpdir, backend):

    file_name = 'does-not-exist'
    local_file = os.path.join(tmpdir, file_name)
    remote_file = backend.join(
        pytest.ID,
        'test_errors',
        file_name,
    )

    error_msg = f"Invalid path name '{remote_file}', " \
                f"does not end on '.bad'."
    with pytest.raises(ValueError, match=error_msg):
        backend.put_file(
            local_file,
            remote_file,
            '1.0.0',
            ext='bad',
        )
    error_msg = rf"Invalid path name '{remote_file}\?', " \
                rf"allowed characters are '\[A-Za-z0-9/\._-\]\+'"
    with pytest.raises(ValueError, match=error_msg):
        backend.put_file(
            local_file,
            remote_file + '?',
            '1.0.0',
        )
    with pytest.raises(FileNotFoundError):
        backend.put_file(
            local_file,
            remote_file,
            '1.0.0',
        )
    with pytest.raises(FileNotFoundError):
        backend.put_archive(
            tmpdir,
            'archive',
            remote_file,
            '1.0.0',
        )
    with pytest.raises(FileNotFoundError):
        backend.get_file(
            remote_file,
            local_file,
            '1.0.0',
        )
    with pytest.raises(FileNotFoundError):
        backend.get_archive(
            remote_file,
            tmpdir,
            '1.0.0',
        )
    with pytest.raises(FileNotFoundError):
        backend.checksum(
            remote_file,
            '1.0.0',
        )
    with pytest.raises(FileNotFoundError):
        backend.remove_file(
            remote_file,
            '1.0.0',
        )


@pytest.mark.parametrize(
    'backend',
    [
        audbackend.FileSystem(
            pytest.FILE_SYSTEM_HOST,
            pytest.REPOSITORY_NAME,
        ),
        audbackend.Artifactory(
            pytest.ARTIFACTORY_HOST,
            pytest.REPOSITORY_NAME,
        ),
    ]
)
def test_exists(tmpdir, backend):
    file = 'test.txt'
    version = '1.0.0'
    local_file = os.path.join(tmpdir, file)
    audeer.mkdir(os.path.dirname(local_file))
    with open(local_file, 'w'):
        pass
    remote_file = backend.join(
        pytest.ID,
        'test_exists',
        file,
    )
    backend.put_file(local_file, remote_file, version)
    assert backend.exists(remote_file, version)
    assert not backend.exists('non-existing-file.txt', version)


@pytest.mark.parametrize(
    'local_file, remote_file, version, ext',
    [
        (
            'file.ext',
            'file.ext',
            '1.0.0',
            None,
        ),
        (
            'file.tar.gz',
            'file.tar.gz',
            '1.0.0',
            'tar.gz',
        ),
        (
            os.path.join('dir', 'to', 'file.ext'),
            'dir/to/file.ext',
            '1.0.0',
            None,
        ),
        (
            os.path.join('dir', 'to', 'file.ext'),
            'alias.ext',
            '1.0.0',
            None,
        ),
    ],
)
@pytest.mark.parametrize(
    'backend',
    [
        audbackend.FileSystem(
            pytest.FILE_SYSTEM_HOST,
            pytest.REPOSITORY_NAME,
        ),
        audbackend.Artifactory(
            pytest.ARTIFACTORY_HOST,
            pytest.REPOSITORY_NAME,
        ),
    ]
)
def test_file(tmpdir, local_file, remote_file, version, ext, backend):

    local_file = os.path.join(tmpdir, local_file)
    audeer.mkdir(os.path.dirname(local_file))
    with open(local_file, 'w'):
        pass

    remote_file = backend.join(
        pytest.ID,
        'test_file',
        remote_file,
    )

    assert not backend.exists(remote_file, version, ext=ext)
    backend.put_file(local_file, remote_file, version, ext=ext)
    # operation will be skipped
    backend.put_file(
        local_file,
        remote_file,
        version,
        ext=ext,
    )
    assert backend.exists(remote_file, version, ext=ext)

    backend.get_file(remote_file, local_file, version, ext=ext)
    assert os.path.exists(local_file)
    assert backend.checksum(remote_file, version, ext=ext) == md5(local_file)

    backend.remove_file(remote_file, version, ext=ext)
    assert not backend.exists(remote_file, version, ext=ext)

    if ext is None:
        _, ext = os.path.splitext(local_file)
    else:
        ext = '.' + ext


@pytest.mark.parametrize(
    'files, pattern, folder, expected',
    [
        (
            [],
            f'{pytest.ID}/test_glob/**/*.ext',
            None,
            [],
        ),
        (
            ['file.ext', 'path/to/file.ext', 'no.match'],
            f'{pytest.ID}/test_glob/**/*.ext',
            None,
            ['file.ext', 'path/to/file.ext'],
        ),
        (
            ['file.ext', 'path/to/file.ext'],
            '**/*.ext',
            f'{pytest.ID}/test_glob/path/to',
            ['path/to/file.ext'],
        ),
        # Test non-existing path on server
        (
            [],
            f'{pytest.ID}/test_non-existing-path/**/*.ext',
            None,
            [],
        ),

    ],
)
@pytest.mark.parametrize(
    'backend',
    [
        audbackend.FileSystem(
            pytest.FILE_SYSTEM_HOST,
            pytest.REPOSITORY_NAME,
        ),
        audbackend.Artifactory(
            pytest.ARTIFACTORY_HOST,
            pytest.REPOSITORY_NAME,
        ),
    ]
)
def test_glob(tmpdir, files, pattern, folder, expected, backend):

    paths = []
    for file in files:
        local_file = os.path.join(tmpdir, file)
        audeer.mkdir(os.path.dirname(local_file))
        with open(local_file, 'w'):
            pass
        remote_file = backend.join(
            pytest.ID,
            'test_glob',
            file,
        )
        paths.append(
            backend.put_file(
                local_file,
                remote_file,
                '1.0.0',
            )
        )

    expected = [
        backend._path(
            backend.join(
                pytest.ID,
                'test_glob',
                *x.split(backend.sep),
            ),
            '1.0.0',
            '.ext',
        )
        for x in expected
    ]

    assert sorted(expected) == sorted(backend.glob(pattern, folder=folder))


@pytest.mark.parametrize(
    'path, content, expected_content',
    [
        (
            'folder1',
            ['file.txt', 'folder/abc.txt'],
            ['file', 'folder'],
        ),
    ],
)
@pytest.mark.parametrize(
    'backend',
    [
        audbackend.FileSystem(
            pytest.FILE_SYSTEM_HOST,
            pytest.REPOSITORY_NAME,
        ),
        audbackend.Artifactory(
            pytest.ARTIFACTORY_HOST,
            pytest.REPOSITORY_NAME,
        ),
    ]
)
def test_ls(tmpdir, path, content, expected_content, backend):

    backend_path = backend.join(
        pytest.ID,
        'test_ls',
        path,
    )

    for file in content:
        local_file = os.path.join(tmpdir, file)
        audeer.mkdir(os.path.dirname(local_file))
        audeer.touch(local_file)
        remote_file = backend.join(backend_path, file)
        backend.put_file(
            local_file,
            remote_file,
            '1.0.0',
        )

    assert backend.ls(backend_path) == expected_content


@pytest.mark.parametrize(
    'backend',
    [
        audbackend.FileSystem(
            pytest.FILE_SYSTEM_HOST,
            pytest.REPOSITORY_NAME,
        ),
    ]
)
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
def test_join(backend, paths, expected):
    assert backend.join(*paths) == expected


@pytest.mark.parametrize(
    'file_name, ext',
    [
        ('db.yaml', None),
        ('file.tar.gz', 'tar.gz'),
    ]
)
@pytest.mark.parametrize(
    'backend',
    [
        audbackend.FileSystem(
            pytest.FILE_SYSTEM_HOST,
            pytest.REPOSITORY_NAME,
        ),
        audbackend.Artifactory(
            pytest.ARTIFACTORY_HOST,
            pytest.REPOSITORY_NAME,
        ),
    ]
)
def test_versions(tmpdir, file_name, ext, backend):

    local_file = os.path.join(tmpdir, file_name)
    with open(local_file, 'w'):
        pass
    remote_file = backend.join(
        pytest.ID,
        'test_versions',
        file_name,
    )

    # empty backend
    assert not backend.versions(remote_file, ext=ext)
    with pytest.raises(RuntimeError):
        backend.latest_version(remote_file, ext=ext)

    # v1
    backend.put_file(local_file, remote_file, '1.0.0', ext=ext)
    assert backend.versions(remote_file, ext=ext) == ['1.0.0']
    assert backend.latest_version(remote_file, ext=ext) == '1.0.0'

    # v2
    backend.put_file(local_file, remote_file, '2.0.0', ext=ext)
    assert backend.versions(remote_file, ext=ext) == ['1.0.0', '2.0.0']
    assert backend.latest_version(remote_file, ext=ext) == '2.0.0'

    # v3 with a different extension
    other_ext = 'other'
    other_remote_file = audeer.replace_file_extension(remote_file, other_ext)
    backend.put_file(local_file, other_remote_file, '3.0.0', ext=other_ext)
    assert backend.versions(remote_file, ext=ext) == ['1.0.0', '2.0.0']
    assert backend.latest_version(remote_file, ext=ext) == '2.0.0'
