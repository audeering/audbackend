.. set temporal working directory
.. jupyter-execute::
    :hide-code:

    import os
    import audeer

    _cwd_root = os.getcwd()
    _tmp_root = audeer.mkdir(os.path.join("docs", "tmp"))
    os.chdir(_tmp_root)


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

.. jupyter-execute::

    import audbackend

    audbackend.backend.FileSystem.create("./host", "repo")
    backend = audbackend.backend.FileSystem("./host", "repo")
    backend.open()
    interface = audbackend.interface.Maven(backend, extensions=["tar.gz"])

Afterwards we upload an TAR.GZ archive
and check that it is stored as expected.

.. jupyter-execute::

    import audeer
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        audeer.touch(audeer.path(tmp, "file.txt"))
        interface.put_archive(tmp, "/file.tar.gz", "1.0.0")

    audeer.list_file_names("./host", recursive=True, basenames=True)


.. reset working directory and clean up
.. jupyter-execute::
    :hide-code:

    import shutil
    os.chdir(_cwd_root)
    shutil.rmtree(_tmp_root)
