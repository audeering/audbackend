import os

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
            marks=pytest.mark.xfail(raises=ValueError)
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

    file_name = 'does-not-exist'
    local_file = os.path.join(tmpdir, file_name)
    remote_file = 'does-not-exist'

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
    with pytest.raises(FileNotFoundError):
        backend.ls(remote_file)


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
    'src_path, dst_path, version, ext',
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
            os.path.join('dir.to', 'file.ext'),
            'dir.to/file.ext',
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
    pytest.BACKENDS,
    indirect=True,
)
def test_file(tmpdir, src_path, dst_path, version, ext, backend):

    src_path = audeer.path(tmpdir, src_path)
    audeer.mkdir(os.path.dirname(src_path))
    audeer.touch(src_path)

    assert not backend.exists(dst_path, version, ext=ext)
    backend.put_file(src_path, dst_path, version, ext=ext)
    # operation will be skipped
    backend.put_file(src_path, dst_path, version, ext=ext)
    assert backend.exists(dst_path, version, ext=ext)

    backend.get_file(dst_path, src_path, version, ext=ext)
    assert os.path.exists(src_path)
    assert backend.checksum(dst_path, version, ext=ext) == \
           audbackend.md5(src_path)

    backend.remove_file(dst_path, version, ext=ext)
    assert not backend.exists(dst_path, version, ext=ext)


@pytest.mark.parametrize(
    'files, pattern, folder, expected',
    [
        (
            [],
            '**/*.ext',
            None,
            [],
        ),
        (
            ['file.ext', 'path/to/file.ext', 'no.match'],
            '**/*.ext',
            None,
            ['file.ext', 'path/to/file.ext'],
        ),
        (
            ['file.ext', 'path/to/file.ext'],
            '**/*.ext',
            'path/to',
            ['path/to/file.ext'],
        ),
        # Test non-existing path on server
        (
            [],
            'does-not-exist/**/*.ext',
            None,
            [],
        ),

    ],
)
@pytest.mark.parametrize(
    'backend',
    pytest.BACKENDS,
    indirect=True,
)
def test_glob(tmpdir, files, pattern, folder, expected, backend):

    src_path = audeer.path(tmpdir, '~')
    audeer.touch(src_path)

    paths = []
    for dst_path in files:
        paths.append(
            backend.put_file(
                src_path,
                dst_path,
                '1.0.0',
            )
        )

    expected = [
        backend._path(
            file,
            '1.0.0',
            '.ext',
        )
        for file in expected
    ]

    assert sorted(expected) == sorted(backend.glob(pattern, folder=folder))


@pytest.mark.parametrize(
    'backend',
    pytest.BACKENDS,
    indirect=True,
)
def test_ls(tmpdir, backend):

    assert backend.ls() == []
    assert backend.ls('/') == []

    sub_content = [  # two versions of same file
        ('sub/file.txt', None, '1.0.0'),
        ('sub/file.txt', None, '2.0.0'),
    ]
    sub_content_latest = sub_content[-1:]

    content = [  # three files with different extensions
        ('file.tar.gz', '', '1.0.0'),
        ('file.tar.gz', None, '1.0.0'),
        ('file.tar.gz', '.tar.gz', '1.0.0'),
    ]
    content_latest = content

    content = sub_content + content
    content_latest = content_latest + sub_content_latest

    # create content

    tmp_file = os.path.join(tmpdir, '~')
    for path, ext, version in content:
        audeer.touch(tmp_file)
        backend.put_file(
            tmp_file,
            path,
            version,
            ext=ext,
        )

    # test

    for folder, expected, expected_latest in [
        ('/', content, content_latest),
        ('sub', sub_content, sub_content_latest),
    ]:
        expected = [  # replace ext where it is None
            (p, f".{p.split('.')[-1]}" if e is None else e, v)
            for p, e, v in expected
        ]
        expected = sorted(expected)
        assert backend.ls(folder) == expected

        expected_latest = [  # replace ext where it is None
            (p, f".{p.split('.')[-1]}" if e is None else e, v)
            for p, e, v in expected_latest
        ]
        expected_latest = sorted(expected_latest)
        assert backend.ls(folder, latest_version=True) == expected_latest


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
    'dst_path, ext',
    [
        ('db.yaml', None),
        ('file.tar.gz', 'tar.gz'),
    ]
)
@pytest.mark.parametrize(
    'backend',
    pytest.BACKENDS,
    indirect=True,
)
def test_versions(tmpdir, dst_path, ext, backend):

    src_path = audeer.path(tmpdir, '~')
    audeer.touch(src_path)

    # empty backend
    assert not backend.versions(dst_path, ext=ext)
    with pytest.raises(RuntimeError):
        backend.latest_version(dst_path, ext=ext)

    # v1
    backend.put_file(src_path, dst_path, '1.0.0', ext=ext)
    assert backend.versions(dst_path, ext=ext) == ['1.0.0']
    assert backend.latest_version(dst_path, ext=ext) == '1.0.0'

    # v2
    backend.put_file(src_path, dst_path, '2.0.0', ext=ext)
    assert backend.versions(dst_path, ext=ext) == ['1.0.0', '2.0.0']
    assert backend.latest_version(dst_path, ext=ext) == '2.0.0'

    # v3 with a different extension
    other_ext = 'other'
    other_remote_file = audeer.replace_file_extension(dst_path, other_ext)
    backend.put_file(src_path, other_remote_file, '3.0.0', ext=other_ext)
    assert backend.versions(dst_path, ext=ext) == ['1.0.0', '2.0.0']
    assert backend.latest_version(dst_path, ext=ext) == '2.0.0'
