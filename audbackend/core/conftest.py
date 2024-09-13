import datetime
from doctest import ELLIPSIS

import pytest
from sybil import Sybil
from sybil.parsers.doctest import DocTestParser

import audeer

import audbackend
from tests.conftest import filesystem  # noqa: F401


@pytest.fixture(scope="function")
def mock_date():
    r"""Custom date method to return a fixed date."""

    def date(path: str) -> str:
        date = datetime.datetime(1991, 2, 20)
        date = audbackend.core.utils.date_format(date)
        return date

    yield date


@pytest.fixture(scope="function", autouse=True)
def prepare_docstring_tests(tmpdir, monkeypatch):
    r"""Code to be run before each doctest."""
    # Change to tmp dir
    monkeypatch.chdir(tmpdir)

    # Provide example file `src.txt`
    audeer.touch("src.txt")

    yield


pytest_collect_file = Sybil(
    parsers=[DocTestParser(optionflags=ELLIPSIS)],
    pattern="*.py",
    fixtures=["filesystem", "mock_date", "prepare_docstring_tests"],
).pytest()
