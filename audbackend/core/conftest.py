import datetime
import os
import tempfile

import pytest

import audeer

import audbackend


class DoctestFileSystem(audbackend.backend.FileSystem):
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


@pytest.fixture(scope="function", autouse=True)
def prepare_docstring_tests(doctest_namespace):
    with tempfile.TemporaryDirectory() as tmp:
        # Change to tmp dir
        current_dir = os.getcwd()
        os.chdir(tmp)
        # Prepare backend
        audeer.mkdir("host")
        audbackend.backend.FileSystem.create("host", "repo")
        # Provide example file `src.txt`
        audeer.touch("src.txt")
        # Provide DoctestFileSystem as FileSystem,
        # and audbackend
        # in docstring examples
        doctest_namespace["DoctestFileSystem"] = DoctestFileSystem
        doctest_namespace["audbackend"] = audbackend

        yield

        # Remove backend
        audbackend.backend.FileSystem.delete("host", "repo")
        # Change back to current dir
        os.chdir(current_dir)
