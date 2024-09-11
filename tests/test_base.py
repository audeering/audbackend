import inspect

import pytest

import audbackend


@pytest.mark.parametrize(
    "method",
    [
        "checksum",
        "copy_file",
        "date",
        "exists",
        "get_file",
        "ls",
        "move_file",
        "path",
        "put_file",
        "remove_file",
    ],
)
def test_errors(tmpdir, filesystem, method):
    r"""Test for errors in AbstractBackend class.

    All of the methods that needs to be implemented
    in derived classes
    should raise a ``NotImplementedError``.

    Args:
        tmpdir: tmpdir fixture
        filesystem: filesystem fixture
        method: method of ``audbackend.AbstractBackend``

    """
    backend = audbackend.AbstractBackend(filesystem)

    # Get method to execute
    backend_method = getattr(backend, method)
    # Get number of arguments of method
    args = inspect.signature(backend_method).parameters
    n_args = len(
        [
            arg
            for arg in args.values()
            if (
                arg.kind != arg.VAR_POSITIONAL  # skip *args
                and arg.kind != arg.VAR_KEYWORD  # skip **kwargs
                and arg.default is arg.empty
            )
        ]
    )
    # Define dummy arguments
    args = [f"path-{n}" for n in range(n_args)]

    with pytest.raises(NotImplementedError):
        backend_method(*args)
