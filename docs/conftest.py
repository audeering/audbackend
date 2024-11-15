from doctest import ELLIPSIS

from sybil import Sybil
from sybil.parsers.rest import DocTestParser
from sybil.parsers.rest import PythonCodeBlockParser
from sybil.parsers.rest import SkipParser

from audbackend.core.conftest import mock_date  # noqa: F401
from audbackend.core.conftest import mock_owner  # noqa: F401
from audbackend.core.conftest import prepare_docstring_tests  # noqa: F401


pytest_collect_file = Sybil(
    parsers=[
        DocTestParser(optionflags=ELLIPSIS),
        PythonCodeBlockParser(),
        SkipParser(),
    ],
    pattern="*.rst",
    fixtures=["mock_date", "mock_owner", "prepare_docstring_tests"],
).pytest()
