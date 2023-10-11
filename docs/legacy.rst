.. set temporal working directory
.. jupyter-execute::
    :hide-code:

    import os
    import audeer

    _cwd_root = os.getcwd()
    _tmp_root = audeer.mkdir(os.path.join('docs', 'tmp'))
    os.chdir(_tmp_root)


.. _legacy-backends:

Legacy backends
===============

The file structure on the backend
has changed for
:class:`audbackend.FileSystem`
and :class:`audbackend.Artifactory`
in version 1.0.0
of :mod:`audbackend`.

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
call the hidden method
``_use_legacy_file_structure()``
after instantiating the backend.
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

    backend = audbackend.create('file-system', './host', 'repo')
    extensions = ['tar.gz']
    backend._use_legacy_file_structure(extensions=extensions)

Afterwards we upload an TAR.GZ archive
and check that it is stored as expected.

.. jupyter-execute::

    import audeer
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        audeer.touch(audeer.path(tmp, 'file.txt'))
        backend.put_archive(tmp, '/file.tar.gz', '1.0.0')

    audeer.list_file_names('./host', recursive=True, basenames=True)


.. reset working directory and clean up
.. jupyter-execute::
    :hide-code:

    import shutil
    os.chdir(_cwd_root)
    shutil.rmtree(_tmp_root)
