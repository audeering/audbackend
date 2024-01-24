import pytest

import audbackend


@pytest.mark.parametrize(
    'paths, expected',
    [
        (['/'], '/'),
        (['/', ''], '/'),
        (['/file'], '/file'),
        (['/file/'], '/file/'),
        (['/root', 'file'], '/root/file'),
        (['/root', 'file/'], '/root/file/'),
        (['/', 'root', None, '', 'file', ''], '/root/file'),
        (['/', 'root', None, '', 'file', '/'], '/root/file/'),
        (['/', 'root', None, '', 'file', '/', ''], '/root/file/'),
        pytest.param(
            [''],
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(
            ['file'],
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(
            ['sub/file'],
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(
            ['', '/file'],
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
    ]
)
@pytest.mark.parametrize(
    'backend',
    [
        audbackend.backend.Base('host', 'repository'),
    ]
)
def test_join(paths, expected, backend):
    assert backend.join(*paths) == expected


@pytest.mark.parametrize(
    'path, expected',
    [
        ('/', ('/', '')),
        ('/file', ('/', 'file')),
        ('/root/', ('/root/', '')),
        ('/root/file', ('/root/', 'file')),
        ('/root/file/', ('/root/file/', '')),
        ('//root///file', ('/root/', 'file')),
        pytest.param(
            '',
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(
            'file',
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
        pytest.param(
            'sub/file',
            None,
            marks=pytest.mark.xfail(raises=ValueError),
        ),
    ]
)
@pytest.mark.parametrize(
    'backend',
    [
        audbackend.backend.Base('host', 'repository'),
    ]
)
def test_split(path, expected, backend):
    assert backend.split(path) == expected
