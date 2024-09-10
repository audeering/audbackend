import os
import random
import string

import pytest

import audeer

import audbackend


def test_validate(tmpdir, filesystem):
    backend = audbackend.Versioned(filesystem)

    def random_checksum(self, path: str) -> str:
        r"""Return random checksum."""
        return "".join(
            random.choices(
                string.ascii_uppercase + string.digits,
                k=33,
            )
        )

    broken_backend = audbackend.Versioned(filesystem)
    broken_backend.checksum = random_checksum

    path = audeer.touch(tmpdir, "~.txt")
    error_msg = "Execution is interrupted because"

    with pytest.raises(InterruptedError, match=error_msg):
        broken_backend.put_file(path, "/remote.txt", "1.0.0", validate=True)
    assert not backend.exists("/remote.txt", "1.0.0")
    backend.put_file(path, "/remote.txt", "1.0.0", validate=True)
    assert backend.exists("/remote.txt", "1.0.0")

    with pytest.raises(InterruptedError, match=error_msg):
        broken_backend.get_file(
            "/remote.txt",
            "local.txt",
            "1.0.0",
            validate=True,
        )
    assert not os.path.exists("local.txt")
    backend.get_file(
        "/remote.txt",
        "local.txt",
        "1.0.0",
        validate=True,
    )
    assert os.path.exists("local.txt")

    with pytest.raises(InterruptedError, match=error_msg):
        broken_backend.copy_file(
            "/remote.txt",
            "/copy.txt",
            validate=True,
        )
    assert not backend.exists("/copy.txt", "1.0.0")
    backend.copy_file(
        "/remote.txt",
        "/copy.txt",
        version="1.0.0",
        validate=True,
    )
    assert backend.exists("/copy.txt", "1.0.0")

    with pytest.raises(InterruptedError, match=error_msg):
        broken_backend.move_file(
            "/remote.txt",
            "/move.txt",
            version="1.0.0",
            validate=True,
        )
    assert not backend.exists("/move.txt", "1.0.0")
    assert backend.exists("/remote.txt", "1.0.0")
    backend.move_file(
        "/remote.txt",
        "/move.txt",
        version="1.0.0",
        validate=True,
    )
    assert backend.exists("/move.txt", "1.0.0")
    assert not backend.exists("/remote.txt", "1.0.0")

    with pytest.raises(InterruptedError, match=error_msg):
        broken_backend.put_archive(
            tmpdir,
            "/remote.zip",
            "1.0.0",
            validate=True,
        )
    assert not backend.exists("/remote.zip", "1.0.0")
    backend.put_archive(
        ".",
        "/remote.zip",
        "1.0.0",
        validate=True,
    )
    assert backend.exists("/remote.zip", "1.0.0")

    dst_root = os.path.join(tmpdir, "extract")
    with pytest.raises(InterruptedError, match=error_msg):
        broken_backend.get_archive(
            "/remote.zip",
            dst_root,
            "1.0.0",
            validate=True,
        )
    assert not os.path.exists(dst_root)
    backend.get_archive(
        "/remote.zip",
        dst_root,
        "1.0.0",
        validate=True,
    )
    assert os.path.exists(dst_root)
