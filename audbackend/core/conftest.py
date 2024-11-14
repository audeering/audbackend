import datetime
import doctest

import pytest
import sybil
from sybil.parsers.rest import DocTestParser

import audeer

import audbackend


# Collect doctests
pytest_collect_file = sybil.Sybil(
    parsers=[DocTestParser(optionflags=doctest.ELLIPSIS)],
    patterns=["*.py"],
    fixtures=["prepare_docstring_tests", "filesystem_backend"],
).pytest()


class FileSystem(audbackend.backend.FileSystem):
    def __init__(
        self,
        host: str,
        repository: str,
    ):
        super().__init__(host, repository)
        self.opened = True

    def _date(
        self,
        path: str,
    ) -> str:
        date = datetime.datetime(1991, 2, 20)
        date = audbackend.core.utils.date_format(date)
        return date

    def _owner(
        self,
        path: str,
    ) -> str:
        return "doctest"


@pytest.fixture(scope="function")
def filesystem_backend():
    yield FileSystem("host", "repo")


@pytest.fixture(scope="function", autouse=True)
def prepare_docstring_tests(tmpdir, monkeypatch):
    r"""Code to be run before each doctest."""
    # Change to tmp dir
    monkeypatch.chdir(tmpdir)

    # Provide example file `src.txt`
    audeer.touch("src.txt")

    # Prepare backend
    audeer.mkdir("host", "repo")

    yield


# @pytest.fixture(scope="function", autouse=True)
# def prepare_docstring_tests(doctest_namespace):
#     with tempfile.TemporaryDirectory() as tmp:
#         # Change to tmp dir
#         current_dir = os.getcwd()
#         os.chdir(tmp)
#         # Prepare backend
#         audeer.mkdir("host")
#         audbackend.backend.FileSystem.create("host", "repo")
#         # Provide example file `src.txt`
#         audeer.touch("src.txt")
#         # Provide DoctestFileSystem as FileSystem,
#         # and audbackend
#         # in docstring examples
#         doctest_namespace["DoctestFileSystem"] = DoctestFileSystem
#         doctest_namespace["audbackend"] = audbackend
#
#         yield
#
#         # Remove backend
#         audbackend.backend.FileSystem.delete("host", "repo")
#         # Change back to current dir
#         os.chdir(current_dir)
