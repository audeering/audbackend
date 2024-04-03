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
        current_dir = os.getcwd()
        os.chdir(tmp)

        file = "src.pth"
        audeer.touch(file)

        # backend

        backend = audbackend.backend.Base("host", "repo")
        doctest_namespace["backend"] = backend

        # interface

        interface = audbackend.interface.Base(backend)
        doctest_namespace["interface"] = interface

        # versioned interface

        DoctestFileSystem.create("host", "repo")
        versioned = audbackend.interface.Versioned(DoctestFileSystem("host", "repo"))
        versioned.put_archive(".", "/a.zip", "1.0.0", files=[file])
        versioned.put_file(file, "/a/b.ext", "1.0.0")
        for version in ["1.0.0", "2.0.0"]:
            versioned.put_file(file, "/f.ext", version)
        doctest_namespace["versioned"] = versioned

        # unversioned interface

        DoctestFileSystem.create("host", "repo-unversioned")
        unversioned = audbackend.interface.Unversioned(
            DoctestFileSystem("host", "repo-unversioned")
        )
        unversioned.put_archive(".", "/a.zip", files=[file])
        unversioned.put_file(file, "/a/b.ext")
        unversioned.put_file(file, "/f.ext")
        doctest_namespace["unversioned"] = unversioned

        yield

        DoctestFileSystem.delete("host", "repo")
        DoctestFileSystem.delete("host", "repo-unversioned")

        os.chdir(current_dir)
