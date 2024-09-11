import pytest

import audeer

import audbackend


def test_get_file_interrupt(tmpdir, filesystem):
    backend = audbackend.Unversioned(filesystem)
    src_path = audeer.path(tmpdir, "~tmp")

    # Put local file on backend
    with open(src_path, "w") as fp:
        fp.write("remote")
    checksum_remote = audeer.md5(src_path)
    backend.put_file(src_path, "/file")

    # change content of local file
    with open(src_path, "w") as fp:
        fp.write("local")
    checksum_local = audeer.md5(src_path)
    assert checksum_local != checksum_remote

    # Simulate malfunctioning filesystem

    def get_file(src_path, dst_path, *, callback=None):
        filesystem.get_file(src_path, dst_path, callback=callback)
        # raise error after file was retrieved
        raise InterruptedError()

    def exists(path):
        # raise error when checking if file exists
        raise InterruptedError()

    filesystem.get_file = get_file
    filesystem.exists = exists

    # Try to use malfanctioning exists() method
    with pytest.raises(audbackend.BackendError):
        backend.exists("/file")
    assert backend.exists("/file", suppress_backend_errors=True) is False

    # try to read remote file, local file remains unchanged
    with pytest.raises(audbackend.BackendError):
        backend.get_file("/file", src_path)
    assert audeer.md5(src_path) == checksum_local
