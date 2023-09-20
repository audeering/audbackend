Installation
============

To install :mod:`audbackend` run:

.. code-block:: bash

    $ # Create and activate Python virtual environment, e.g.
    $ # virtualenv --python=python3 ${HOME}/.envs/audbackend
    $ # source ${HOME}/.envs/audbackend/bin/activate
    $ pip install audbackend

By default,
only the :class:`audbackend.FileSystem` backend will be installed.
To install all backends run:

.. code-block:: bash

    $ pip install audbackend[all]

or select single backends,
e.g. :class:`audbackend.Artifactory`

.. code-block:: bash

    $ pip install audbackend[artifactory]
