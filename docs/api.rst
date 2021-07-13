audbackend
==========

.. automodule:: audbackend

A backend is a generic interface
for storing and accessing files
on a host.

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

Repository
----------

.. autoclass:: Repository
    :members:
