import datetime
import os
import tempfile

import pytest

import audeer

import audbackend


class DoctestFileSystem(audbackend.backend.FileSystem):
    def __repr__(self) -> str:  # noqa: D105
        return f"audbackend.backend.FileSystem('{self.host}', '{self.repository}')"

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


@pytest.fixture(scope="module", autouse=True)
def prepare_docstring_tests(doctest_namespace):
    with tempfile.TemporaryDirectory() as tmp:
        # Change to tmp dir
        current_dir = os.getcwd()
        os.chdir(tmp)
        # Prepare backend
        audeer.mkdir("host")
        DoctestFileSystem.create("host", "repo")
        # Provide DoctestFileSystem as FileSystem,
        # and audbackend
        # in docstring examples
        doctest_namespace["FileSystem"] = DoctestFileSystem
        doctest_namespace["audbackend"] = audbackend

        yield

        # Remove backend
        DoctestFileSystem.delete("host", "repo")
        # Change back to current dir
        os.chdir(current_dir)
