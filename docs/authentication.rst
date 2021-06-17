Authentication
==============

To use the :class:`audbackend.Artifactory` backend
store your credentials in :file:`~/.artifactory_python.cfg`:

.. code-block:: cfg

    [artifactory.audeering.com/artifactory]
    username = MY_USERNAME
    password = MY_API_KEY

and replace ``artifactory.audeering.com/artifactory``
with your Artifactory server address.
You can also add several server entries.

Alternatively, export the credentials as environment variables:

.. code-block:: bash

    export ARTIFACTORY_USERNAME="MY_USERNAME"
    export ARTIFACTORY_API_KEY="MY_API_KEY"

The environment variables will be applied to all servers.
You might loose access to artifacts on servers
that are setup for anonymous access
as it will always try to authenticate
with the given username and password.
In this case
it is recommended to not use the environment variables.
