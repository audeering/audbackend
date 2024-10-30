==========
audbackend
==========

|tests| |coverage| |docs| |python-versions| |license|

**audbackend** provides interfaces_
for file storage on different backends_.

An interface enables user interactions
with a backend,
and influences how the data is structured,
e.g. `versioned`_
or `unversioned`_.
A backend is responsible
for managing
the requested data structure
in a repository
on a storage system,
such as a file system
or MinIO_.

Have a look at the installation_ and usage_ instructions.

.. _MinIO: https://min.io
.. _backends: https://audeering.github.io/audbackend/api/audbackend.backend.html
.. _interfaces: https://audeering.github.io/audbackend/api/audbackend.interface.html
.. _installation: https://audeering.github.io/audbackend/install.html
.. _unversioned: https://audeering.github.io/audbackend/api/audbackend.interface.Unversioned.html
.. _usage: https://audeering.github.io/audbackend/usage.html
.. _versioned: https://audeering.github.io/audbackend/api/audbackend.interface.Versioned.html


.. badges images and links:
.. |tests| image:: https://github.com/audeering/audbackend/workflows/Test/badge.svg
    :target: https://github.com/audeering/audbackend/actions?query=workflow%3ATest
    :alt: Test status
.. |coverage| image:: https://codecov.io/gh/audeering/audbackend/branch/main/graph/badge.svg?token=pCTgGG7Sd1
    :target: https://codecov.io/gh/audeering/audbackend/
    :alt: code coverage
.. |docs| image:: https://img.shields.io/pypi/v/audbackend?label=docs
    :target: https://audeering.github.io/audbackend/
    :alt: audbackend's documentation
.. |license| image:: https://img.shields.io/badge/license-MIT-green.svg
    :target: https://github.com/audeering/audbackend/blob/main/LICENSE
    :alt: audbackend's MIT license
.. |python-versions| image:: https://img.shields.io/pypi/pyversions/audbackend.svg
    :target: https://pypi.org/project/audbackend/
    :alt: audbackends's supported Python versions
