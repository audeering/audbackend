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

pytest.ARTIFACTORY_HOST = 'https://audeering.jfrog.io/artifactory'
pytest.FILE_SYSTEM_HOST = os.path.join(pytest.ROOT, 'repo')
pytest.ID = audeer.uid()
pytest.REPOSITORY_NAME = 'unittests-public'


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
    url = audfactory.path(
        audfactory.url(
            pytest.ARTIFACTORY_HOST,
            repository=pytest.REPOSITORY_NAME,
            group_id=pytest.ID,
        ),
    )
    if url.exists():
        url.unlink()
