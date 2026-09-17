Contributing
============

Everyone is invited to contribute to this project.
Feel free to create a `pull request`_ .
If you find errors,
omissions,
inconsistencies,
or other things
that need improvement,
please create an issue_.

.. _issue: https://github.com/audeering/audbackend/issues/new/
.. _pull request: https://github.com/audeering/audbackend/compare/


Development Installation
------------------------

Instead of installing the latest release from PyPI_,
you should get the newest development version from Github_::

    git clone https://github.com/audeering/audbackend/
    cd audbackend
    uv sync


This way,
your installation always stays up-to-date,
even if you pull new changes from the Github repository.

.. _PyPI: https://pypi.org/project/audbackend/
.. _Github: https://github.com/audeering/audbackend/


Coding Convention
-----------------

We follow the PEP8_ convention for Python code
and use ruff_ as a linter and code formatter.
In addition,
we check for common spelling errors with codespell_.
Both tools and possible exceptions
are defined in :file:`pyproject.toml`.

The checks are executed in the CI using `pre-commit`_.
You can enable those checks locally by executing::

    uvx pre-commit install
    uvx pre-commit run --all-files

Afterwards ruff_ and codespell_ are executed
every time you create a commit.

Alternatively,
you can run ruff_ and codespell_ directly using ``uvx``::

    uvx ruff check --fix .  # lint all Python files, and fix any fixable errors
    uvx ruff format .  # format code of all Python files
    uvx codespell

It can be restricted to specific folders::

    uvx ruff check audbackend/ tests/
    uvx codespell audbackend/ tests/


.. _codespell: https://github.com/codespell-project/codespell/
.. _PEP8: http://www.python.org/dev/peps/pep-0008/
.. _pre-commit: https://pre-commit.com
.. _ruff: https://beta.ruff.rs


Building the Documentation
--------------------------

If you make changes to the documentation,
you can re-create the HTML pages using Sphinx_::

    uv run python -m sphinx docs/ build/html -b html

The generated files will be available
in the directory :file:`build/html/`.

It is also possible to automatically check if all links are still valid::

    uv run python -m sphinx docs/ build/html -b linkcheck

.. _Sphinx: http://sphinx-doc.org


Running the Tests
-----------------

Some of the tests need a MinIO server.
MinIO has archived its community server
and shut down its public playground at play.min.io,
so start the last community release on your own machine::

    docker compose up -d

Docker Compose and ``podman-compose``
both read the provided :file:`compose.yaml`.
The server listens on ``127.0.0.1:9000``
and needs a moment to come up;
``docker compose ps`` reports it as healthy.
The test fixtures default to that address
and to its ``minioadmin`` credentials,
so no further configuration is needed.

You can then run tests with pytest_::

    uv run pytest

When you are done,
stop and remove the server again::

    docker compose down

To use a different server,
point ``AUDBACKEND_TEST_MINIO_HOST`` at it
and set ``MINIO_ACCESS_KEY`` and ``MINIO_SECRET_KEY``.
A server without TLS needs a config file as well,
as ``secure`` can only be set there,
see :meth:`audbackend.backend.Minio.get_config`::

    export MINIO_CONFIG_FILE=~/my-minio.cfg

.. code-block:: ini

    [my-server:9000]
    secure = False

.. _pytest: https://pytest.org


Creating a New Release
----------------------

New releases are made using the following steps:

#. Update ``CHANGELOG.rst``
#. Commit those changes as "Release X.Y.Z"
#. Create an (annotated) tag with ``git tag -a X.Y.Z``
#. Push the commit and the tag to Github
