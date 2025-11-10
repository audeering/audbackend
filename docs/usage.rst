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

>>> import audbackend
>>> import audeer
>>> host = audeer.mkdir("host")
>>> audbackend.backend.FileSystem.create(host, "repo")

Once we have an existing repository,
we can access it by instantiating the backend class.
For some backends we have to establish a connection first.
This can be achieved using a ``with`` statement,
or by calling ``backend.open()`` at the beginning,
and ``backend.close()`` at the end.
If you are unsure
whether your backend requires this step,
just do it always.

>>> backend = audbackend.backend.FileSystem(host, "repo")
>>> backend.open()

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

>>> interface = audbackend.interface.Unversioned(backend)

Now we can upload our first file to the repository.
Note,
it is important to provide an absolute path
from the root of the repository
by starting it with ``/``.

>>> file = audeer.touch("file.txt")
>>> interface.put_file(file, "/file.txt")

We check if the file exists in the repository.

>>> interface.exists("/file.txt")
True

And access its meta information,
like its checksum.

>>> interface.checksum("/file.txt")
'd41d8cd98f00b204e9800998ecf8427e'

Its creation date.

..
    >>> interface.date = mock_date

>>> interface.date("/file.txt")
'1991-02-20'

Or the owner who uploaded the file.

..
    >>> interface.owner = mock_owner

>>> interface.owner("/file.txt")
'doctest'

We create a copy of the file
and verify it exists.

>>> interface.copy_file("/file.txt", "/copy/file.txt")
>>> interface.exists("/copy/file.txt")
True

We move it to a new location.

>>> interface.move_file("/copy/file.txt", "/move/file.txt")
>>> interface.exists("/copy/file.txt"), interface.exists("/move/file.txt")
(False, True)

We download the file
and store it as ``local.txt``.

>>> file = audeer.path("local.txt")
>>> interface.get_file("/file.txt", file)
'...local.txt'

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
>>> interface.put_archive(folder, "/archives/folder.zip")

When we download an archive
it is automatically extracted,
when using :meth:`audbackend.interface.Unversioned.get_archive`
instead of :meth:`audbackend.interface.Unversioned.get_file`.

>>> interface.get_archive("/archives/folder.zip", "downloaded_folder")
['file1.txt', 'file2.txt']

We can list all files
in the repository.

>>> interface.ls("/")
['/archives/folder.zip', '/file.txt', '/move/file.txt']

If we provide
a sub-path
(must end on ``"/"``),
a list with files that
start with the sub-path
is returned.

>>> interface.ls("/archives/")
['/archives/folder.zip']

We can remove files.

>>> interface.remove_file("/file.txt")
>>> interface.remove_file("/archives/folder.zip")
>>> interface.ls("/")
['/move/file.txt']

Finally,
we close the connection to the backend.

>>> backend.close()

And delete the whole repository
with all its content.

>>> audbackend.backend.FileSystem.delete(host, "repo")

Now,
if we try to open the repository again,
we will get an error
(note that this behavior is not guaranteed
for all backend classes
as it depends on the implementation).

>>> try:
...     backend.open()
... except audbackend.BackendError as ex:
...     print(str(ex.exception))
[Errno 2] No such file or directory: ...'


.. _versioned-data-on-a-file-system:

Versioned data on a file system
-------------------------------

We start by creating a repository
on the :class:`audbackend.backend.FileSystem` backend.
This time we access it
with the :class:`audbackend.interface.Versioned` interface
(which is also used by default).

>>> audbackend.backend.FileSystem.create(host, "repo")
>>> backend = audbackend.backend.FileSystem(host, "repo")
>>> backend.open()
>>> interface = audbackend.interface.Versioned(backend)

We then upload a file
and assign version ``"1.0.0"`` to it.

>>> file = audeer.path("file.txt")
>>> with open(file, "w") as fp:
...     _ = fp.write("Content v1.0.0")
>>> interface.put_file(file, "/file.txt", "1.0.0")

Now we change the file for version ``"2.0.0"``.

>>> with open(file, "w") as fp:
...     _ = fp.write("Content v2.0.0")
>>> interface.put_file(file, "/file.txt", "2.0.0")

If we inspect the content of the repository
it will return a list of tuples
containing file name and version.

>>> interface.ls("/")
[('/file.txt', '1.0.0'), ('/file.txt', '2.0.0')]

We can also inspect the available versions
for a file.

>>> interface.versions("/file.txt")
['1.0.0', '2.0.0']

Or request its latest version.

>>> interface.latest_version("/file.txt")
'2.0.0'

We can copy a specific version of a file.

>>> interface.copy_file("/file.txt", "/copy/file.txt", version="1.0.0")
>>> interface.ls("/copy/")
[('/copy/file.txt', '1.0.0')]

Or all versions.

>>> interface.copy_file("/file.txt", "/copy/file.txt")
>>> interface.ls("/copy/")
[('/copy/file.txt', '1.0.0'), ('/copy/file.txt', '2.0.0')]

We move them to a new location.

>>> interface.move_file("/copy/file.txt", "/move/file.txt")
>>> interface.ls("/move/")
[('/move/file.txt', '1.0.0'), ('/move/file.txt', '2.0.0')]

When downloading a file,
we can select the desired version.

>>> path = interface.get_file("/file.txt", audeer.path("local.txt"), "1.0.0")
>>> with open(path, "r") as file:
...     print(file.read())
Content v1.0.0

When we are done,
we close the connection to the repository.

>>> backend.close()
