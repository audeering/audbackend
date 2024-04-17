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

Users can implement their own
backend by deriving from
:class:`audbackend.backend.Base`,
or :class:`audbackend.backend.BaseAuthentication`.

.. autosummary::
    :toctree:
    :nosignatures:

    Base
    BaseAuthentication
