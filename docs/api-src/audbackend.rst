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

To access a backend
the user can choose between two interfaces
:class:`audbackend.Unversioned`
or
:class:`audbackend.Versioned`:

.. autosummary::
    :toctree:
    :nosignatures:

    Unversioned
    Versioned

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
