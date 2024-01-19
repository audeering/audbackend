import datetime
import os
import tempfile

import pytest

import audeer

import audbackend


class DoctestFileSystem(audbackend.FileSystem):

    def __repr__(self) -> str:
        name = 'audbackend.core.filesystem.FileSystem'
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
        return 'doctest'


@pytest.fixture(scope='function', autouse=True)
def prepare_docstring_tests(doctest_namespace):

    with tempfile.TemporaryDirectory() as tmp:

        current_dir = os.getcwd()
        os.chdir(tmp)

        file = 'src.pth'
        audeer.touch(file)

        audbackend.register('file-system', DoctestFileSystem)

        # backend

        backend = audbackend.Backend('host', 'repository')
        doctest_namespace['backend'] = backend

        # unversioned interface

        unversioned = audbackend.create('file-system', 'host', 'unversioned', versioned=False)
        unversioned.put_archive('.', '/a.zip', files=[file])
        unversioned.put_file(file, '/a/b.ext')
        unversioned.put_file(file, '/f.ext')
        doctest_namespace['unversioned'] = unversioned

        # versioned interface

        versioned = audbackend.create('file-system', 'host', 'versioned', versioned=True)
        versioned.put_archive('.', '/a.zip', '1.0.0', files=[file])
        versioned.put_file(file, '/a/b.ext', '1.0.0')
        for version in ['1.0.0', '2.0.0']:
            versioned.put_file(file, '/f.ext', version)
        doctest_namespace['versioned'] = versioned

        yield

        audbackend.delete('file-system', 'host', 'unversioned')
        audbackend.delete('file-system', 'host', 'versioned')
        audbackend.register('file-system', audbackend.FileSystem)

        os.chdir(current_dir)
