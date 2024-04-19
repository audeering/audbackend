import pytest

import audbackend


def test_repository():
    name = "name"
    host = "host"
    backend = "backend"
    msg = "Repository is deprecated and will be removed with version 2.2.0."
    with pytest.warns(UserWarning, match=msg):
        repo = audbackend.Repository(name, host, backend)
    assert repo.name == name
    assert repo.host == host
    assert repo.backend == backend
    assert repo.__repr__() == f"Repository('{name}', '{host}', '{backend}')"
