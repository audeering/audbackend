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
