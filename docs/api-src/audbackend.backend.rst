.. _backends:

audbackend.backend
==================

.. automodule:: audbackend.backend

Currently the following
backends are supported:

.. autosummary::
    :toctree:
    :nosignatures:

    Artifactory
    FileSystem
    Minio

Users can implement their own
backend by deriving from
:class:`audbackend.backend.Base`.

.. autosummary::
    :toctree:
    :nosignatures:

    Base
