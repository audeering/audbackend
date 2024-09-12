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

To access data on a backend
we need a file system
to store the data.
We select the :class:`fsspec.DirFileSystem`.

>>> import fsspec
>>> import audeer
>>> path = audeer.mkdir("./repo")
>>> filesystem = fsspec.filesystem("dir", path=path)

Now we can wrap around a backend,
which manages how the data is stored.
Here, we use :class:`audbackend.Unversioned`.
It does not support versioning,
i.e. exactly one file exists for a backend path.

>>> import audbackend
>>> backend = audbackend.Unversioned(filesystem)

Now we can upload our first file to the backend.
Note,
it is important to provide an absolute path
from the root of the backend
by starting it with ``/``.

..
    >>> import audeer

>>> file = audeer.touch("file.txt")
>>> backend.put_file(file, "file.txt")

We check if the file exists on the backend.

>>> backend.exists("file.txt")
True

And access its meta information,
like its checksum.

>>> backend.checksum("file.txt")
'd41d8cd98f00b204e9800998ecf8427e'

We create a copy of the file
and verify it exists.

>>> backend.copy_file("file.txt", "copy/file.txt")
>>> backend.exists("copy/file.txt")
True

We move it to a new location.

>>> backend.move_file("copy/file.txt", "move/file.txt")
>>> backend.exists("copy/file.txt")
False
>>> backend.exists("move/file.txt")
True

We download the file
and store it as ``local.txt``.

>>> file = backend.get_file("file.txt", "local.txt")

It is possible to upload
one or more files
as an archive.
Here,
we select all files
stored under ``folder/``
and store them as ``folder.zip``
under the sub-path ``/archives/``
in the repository.

>>> folder = audeer.mkdir("./folder")
>>> _ = audeer.touch(folder, "file1.txt")
>>> _ = audeer.touch(folder, "file2.txt")
>>> backend.put_archive(folder, "archives/folder.zip")

When we download an archive
it is automatically extracted,
when using :meth:`audbackend.Unversioned.get_archive`
instead of :meth:`audbackend.Unversioned.get_file`.

>>> backend.get_archive("/archives/folder.zip", "downloaded_folder")
['file1.txt', 'file2.txt']

We can list all files
in the repository.

>>> backend.ls("/")
['/archives/folder.zip', '/file.txt', '/move/file.txt']

If we provide
a sub-path
(must end on ``"/"``),
a list with files that
start with the sub-path
is returned.

>>> backend.ls("/archives/")
['/archives/folder.zip']

We can remove files.

>>> backend.remove_file("file.txt")
>>> backend.remove_file("archives/folder.zip")
>>> backend.ls("/")
['/move/file.txt']

In the end we clean up,
by deleting the repository folder.

>>> audeer.rmdir(path)


.. _versioned-data-on-a-file-system:

Versioned data on a file system
-------------------------------

We start by creating a repository folder
and a :class:`ffspec.DirFileSystem` file system.

>>> path = audeer.mkdir("./repo")
>>> filesystem = fsspec.filesystem("dir", path=path)

This time we manage the files
with the :class:`audbackend.Versioned` backend.

>>> backend = audbackend.Versioned(backend)

We then upload a file
and assign version ``"1.0.0"`` to it.

.. skip: next "as it return '14' as output, do not know why"

>>> with open("file.txt", "w") as file:
...     file.write("Content v1.0.0")
>>> backend.put_file("file.txt", "file.txt", "1.0.0")

Now we change the file for version ``"2.0.0"``.

>>> with open("file.txt", "w") as file:
...     file.write("Content v2.0.0")
>>> backend.put_file("file.txt", "file.txt", "2.0.0")

If we inspect the content of the repository
it will return a list of tuples
containing file name and version.

>>> backend.ls("/")

We can also inspect the available versions
for a file.

>>> backend.versions("file.txt")

Or request it's latest version.

>>> backend.latest_version("file.txt")

We can copy a specific version of a file.

>>> backend.copy_file("file.txt", "copy/file.txt", version="1.0.0")
>>> backend.ls("/copy/")

Or all versions.

>>> backend.copy_file("file.txt", "copy/file.txt")
>>> backend.ls("copy/")

We move them to a new location.

>>> backend.move_file("copy/file.txt", "move/file.txt")
>>> backend.ls("move/")

When downloading a file,
we can select the desired version.

>>> path = backend.get_file("file.txt", "local.txt", "1.0.0")
>>> with open(path, "r") as file:
...     display(file.read())

When we are done,
we delete the repository.

>>> audeer.rmdir(path)
