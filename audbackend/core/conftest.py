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
    fixtures=[
        "filesystem",
        "mock_date",
        "mock_owner",
        "mock_repr",
        "prepare_docstring_tests",
    ],
).pytest()


@pytest.fixture(scope="function")
def filesystem(tmpdir):
    """Filesystem backend.

    A repository with unique name is created
    for the filesystem backend.
    The filesystem backend is marked as opened
    and returned.

    Args:
        tmpdir: tmpdir fixture

    Returns:
        filesystem backend object

    """
    repo = f"repo-{audeer.uid()[:8]}"
    host = audeer.mkdir(tmpdir, "host")
    audeer.mkdir(host, repo)
    backend = audbackend.backend.FileSystem(host, repo)
    backend.opened = True
    yield backend


@pytest.fixture(scope="function")
def mock_date():
    r"""Custom date method to return a fixed date."""

    def date(path: str, version: str = None) -> str:
        date = datetime.datetime(1991, 2, 20)
        date = audbackend.core.utils.date_format(date)
        return date

    yield date


@pytest.fixture(scope="function")
def mock_owner():
    r"""Custom owner method to return a fixed owner."""

    def owner(path: str, version: str = None) -> str:
        return "doctest"

    yield owner


@pytest.fixture(scope="function")
def mock_repr():
    """Custom __repr__ method to return fixed string."""
    return 'audbackend.interface.FileSystem("host", "repo")'


@pytest.fixture(scope="function", autouse=True)
def prepare_docstring_tests(tmpdir, monkeypatch):
    r"""Code to be run before each doctest."""
    # Change to tmp dir
    monkeypatch.chdir(tmpdir)

    # Provide example file `src.txt`
    audeer.touch("src.txt")

    yield
