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
    'file, version, extensions, regex, expected',
    [
        (
            '/file.tar.gz', '1.0.0', None, False,
            'file.tar/1.0.0/file.tar-1.0.0.gz',
        ),
        (
            '/file.tar.gz', '1.0.0', [], False,
            'file.tar/1.0.0/file.tar-1.0.0.gz',
        ),
        (
            '/file.tar.gz', '1.0.0', ['tar.gz'], False,
            'file/1.0.0/file-1.0.0.tar.gz',
        ),
        (
            '/.tar.gz', '1.0.0', ['tar.gz'], False,
            '.tar/1.0.0/.tar-1.0.0.gz',
        ),
        (
            '/tar.gz', '1.0.0', ['tar.gz'], False,
            'tar/1.0.0/tar-1.0.0.gz',
        ),
        (
            '/.tar.gz', '1.0.0', None, False,
            '.tar/1.0.0/.tar-1.0.0.gz',
        ),
        (
            '/.tar', '1.0.0', None, False,
            '.tar/1.0.0/.tar-1.0.0',
        ),
        (
            '/tar', '1.0.0', None, False,
            'tar/1.0.0/tar-1.0.0',
        ),
        # test regex
        (
            '/file.0.tar.gz', '1.0.0', [r'\d+.tar.gz'], False,
            'file.0.tar/1.0.0/file.0.tar-1.0.0.gz',
        ),
        (
            '/file.0.tar.gz', '1.0.0', [r'\d+.tar.gz'], True,
            'file/1.0.0/file-1.0.0.0.tar.gz',
        ),
        (
            '/file.99.tar.gz', '1.0.0', [r'\d+.tar.gz'], True,
            'file/1.0.0/file-1.0.0.99.tar.gz',
        ),
        (
            '/file.prediction.99.tar.gz', '1.0.0',
            [r'prediction.\d+.tar.gz', r'truth.tar.gz'], True,
            'file/1.0.0/file-1.0.0.prediction.99.tar.gz',
        ),
        (
            '/file.truth.tar.gz', '1.0.0',
            [r'prediction.\d+.tar.gz', r'truth.tar.gz'], True,
            'file/1.0.0/file-1.0.0.truth.tar.gz',
        ),
        (
            '/file.99.tar.gz', '1.0.0', [r'(\d+.)?tar.gz'], True,
            'file/1.0.0/file-1.0.0.99.tar.gz',
        ),
        (
            '/file.tar.gz', '1.0.0', [r'(\d+.)?tar.gz'], True,
            'file/1.0.0/file-1.0.0.tar.gz',
        ),
    ]
)
def test_legacy_file_structure(tmpdir, backend, file, version, extensions,
                               regex, expected):

    expected = expected.replace('/', os.path.sep)

    backend._use_legacy_file_structure(extensions=extensions, regex=regex)

    src_path = audeer.touch(audeer.path(tmpdir, 'tmp'))
    backend.put_file(src_path, file, version)

    path = os.path.join(backend._root, expected)
    assert str(backend._path(file, version)) == path
    assert backend.ls(file) == [(file, version)]
    assert backend.ls() == [(file, version)]
