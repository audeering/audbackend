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

        backend = audbackend.Backend('host', 'repo')
        doctest_namespace['backend'] = backend

        interface = audbackend.Interface(backend)
        doctest_namespace['interface'] = interface

        # versioned interface

        versioned = audbackend.create(
            'file-system',
            'host',
            'repo',
            interface=audbackend.Versioned,
        )
        assert isinstance(versioned, audbackend.Versioned)
        versioned.put_archive('.', '/a.zip', '1.0.0', files=[file])
        versioned.put_file(file, '/a/b.ext', '1.0.0')
        for version in ['1.0.0', '2.0.0']:
            versioned.put_file(file, '/f.ext', version)
        doctest_namespace['versioned'] = versioned

        # unversioned interface

        unversioned = audbackend.create(
            'file-system',
            'host',
            'repo-unversioned',
            interface=audbackend.Unversioned,
        )
        assert isinstance(unversioned, audbackend.Unversioned)
        unversioned.put_archive('.', '/a.zip', files=[file])
        unversioned.put_file(file, '/a/b.ext')
        unversioned.put_file(file, '/f.ext')
        doctest_namespace['unversioned'] = unversioned

        yield

        audbackend.delete('file-system', 'host', 'repo')
        audbackend.delete('file-system', 'host', 'repo-unversioned')
        audbackend.register('file-system', audbackend.FileSystem)

        os.chdir(current_dir)
