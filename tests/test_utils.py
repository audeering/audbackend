import sys

import pyarrow
import pyarrow.parquet as parquet
import pytest

import audeer

import audbackend


@pytest.fixture
def pyarrow_installed(request):
    """Simulate missing pyarrow installation.

    Args:
        request: request parameter for indirect call of fixture

    """
    if not request.param:
        sys.modules["pyarrow"] = None

        yield False

        del sys.modules["pyarrow"]

    else:
        yield True


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

        file = "folder"
        cls.files[file] = audeer.mkdir(tmpdir, file)

    @pytest.mark.parametrize("pyarrow_installed", [True, False], indirect=True)
    @pytest.mark.parametrize(
        "file",
        ["file.txt", "file.parquet", "file-metadata.parquet", "folder"],
    )
    def test_checksum(self, file, pyarrow_installed):
        """Test checksum of local file.

        Args:
            file: file name, see ``setup()``
            pyarrow_installed: if ``False,
                it hides the ``pyarrow`` module
            expected_checksum_function: function executed
                to generate expected checksum for ``file``

        """
        path = self.files[file]
        expected_checksum = self.determine_expected_checksum(file, pyarrow_installed)
        assert audbackend.checksum(path) == expected_checksum

    @pytest.mark.parametrize(
        "file, error, error_msg",
        [
            ("non-existing.txt", FileNotFoundError, "non-existing.txt"),
            ("non-existing.parquet", FileNotFoundError, "non-existing.parquet"),
        ],
    )
    def test_errors(self, file, error, error_msg):
        """Test expected errors.

        Args:
            file: file path
            error: expected error
            error_msg: expected error message.
                For ``FileNotFoundError``,
                we recommend to use only the file name
                as the rest of the error message differs under Windows

        """
        with pytest.raises(error, match=error_msg):
            file = self.files.get(file, file)
            audbackend.checksum(file)

    def determine_expected_checksum(self, file, pyarrow_installed):
        """Expected checksum for file and pyarrow installation.

        Args:
            file: file to calculate checksum for
            pyarrow_installed: if ``True`` it assumes ``pyarrow`` is installed

        """
        if file == "file-metadata.parquet" and pyarrow_installed:
            return "my-hash"
        return audeer.md5(self.files[file])
