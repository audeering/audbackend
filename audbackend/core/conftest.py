import tempfile
import pytest

import audbackend
import audeer


@pytest.fixture(autouse=True)
def create_backend(doctest_namespace):
    with tempfile.TemporaryDirectory() as tmp:
        audbackend.create(
            'artifactory',
            'https://host.com',
            'repo',
        )
        backend = audbackend.create(
            'file-system',
            tmp,
            'doctest',
        )
        src_file = 'src.pth'
        src_path = audeer.touch(audeer.path(tmp, src_file))
        backend.put_archive(tmp, [src_file], 'folder/name.zip', '1.0.0')
        for version in ['1.0.0', '2.0.0']:
            backend.put_file(src_path, 'folder/name.ext', version)
        doctest_namespace['backend'] = backend
        doctest_namespace['tmp'] = tmp
        yield
