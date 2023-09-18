import os

import pytest

import audeer

import audbackend


class BadFileSystem(audbackend.FileSystem):
    r"""Imitates a corrupted file system."""
    def _get_file(
            self,
            src_path: str,
            dst_path: str,
            version: str,
            verbose: bool,
    ):
        super()._get_file(src_path, dst_path, version, verbose)
        # raise error after file was retrieved
        raise InterruptedError()


@pytest.fixture(scope='function', autouse=False)
def bad_file_system():
    audbackend.register('file-system', BadFileSystem)
    yield
    audbackend.register('file-system', audbackend.FileSystem)


@pytest.mark.parametrize(
    'backend',
    ['file-system'],
    indirect=True,
)
def test_get_file_interrupt(tmpdir, bad_file_system, backend):

    src_path = audeer.path(tmpdir, '~tmp')

    # put local file on backend
    with open(src_path, 'w') as fp:
        fp.write('remote')
    checksum_remote = audeer.md5(src_path)
    backend.put_file(src_path, '/file', '1.0.0')

    # change content of local file
    with open(src_path, 'w') as fp:
        fp.write('local')
    checksum_local = audeer.md5(src_path)
    assert checksum_local != checksum_remote

    # try to read remote file, local file remains unchanged
    with pytest.raises(audbackend.BackendError):
        backend.get_file('/file', src_path, '1.0.0')
    assert audeer.md5(src_path) == checksum_local


@pytest.mark.parametrize(
    'backend',
    ['file-system'],
    indirect=True,
)
@pytest.mark.parametrize(
    'file, version, extensions, expected',
    [
        ('/file.tar.gz', '1.0.0', None, 'file.tar/1.0.0/file.tar-1.0.0.gz'),
        ('/file.tar.gz', '1.0.0', [], 'file.tar/1.0.0/file.tar-1.0.0.gz'),
        ('/file.tar.gz', '1.0.0', ['tar.gz'], 'file/1.0.0/file-1.0.0.tar.gz'),
        ('/.tar.gz', '1.0.0', ['tar.gz'], '.tar/1.0.0/.tar-1.0.0.gz'),
        ('/tar.gz', '1.0.0', ['tar.gz'], 'tar/1.0.0/tar-1.0.0.gz'),
        ('/.tar.gz', '1.0.0', None, '.tar/1.0.0/.tar-1.0.0.gz'),
        ('/.tar', '1.0.0', None, '.tar/1.0.0/.tar-1.0.0'),
        ('/tar', '1.0.0', None, 'tar/1.0.0/tar-1.0.0'),
    ]
)
def test_legacy_file_structure(tmpdir, backend, file, version, extensions,
                               expected):

    expected = expected.replace('/', os.path.sep)

    backend._use_legacy_file_structure(extensions=extensions)

    src_path = audeer.touch(audeer.path(tmpdir, 'tmp'))
    backend.put_file(src_path, file, version)

    path = os.path.join(backend._root, expected)
    assert str(backend._path(file, version)) == path
    assert backend.ls(file) == [(file, version)]
    assert backend.ls() == [(file, version)]
