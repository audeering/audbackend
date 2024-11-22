audbackend
==========

.. automodule:: audbackend

:mod:`audbackend`
provides an abstract layer
for managing files
in a repository
on a host.

This involves two components:

1. A *backend* that
   implements file operations
   on a specific storing device
   (:mod:`audbackend.backend`).

2. An *interface* that
   passes user requests
   to a backend
   (:mod:`audbackend.interface`).

Additionally,
the following classes
and functions are available.

.. autosummary::
    :toctree:
    :nosignatures:

    BackendError
    Repository
