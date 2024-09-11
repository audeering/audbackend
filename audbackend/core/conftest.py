import datetime
import os
import tempfile

import fsspec
import pytest

import audeer

import audbackend


def date(path: str) -> str:
    date = datetime.datetime(1991, 2, 20)
    date = audbackend.core.utils.date_format(date)
    return date


@pytest.fixture(scope="function", autouse=True)
def prepare_docstring_tests(doctest_namespace):
    with tempfile.TemporaryDirectory() as tmp:
        # Change to tmp dir
        current_dir = os.getcwd()
        os.chdir(tmp)
        # Prepare backend
        audeer.mkdir("host/repo")
        # Provide example file `src.txt`
        audeer.touch("src.txt")
        fs = fsspec.filesystem("dir", path="./host/repo")
        fs.date = date

        doctest_namespace["audbackend"] = audbackend
        doctest_namespace["fs"] = fs

        yield

        audeer.rmdir("host")
        # Change back to current dir
        os.chdir(current_dir)
