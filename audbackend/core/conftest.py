import datetime
import doctest
import os

import pytest
import sybil
from sybil.parsers.rest import DocTestParser

import audeer

import audbackend


# Collect doctests
pytest_collect_file = sybil.Sybil(
    parsers=[DocTestParser(optionflags=doctest.ELLIPSIS)],
    patterns=["*.py"],
    fixtures=[
        "filesystem_backend",
        "prepare_docstring_tests",
        "clear",
    ],
).pytest()


class FileSystem(audbackend.backend.FileSystem):
    def __init__(self, host, repository):
        super().__init__(host, repository)
        self.opened = True

    def _date(self, path):
        date = datetime.datetime(1991, 2, 20)
        date = audbackend.core.utils.date_format(date)
        return date

    def _owner(self, path):
        return "doctest"


@pytest.fixture(scope="session", autouse=True)
def clear():
    """Clear local files and filesystem backend.

    When using a tmpdir with the scope ``"function"`` or ``"class"``,
    a new tmpdir is used each line
    in the docstring tests.
    When using the next greater scope ``"module"``,
    the same tmpdir is used in the whole file,
    which means there is no scope
    that provides a new tmpdir
    for each function/method
    within a file.
    To simulate this behavior,
    we use the scope ``"module"``,
    and provide this ``clear()`` function
    to reset after a finished docstring.

    """

    def clear_all():
        # Clear backend
        audeer.rmdir("host", "repo")
        audeer.mkdir("host", "repo")
        # Clear local files
        files = audeer.list_file_names(".", basenames=True)
        files = [file for file in files if not file == "src.txt"]
        for file in files:
            os.remove(file)

    yield clear_all


@pytest.fixture(scope="function")
def filesystem_backend():
    """Filesystem backend with patched date and owner methods.

    The backend is also opened already.

    """
    yield FileSystem("host", "repo")


@pytest.fixture(scope="module", autouse=True)
def prepare_docstring_tests(tmpdir_factory):
    r"""Code to be run before each doctest."""
    tmp_dir = tmpdir_factory.mktemp("tmp")

    try:
        # Change to tmp dir
        current_dir = os.getcwd()
        os.chdir(tmp_dir)

        # Provide example file `src.txt`
        audeer.touch("src.txt")

        # Prepare backend
        audeer.mkdir("host", "repo")

        yield

    finally:
        os.chdir(current_dir)
