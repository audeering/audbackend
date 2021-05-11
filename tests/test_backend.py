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
    'files, name, folder, version',
    [
        (
            [],
            'empty',
            None,
            '1.0.0',
        ),
        (
            'file.ext',
            'not-empty',
            None,
            '1.0.0',
        ),
        (
            ['file.ext', 'dir/to/file.ext'],
            'not-empty',
            'group',
            '1.0.0',
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
def test_archive(tmpdir, files, name, folder, version, backend):

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
    path_backend = backend.put_archive(tmpdir, files, archive, version)
    # operation will be skipped
    assert backend.put_archive(tmpdir, files, archive, version) == path_backend
    assert backend.exists(archive + '.zip', version)

    assert backend.get_archive(archive, tmpdir, version) == files_as_list


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
    path_backend = backend.put_file(local_file, remote_file, version, ext=ext)
    # operation will be skipped
    assert backend.put_file(
        local_file,
        remote_file,
        version,
        ext=ext,
    ) == path_backend
    assert backend.exists(remote_file, version, ext=ext)

    backend.get_file(remote_file, local_file, version, ext=ext)
    assert os.path.exists(local_file)
    assert backend.checksum(remote_file, version, ext=ext) == md5(local_file)

    assert backend.remove_file(remote_file, version, ext=ext) == path_backend
    assert not backend.exists(remote_file, version, ext=ext)

    if ext is None:
        _, ext = os.path.splitext(local_file)
    else:
        ext = '.' + ext
    assert path_backend.endswith(ext)


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
        backend.path(
            backend.join(
                pytest.ID,
                'test_glob',
                *x.split(backend.sep),
            ),
            '1.0.0',
        )
        for x in expected
    ]

    assert sorted(expected) == sorted(backend.glob(pattern, folder=folder))


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
@pytest.mark.parametrize(
    'path, version, ext, expected',
    [
        ('media/test', '1.0.0', None, 'test-1.0.0'),
        ('media/test1-12.344', '1.0.0', None, 'test1-12-1.0.0.344'),
        ('media/test.tar', '1.0.0', None, 'test-1.0.0.tar'),
        ('media/test.tar', '1.0.0', 'tar', 'test-1.0.0.tar'),
        ('media/test.tar', '1.0.0', '.tar', 'test-1.0.0.tar'),
        ('media/test.tar.gz', '1.0.0', None, 'test.tar-1.0.0.gz'),
        ('media/test.tar.gz', '1.0.0', 'tar.gz', 'test-1.0.0.tar.gz'),
        ('media/test.tar.gz', '1.0.0', '.tar.gz', 'test-1.0.0.tar.gz'),
        ('media/test.1.2.3', '1.0.0', '1.2.3', 'test-1.0.0.1.2.3'),
        ('media/test.1.2.3', '1.0.0', '', 'test.1.2.3-1.0.0'),
        pytest.param(  # invalid character
            r'media\test',
            '1.0.0',
            None,
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(  # invalid file extension
            r'media/test.tar.gz',
            '1.0.0',
            'gz.tar',
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
    ]
)
def test_path(backend, path, version, ext, expected):
    path = backend.path(path, version, ext=ext)
    assert os.path.basename(path) == expected


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

    assert not backend.versions(remote_file, ext=ext)
    with pytest.raises(RuntimeError):
        backend.latest_version(remote_file, ext=ext)
    backend.put_file(local_file, remote_file, '1.0.0', ext=ext)
    assert backend.versions(remote_file, ext=ext) == ['1.0.0']
    assert backend.latest_version(remote_file, ext=ext) == '1.0.0'
    backend.put_file(local_file, remote_file, '2.0.0', ext=ext)
    assert backend.versions(remote_file, ext=ext) == ['1.0.0', '2.0.0']
    assert backend.latest_version(remote_file, ext=ext) == '2.0.0'
