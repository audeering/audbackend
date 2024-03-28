import datetime
import os
import tempfile

import pytest

import audeer

import audbackend


class DoctestFileSystem(audbackend.backend.FileSystem):
    def __repr__(self) -> str:
        name = "audbackend.core.backend.filesystem.FileSystem"
        return str((name, self.host, self.repository))

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


def doctest_create(
    name: str,
    host: str,
    repository: str,
):
    # call create without return value
    audbackend.create(name, host, repository)


@pytest.fixture(scope="function", autouse=True)
def prepare_docstring_tests(doctest_namespace):
    with tempfile.TemporaryDirectory() as tmp:
        current_dir = os.getcwd()
        os.chdir(tmp)

        file = "src.pth"
        audeer.touch(file)

        audbackend.register("file-system", DoctestFileSystem)
        doctest_namespace["create"] = doctest_create

        # backend

        backend = audbackend.backend.Base("host", "repo")
        doctest_namespace["backend"] = backend

        # interface

        interface = audbackend.interface.Base(backend)
        doctest_namespace["interface"] = interface

        # create backends

        DoctestFileSystem.create("host", "repo")
        DoctestFileSystem.create("host", "repo-unversioned")

        with DoctestFileSystem("host", "repo") as backend_versioned:
            with DoctestFileSystem("host", "repo-unversioned") as backend_unversioned:
                # versioned interface

                versioned = audbackend.interface.Versioned(backend_versioned)
                versioned.put_archive(".", "/a.zip", "1.0.0", files=[file])
                versioned.put_file(file, "/a/b.ext", "1.0.0")
                for version in ["1.0.0", "2.0.0"]:
                    versioned.put_file(file, "/f.ext", version)
                doctest_namespace["versioned"] = versioned

                # unversioned interface

                unversioned = audbackend.interface.Unversioned(backend_unversioned)
                unversioned.put_archive(".", "/a.zip", files=[file])
                unversioned.put_file(file, "/a/b.ext")
                unversioned.put_file(file, "/f.ext")
                doctest_namespace["unversioned"] = unversioned

                yield

        audbackend.delete("file-system", "host", "repo")
        audbackend.delete("file-system", "host", "repo-unversioned")
        audbackend.register("file-system", audbackend.backend.FileSystem)
        doctest_namespace["create"] = audbackend.create

        os.chdir(current_dir)
