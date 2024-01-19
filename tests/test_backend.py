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
        audbackend.Backend('host', 'repository'),
    ]
)
def test_join(paths, expected, interface):
    assert interface.join(*paths) == expected


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
        audbackend.Backend('host', 'repository'),
    ]
)
def test_split(path, expected, interface):
    assert interface.split(path) == expected
