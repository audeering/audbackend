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
            version: str,
    ) -> str:
        date = datetime.datetime(1991, 2, 20)
        date = audbackend.core.utils.date_format(date)
        return date

    def _owner(
            self,
            path: str,
            version: str,
    ) -> str:
        return 'doctest'


@pytest.fixture(scope='function', autouse=True)
def prepare_docstring_tests(doctest_namespace):

    with tempfile.TemporaryDirectory() as tmp:

        current_dir = os.getcwd()
        os.chdir(tmp)

        host = 'host'
        repository = 'doctest'

        audbackend.register('file-system', DoctestFileSystem)
        backend = audbackend.create('file-system', host, repository)

        file = 'src.pth'
        audeer.touch(file)
        backend.put_archive('.', '/a.zip', '1.0.0', files=[file])
        backend.put_file(file, '/a/b.ext', '1.0.0')
        for version in ['1.0.0', '2.0.0']:
            backend.put_file(file, '/f.ext', version)

        doctest_namespace['backend'] = backend

        yield

        audbackend.delete('file-system', host, repository)
        audbackend.register('file-system', audbackend.FileSystem)

        os.chdir(current_dir)
