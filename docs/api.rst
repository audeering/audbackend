audbackend
==========

.. automodule:: audbackend

A backend is an interface
to a host
that stores meta
and media files
of a database
in a repository.

Currently the following backends
are shipped with :mod:`audbackend`:

Artifactory
-----------

.. autoclass:: Artifactory

FileSystem
----------

.. autoclass:: FileSystem

Users can implement their own
backend by deriving from
:class:`audbackend.Backend`.

Backend
-------

.. autoclass:: Backend
    :members:

create
------

.. autofunction:: create

md5
---

.. autofunction:: md5

register
--------

.. autofunction:: register
