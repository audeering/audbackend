import os
import random
import string

import pytest

import audeer

import audbackend


# def test_validate(tmpdir, filesystem):


@pytest.mark.parametrize("error_msg", ["Execution is interrupted because"])
class TestValidate:
    """Test methods that provide validation.

    We inject a broken `checksum()` method
    into one backend
    to force the validation to go always wrong
    on that backend.

    Args:
        tmpdir: tmpdir fixture
        filesystem: filesystemn fixture

    """

    @classmethod
    @pytest.fixture(scope="function", autouse=True)
    def setup(cls, tmpdir, filesystem, monkeypatch):
        """Instantiate backend objects and local file."""
        cls.backend = audbackend.Unversioned(filesystem)

        def random_checksum(path: str) -> str:
            r"""Return random checksum."""
            return "".join(
                random.choices(
                    string.ascii_uppercase + string.digits,
                    k=33,
                )
            )

        cls.broken_backend = audbackend.Unversioned(filesystem)
        cls.broken_backend._checksum = random_checksum
        cls.local_file = audeer.touch(tmpdir, "~.txt")

        working_dir = audeer.mkdir(tmpdir, "work")
        monkeypatch.chdir(working_dir)

    def test_put_file(self, error_msg):
        """Test validate for put_file."""
        with pytest.raises(InterruptedError, match=error_msg):
            self.broken_backend.put_file(self.local_file, "/remote.txt", validate=True)
        assert not self.backend.exists("/remote.txt")
        self.backend.put_file(self.local_file, "/remote.txt", validate=True)
        assert self.backend.exists("/remote.txt")

    def test_get_file(self, error_msg):
        """Test validate for get_file."""
        self.backend.put_file(self.local_file, "/remote.txt", validate=True)
        with pytest.raises(InterruptedError, match=error_msg):
            self.broken_backend.get_file("/remote.txt", "local.txt", validate=True)
        assert not os.path.exists("local.txt")
        self.backend.get_file("/remote.txt", "local.txt", validate=True)
        assert os.path.exists("local.txt")

    def test_copy_file(self, error_msg):
        """Test validate for copy_file."""
        self.backend.put_file(self.local_file, "/remote.txt", validate=True)
        with pytest.raises(InterruptedError, match=error_msg):
            self.broken_backend.copy_file("/remote.txt", "/copy.txt", validate=True)
        assert not self.backend.exists("/copy.txt")
        self.backend.copy_file("/remote.txt", "/copy.txt", validate=True)
        assert self.backend.exists("/copy.txt")

    def test_move_file(self, error_msg):
        """Test validate for move_file."""
        self.backend.put_file(self.local_file, "/remote.txt", validate=True)
        with pytest.raises(InterruptedError, match=error_msg):
            self.broken_backend.move_file("/remote.txt", "/move.txt", validate=True)
        assert not self.backend.exists("/move.txt")
        assert self.backend.exists("/remote.txt")
        self.backend.move_file("/remote.txt", "/move.txt", validate=True)
        assert self.backend.exists("/move.txt")
        assert not self.backend.exists("/remote.txt")

    def test_put_archive(self, error_msg):
        """Test validate for put_archive."""
        with pytest.raises(InterruptedError, match=error_msg):
            self.broken_backend.put_archive(".", "/remote.zip", validate=True)
        assert not self.backend.exists("/remote.zip")
        self.backend.put_archive(".", "/remote.zip", validate=True)
        assert self.backend.exists("/remote.zip")

    def test_get_archive(self, error_msg):
        """Test validate for get_archive."""
        self.backend.put_archive(".", "/remote.zip", validate=True)
        with pytest.raises(InterruptedError, match=error_msg):
            self.broken_backend.get_archive("/remote.zip", "./extract", validate=True)
        assert not os.path.exists("./extract")
        self.backend.get_archive("/remote.zip", "./extract", validate=True)
        assert os.path.exists("./extract")
