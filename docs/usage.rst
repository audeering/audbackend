.. set temporal working directory
.. jupyter-execute::
    :hide-code:

    import os
    import audeer

    _cwd_root = os.getcwd()
    _tmp_root = audeer.mkdir("docs", "tmp-usage")
    os.chdir(_tmp_root)


.. _usage:

Usage
=====

With the help of :mod:`audbackend`
a user can store files
in a repository
on a storage system
(backend).

File access is handled
via an :ref:`interface <interfaces>`,
which defines how the data is structured
and presented to the user.
In addition,
:mod:`audbackend` supports different storage systems,
so called :ref:`backends <backends>`.


.. _unversioned-data-on-a-file-system:

Unversioned data on a file system
---------------------------------

To store data on a backend
we need to create a repository first.
We select the :class:`audbackend.backend.FileSystem` backend.

.. jupyter-execute::
    :hide-output:

    import audbackend

    audbackend.backend.FileSystem.create("./host", "repo")

Once we have an existing repository,
we can access it by instantiating the backend class.
For some backends we have to establish a connection first.
This can be achieved using a ``with`` statement,
or by calling ``backend.open()`` at the beginning,
and ``backend.close()`` at the end.
If you are unsure
whether your backend requires this step,
just do it always.

.. jupyter-execute::

    backend = audbackend.backend.FileSystem("./host", "repo")
    backend.open()

After establishing a connection
we could directly execute read and write operations
on the backend object.
However,
we recommend to always use
:mod:`interfaces <audbackend.interface>`
to communicate with a backend.
Here, we use :class:`audbackend.interface.Unversioned`.
It does not support versioning,
i.e. exactly one file exists for a backend path.

.. jupyter-execute::

    interface = audbackend.interface.Unversioned(backend)

Now we can upload our first file to the repository.
Note,
it is important to provide an absolute path
from the root of the repository
by starting it with ``/``.

.. jupyter-execute::

    import audeer

    file = audeer.touch("file.txt")
    interface.put_file(file, "/file.txt")

We check if the file exists in the repository.

.. jupyter-execute::

    interface.exists("/file.txt")

And access its meta information,
like its checksum.

.. jupyter-execute::

    interface.checksum("/file.txt")

Its creation date.

.. jupyter-execute::

    interface.date("/file.txt")

Or the owner who uploaded the file.

.. jupyter-execute::

    interface.owner("/file.txt")

We create a copy of the file
and verify it exists.

.. jupyter-execute::

    interface.copy_file("/file.txt", "/copy/file.txt")
    interface.exists("/copy/file.txt")

We move it to a new location.

.. jupyter-execute::

    interface.move_file("/copy/file.txt", "/move/file.txt")
    interface.exists("/copy/file.txt"), interface.exists("/move/file.txt")

We download the file
and store it as ``local.txt``.

.. jupyter-execute::

    file = interface.get_file("/file.txt", "local.txt")

It is possible to upload
one or more files
as an archive.
Here,
we select all files
stored under ``folder/``
and store them as ``folder.zip``
under the sub-path ``/archives/``
in the repository.

.. jupyter-execute::

    folder = audeer.mkdir("./folder")
    audeer.touch(folder, "file1.txt")
    audeer.touch(folder, "file2.txt")
    interface.put_archive(folder, "/archives/folder.zip")

When we download an archive
it is automatically extracted,
when using :meth:`audbackend.interface.Unversioned.get_archive`
instead of :meth:`audbackend.interface.Unversioned.get_file`.

.. jupyter-execute::

    paths = interface.get_archive("/archives/folder.zip", "downloaded_folder")
    paths

We can list all files
in the repository.

.. jupyter-execute::

    interface.ls("/")

If we provide
a sub-path
(must end on ``"/"``),
a list with files that
start with the sub-path
is returned.

.. jupyter-execute::

    interface.ls("/archives/")

We can remove files.

.. jupyter-execute::

    interface.remove_file("/file.txt")
    interface.remove_file("/archives/folder.zip")
    interface.ls("/")

Finally,
we close the connection to the backend.

.. jupyter-execute::

    backend.close()

And delete the whole repository
with all its content.

.. jupyter-execute::

    audbackend.backend.FileSystem.delete("host", "repo")

Now,
if we try to open the repository again,
we will get an error
(note that this behavior is not guaranteed
for all backend classes
as it depends on the implementation).

.. jupyter-execute::

    try:
        backend.open()
    except audbackend.BackendError as ex:
        display(str(ex.exception))


.. _versioned-data-on-a-file-system:

Versioned data on a file system
-------------------------------

We start by creating a repository
on the :class:`audbackend.backend.FileSystem` backend.
This time we access it
with the :class:`audbackend.interface.Versioned` interface
(which is also used by default).

.. jupyter-execute::

    audbackend.backend.FileSystem.create("./host", "repo")
    backend = audbackend.backend.FileSystem("./host", "repo")
    backend.open()
    interface = audbackend.interface.Versioned(backend)

We then upload a file
and assign version ``"1.0.0"`` to it.

.. jupyter-execute::

    with open("file.txt", "w") as file:
        file.write("Content v1.0.0")
    interface.put_file("file.txt", "/file.txt", "1.0.0")

Now we change the file for version ``"2.0.0"``.

.. jupyter-execute::

    with open("file.txt", "w") as file:
        file.write("Content v2.0.0")
    interface.put_file("file.txt", "/file.txt", "2.0.0")

If we inspect the content of the repository
it will return a list of tuples
containing file name and version.

.. jupyter-execute::

    interface.ls("/")

We can also inspect the available versions
for a file.

.. jupyter-execute::

    interface.versions("/file.txt")

Or request it's latest version.

.. jupyter-execute::

    interface.latest_version("/file.txt")

We can copy a specific version of a file.

.. jupyter-execute::

    interface.copy_file("/file.txt", "/copy/file.txt", version="1.0.0")
    interface.ls("/copy/")

Or all versions.

.. jupyter-execute::

    interface.copy_file("/file.txt", "/copy/file.txt")
    interface.ls("/copy/")

We move them to a new location.

.. jupyter-execute::

    interface.move_file("/copy/file.txt", "/move/file.txt")
    interface.ls("/move/")

When downloading a file,
we can select the desired version.

.. jupyter-execute::

    path = interface.get_file("/file.txt", "local.txt", "1.0.0")
    with open(path, "r") as file:
        display(file.read())

When we are done,
we close the connection to the repository.

.. jupyter-execute::

    backend.close()

.. reset working directory and clean up
.. jupyter-execute::
    :hide-code:

    import shutil
    os.chdir(_cwd_root)
    shutil.rmtree(_tmp_root)
