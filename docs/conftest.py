import datetime
from doctest import ELLIPSIS
import os

import pytest
from sybil import Sybil
from sybil.parsers.rest import DocTestParser
from sybil.parsers.rest import SkipParser

import audbackend


@pytest.fixture(scope="function")
def mock_date():
    r"""Custom date method to return a fixed date."""

    def date(path: str) -> str:
        date = datetime.datetime(1991, 2, 20)
        date = audbackend.core.utils.date_format(date)
        return date

    yield date


@pytest.fixture(scope="module", autouse=True)
def prepare_docstring_tests(tmpdir_factory):
    r"""Code to be run before each doctest."""
    tmp = tmpdir_factory.mktemp("tmp")
    # Change to tmp dir
    current_dir = os.getcwd()
    os.chdir(tmp)

    yield

    # Change back to current dir
    os.chdir(current_dir)


pytest_collect_file = Sybil(
    parsers=[DocTestParser(optionflags=ELLIPSIS), SkipParser()],
    pattern="*.rst",
    fixtures=["mock_date", "prepare_docstring_tests"],
).pytest()
