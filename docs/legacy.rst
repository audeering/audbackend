.. _legacy-backends:

Legacy backends
===============

The default file structure on the backend
has changed with version 1.0.0.

Before,
a file ``/sub/file.txt``
with version ``1.0.0``
was stored under

.. code-block::

    /sub/file/1.0.0/file-1.0.0.txt

Now it is stored under

.. code-block::

    /sub/1.0.0/file.txt

To force the old file structure
use the :class:`audbackend.interface.Maven` interface.
We recommend this 
for existing repositories
that store files
under the old structure.
If you have to store files
that contain a dot
in its file extension,
you have to list those extensions explicitly.

.. code-block:: python

    import audbackend
    import audeer


    host = audeer.mkdir("host")
    audbackend.backend.FileSystem.create(host, "repo")
    backend = audbackend.backend.FileSystem(host, "repo")
    backend.open()
    interface = audbackend.interface.Maven(backend, extensions=["tar.gz"])

Afterwards we upload an TAR.GZ archive.

.. code-block:: python

    import tempfile


    with tempfile.TemporaryDirectory() as tmp:
        audeer.touch(audeer.path(tmp, "file.txt"))
        interface.put_archive(tmp, "/file.tar.gz", "1.0.0")

And check that it is stored as expected.

>>> files = audeer.list_file_names(host, recursive=True, basenames=True)
>>> from pathlib import Path
>>> [Path(file).as_posix() for file in files]
['repo/file/1.0.0/file-1.0.0.tar.gz']
