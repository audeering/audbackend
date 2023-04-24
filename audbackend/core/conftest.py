import os
import tempfile

import pytest

import audbackend
import audeer


@pytest.fixture(scope='function', autouse=True)
def prepare_docstring_tests(doctest_namespace):

    with tempfile.TemporaryDirectory() as tmp:

        current_dir = os.getcwd()
        os.chdir(tmp)

        host = 'host'
        repository = 'doctest'

        backend = audbackend.create('file-system', host, repository)

        file = 'src.pth'
        audeer.touch(file)
        backend.put_archive('.', [file], '/a.zip', '1.0.0')
        backend.put_file(file, '/a/b.ext', '1.0.0')
        for version in ['1.0.0', '2.0.0']:
            backend.put_file(file, '/name.ext', version)

        doctest_namespace['backend'] = backend

        yield

        audbackend.delete('file-system', host, repository)

        os.chdir(current_dir)
