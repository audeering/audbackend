Installation
============

To install :mod:`audbackend` run:

.. code-block:: bash

    $ uv pip install audbackend

By default,
only the :class:`audbackend.backend.FileSystem`
backend will be installed.
To install all backends run:

.. code-block:: bash

    $ uv pip install audbackend[all]

You can also select single backends,
e.g. :class:`audbackend.backend.Minio`:

.. code-block:: bash

    $ uv pip install audbackend[minio]
