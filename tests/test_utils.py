import sys

import pyarrow
import pyarrow.parquet as parquet
import pytest

import audeer

import audbackend


class TestChecksum:
    """Test local checksum calculation."""

    @classmethod
    @pytest.fixture(autouse=True)
    def setup(cls, tmpdir):
        """Prepare files for tests."""
        cls.files = {}

        file = "file.txt"
        cls.files[file] = audeer.path(tmpdir, file)
        with open(cls.files[file], "w") as fp:
            fp.write("hello\n")

        file = "file.parquet"
        cls.files[file] = audeer.path(tmpdir, file)
        table = pyarrow.Table.from_pylist([{"a": 0, "b": 1}])
        parquet.write_table(table, cls.files[file], compression="snappy")

        file = "file-metadata.parquet"
        cls.files[file] = audeer.path(tmpdir, file)
        metadata = {"hash": "my-hash"}
        table = table.replace_schema_metadata(metadata)
        parquet.write_table(table, cls.files[file], compression="snappy")

    @pytest.mark.parametrize(
        "file, pyarrow_installed, expected_checksum_function",
        [
            ("file.txt", True, audeer.md5),
            ("file.parquet", True, audeer.md5),
            ("file-metadata.parquet", True, lambda x: "my-hash"),
            ("file.txt", False, audeer.md5),
            ("file.parquet", False, audeer.md5),
            ("file-metadata.parquet", False, audeer.md5),
        ],
    )
    def test_checksum(self, file, pyarrow_installed, expected_checksum_function):
        """Test checksum of local file.

        Args:
            file: file name, see ``setup()``
            pyarrow_installed: if ``False,
                it hides the ``pyarrow`` module
            expected_checksum_function: function executed
                to generate expected checksum for ``file``

        """
        path = self.files[file]
        if not pyarrow_installed:
            sys.modules["pyarrow"] = None
        assert audbackend.checksum(path) == expected_checksum_function(path)
        if not pyarrow_installed:
            del sys.modules["pyarrow"]

    @pytest.mark.parametrize(
        "file, error, error_msg",
        [
            ("non-existing.txt", FileNotFoundError, "No such file or directory"),
        ],
    )
    def test_errors(self, file, error, error_msg):
        """Test expected errors.

        Args:
            file: file path
            error: expected error
            error_msg: expected error message

        """
        with pytest.raises(error, match=error_msg):
            audbackend.checksum(file)
