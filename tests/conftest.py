import glob
import os
import shutil

import pytest

import audbackend
import audeer
import audfactory


pytest.ROOT = os.path.dirname(os.path.realpath(__file__))
pytest.ID = audeer.uid()

pytest.ARTIFACTORY_HOST = 'https://audeering.jfrog.io/artifactory'
pytest.ARTIFACTORY_REPOSITORY = f'unittests-public/{pytest.ID}'
pytest.ARTIFACTORY_BACKEND = audbackend.Artifactory(
    'https://audeering.jfrog.io/artifactory',
    f'unittests-public/{pytest.ID}',
)

pytest.FILE_SYSTEM_HOST = audeer.path(pytest.ROOT, 'host')
pytest.FILE_SYSTEM_REPOSITORY = os.path.join('unittests-public', pytest.ID)
pytest.FILE_SYSTEM_BACKEND = audbackend.FileSystem(
    pytest.FILE_SYSTEM_HOST,
    os.path.join('unittests-public', pytest.ID)
)

pytest.BACKENDS = [
    pytest.FILE_SYSTEM_BACKEND,
    pytest.ARTIFACTORY_BACKEND,
]


@pytest.fixture(scope='session', autouse=True)
def cleanup_session():

    # clean up old coverage files
    path = audeer.path(
        pytest.ROOT,
        '.coverage.*',
    )
    for file in glob.glob(path):
        os.remove(file)

    yield

    # clean up file system
    if os.path.exists(pytest.FILE_SYSTEM_HOST):
        shutil.rmtree(pytest.FILE_SYSTEM_HOST)

    # clean up Artifactory
    url = audfactory.path(
        audfactory.url(
            pytest.ARTIFACTORY_HOST,
            repository=pytest.ARTIFACTORY_REPOSITORY,
        ),
    )
    if url.exists():
        url.unlink()
