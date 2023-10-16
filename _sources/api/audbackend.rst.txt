audbackend
==========

.. automodule:: audbackend

A backend is a generic interface
for storing and accessing files
on a host.

Currently the following backends
are shipped with :mod:`audbackend`:

.. autosummary::
    :toctree:
    :nosignatures:

    Artifactory
    FileSystem

Users can implement their own
backend by deriving from
:class:`audbackend.Backend`.

.. autosummary::
    :toctree:
    :nosignatures:

    Backend

In addition to the backends
the following classes and functions are available.

.. autosummary::
    :toctree:
    :nosignatures:

    BackendError
    Repository
    access
    available
    create
    delete
    register
