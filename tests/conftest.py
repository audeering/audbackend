import glob
import os
import shutil

import pytest

import audeer
import audfactory


pytest.ROOT = audeer.safe_path(
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        'tmp',
    )
)

pytest.ARTIFACTORY_HOST = 'https://artifactory.audeering.com/artifactory'
pytest.FILE_SYSTEM_HOST = os.path.join(pytest.ROOT, 'repo')
pytest.ID = audeer.uid()
pytest.REPOSITORY_NAME = 'data-unittests-local'


@pytest.fixture(scope='session', autouse=True)
def cleanup_session():
    path = os.path.join(
        pytest.ROOT,
        '..',
        '.coverage.*',
    )
    for file in glob.glob(path):
        os.remove(file)
    yield
    if os.path.exists(pytest.ROOT):
        shutil.rmtree(pytest.ROOT)
    url = audfactory.artifactory_path(
        audfactory.server_url(
            pytest.ID,
            repository=pytest.REPOSITORY_NAME,
        ),
    )
    if url.exists():
        url.unlink()
