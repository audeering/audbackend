==========
audbackend
==========

|tests| |coverage| |docs| |python-versions| |license|

Manage file storage on different backends.

At the moment we support
the following backends:

* Artifactory_ with ``audbackend.backend.Artifactory``
* local file system with ``audbackend.backend.FileSystem``

And the following interfaces
to access files on a backend:

* unversioned with ``audbackend.interface.Unversioned``
* versioned with  ``audbackend.interface.Versioned``

Have a look at the installation_ instructions.

.. _Artifactory: https://jfrog.com/artifactory/
.. _installation: https://audeering.github.io/audbackend/install.html


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
