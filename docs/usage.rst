Usage
=====

The aim of
:mod:`audbackend`
is to provide an
abstract interface for
any kind of file storage system.
Even those,
that have not been
invented yet :)

This tutorial is divided
into three parts.
Under :ref:`file-system-example`,
we show the basic usage
by means of a
standard file system.
In :ref:`backend-interface`
we introduce the concept
of a backend interface.
Under :ref:`develop-new-backend`,
we take a deep dive
and develop a backend
that stores files into
a SQLite_ database.

.. set temporal working directory
.. jupyter-execute::
    :hide-code:

    import os
    import audeer

    _cwd_root = os.getcwd()
    _tmp_root = audeer.mkdir(os.path.join('docs', 'tmp'))
    os.chdir(_tmp_root)


.. _file-system-example:

File-system example
-------------------

The class
:class:`audbackend.backend.FileSystem`
implements
:class:`audbackend.backend.Base`
for a standard file system.


We start by registering the class
(in fact,
the class is registered
by default,
but it doesn't hurt
if we do it again).

.. jupyter-execute::

    import audbackend

    audbackend.register('file-system', audbackend.backend.FileSystem)


To make sure we can keep track
of all existing backend instances,
we use :func:`audbackend.create`
to create a repository
instead of calling the class ourselves.
We provide three arguments:

* ``name``: the name under which the backend class is registered
* ``host``: the host address,
  in this case a folder on the local file system.
* ``repository``: the repository name,
  in this case a sub-folder within the ``host`` folder
  (it is possible to have several repositories
  on the same host).

.. jupyter-execute::
    :hide-output:

    audbackend.create('file-system', './host', 'repo')


This will create an empty repository
(in our case the folder ``'./host/repo/'``).
To view all available instances,
we would do:

.. jupyter-execute::

    audbackend.available()


We can access an existing repository with:

.. jupyter-execute::

    backend = audbackend.access('file-system', './host', 'repo')


To put a file on the backend,
we provide two path arguments.

* ``src_path``: path to a file on the local file system.
  This is the file we want to store on the backend.
* ``dst_path``: virtual path that represents the file on the backend.
  It serves as an alias that is understood by all backends.

With
:mod:`audbackend`
we can store different
versions of a file.
Hence,
we attach a
``version`` string
to the backend path.
Together they
provide a unique identifier
to the file.

.. jupyter-execute::

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, 'file.txt')
        with open(src_path, 'w') as fp:
            fp.write('Hello world')
        backend.put_file(src_path, '/file.txt', '1.0.0')


We check if the file exists on the backend.

.. jupyter-execute::

    backend.exists('/file.txt', '1.0.0')


And access its meta information.

.. jupyter-execute::

    backend.checksum('/file.txt', '1.0.0')

.. jupyter-execute::

    backend.date('/file.txt', '1.0.0')

.. jupyter-execute::

    backend.owner('/file.txt', '1.0.0')


We fetch the file
from the backend
and verify it has
the expected content.

.. jupyter-execute::

    path = backend.get_file('/file.txt', 'local.txt', '1.0.0')
    with open(path, 'r') as fp:
        display(fp.read())


Then we modify it and
publish it under a new version.

.. jupyter-execute::

    with open(path, 'a') as fp:
        fp.write('. Goodbye!')
    backend.put_file(path, '/file.txt', '2.0.0')


It is possible to upload
one or more files
as an archive.
Here,
we select the modified file
and put the archive
under the sub-path ``'/a/'``
on the backend.

.. jupyter-execute::

    backend.put_archive('.', '/a/file.zip', '1.0.0', files=[path])


When we get an archive from the backend
we can automatically extract it,
by using :meth:`audbackend.backend.FileSystem.get_archive`
instead of :meth:`audbackend.backend.FileSystem.get_file`.

.. jupyter-execute::

    paths = backend.get_archive('/a/file.zip', '.', '1.0.0')
    with open(paths[0], 'r') as fp:
        display(fp.read())


We can list the files
on a backend.
The result is
a sequence of tuples
``(path, version)``.
If we provide
a sub-path
(must end on ``'/'``),
a list with files that
start with the sub-path
is returned.

.. jupyter-execute::

    backend.ls('/')

.. jupyter-execute::

    backend.ls('/a/')

.. jupyter-execute::

    backend.ls('/file.txt')

.. jupyter-execute::

    backend.ls('/file.txt', latest_version=True)


We can also directly request
the version(s) of a path.

.. jupyter-execute::

    backend.versions('/file.txt')

.. jupyter-execute::

    backend.latest_version('/file.txt')


And we can remove files
from a backend.

.. jupyter-execute::

    backend.remove_file('/file.txt', '2.0.0')
    backend.remove_file('/a/file.zip', '1.0.0')
    backend.ls('/')


Or even delete the whole repository
with all its content.

.. jupyter-execute::

    audbackend.delete('file-system', 'host', 'repo')


If we now try to access the repository,
an error of type
:class:`audbackend.BackendError`
is raised,
which wraps the original
exception thrown by the backend.

.. jupyter-execute::

    try:
        audbackend.access('file-system', 'host', 'repo')
    except audbackend.BackendError as ex:
        display(str(ex.exception))


.. _backend-interface:

Backend interface
-----------------

By default,
a file is stored
on the backend with a version
(see :ref:`file-system-example`).
We can change this behavior
by using a different interface.
For instance,
if we are not interested
in versioning we can use
:class:`audbackend.interface.Unversioned`.

.. jupyter-execute::

    audbackend.create(
        'file-system',
        './host',
        'repo',
    )
    backend = audbackend.access(
        'file-system',
        './host',
        'repo',
        interface=audbackend.interface.Unversioned,
    )
    backend.put_file('local.txt', '/file-without-version.txt')
    backend.ls()

.. jupyter-execute::
    :hide-code:
    :hide-output:

    audbackend.delete('file-system', './host', 'repo')


We can also implement our own interface
by deriving from
:class:`audbackend.interface.Base`.
For instance,
we can create an interface
to manage user content.
It provides three functions:

* ``add_user()`` to register a user
* ``upload()`` to upload a file for user
* ``ls()`` to list the files of a user

We store user information
in a database under
``'/user.map'``.
To access and update
the database
we implement the following
helper class.


.. jupyter-execute::

    import shelve

    class UserDB:
        r"""User database.

        Temporarily get user database
        and write changes back to the backend.

        """
        def __init__(self, backend: audbackend.backend.Base):
            self.backend = backend

        def __enter__(self) -> shelve.Shelf:
            if self.backend.exists('/user.db'):
                self.backend.get_file('/user.db', '~.db')
                self._map = shelve.open('~.db', flag='w', writeback=True)
            else:
                self._map = shelve.open('~.db', writeback=True)
            return self._map

        def __exit__(self, exc_type, exc_val, exc_tb):
            self._map.close()
            self.backend.put_file('~.db', '/user.db')
            os.remove('~.db')


Now,
we implement the interface.

.. jupyter-execute::

    class UserContent(audbackend.interface.Base):

        def add_user(self, username: str, password: str):
            r"""Add user to database."""
            with UserDB(self.backend) as map:
                map[username] = password

        def upload(self, username: str, password: str, path: str):
            r"""Upload user file."""
            with UserDB(self.backend) as map:
                if username not in map or map[username] != password:
                    raise ValueError('User does not exist or wrong password.')
                self.backend.put_file(path, f'/{username}/{os.path.basename(path)}')

        def ls(self, username: str) -> list:
            r"""List files of user."""
            with UserDB(self.backend) as map:
                if username not in map:
                    return []
            return self.backend.ls(f'/{username}/')


Let's create a repository and access it
with our custom interface:

.. jupyter-execute::

    audbackend.create('file-system', tmp, 'repo')
    backend = audbackend.access('file-system', tmp, 'repo', interface=UserContent)

    backend.add_user('audeering', 'pa$$word')
    backend.upload('audeering', 'pa$$word', 'local.txt')
    backend.ls('audeering')


.. _develop-new-backend:

Develop new backend
-------------------

In the previous section
we have used an existing
backend implementation.
Now we develop a new backend
that implements
a SQLite_ database.

A new backend
should be implemented as a class
deriving from
:class:`audbackend.backend.Base`.
As can be seen in the file
:file:`audbackend/core/backend.py`,
we need to implement the following private methods:

* ``_access()``
* ``_checksum()``
* ``_create()``
* ``_date()``
* ``_delete()``
* ``_exists()``
* ``_get_file()``
* ``_ls()``
* ``_owner()``
* ``_put_file()``
* ``_remove_file()``

We call the class ``SQLite``.
and we add two more attributes
in the constructor:

* ``_path``: the path of the database,
  which we derive from the host and repository,
  namely ``'<host>/<repository>/db'``.
* ``_db``: connection object to the database.

.. jupyter-execute::

    import audbackend
    import os

    class SQLite(audbackend.backend.Base):

        def __init__(
                self,
                host: str,
                repository: str,
        ):
            super().__init__(host, repository)
            self._path = os.path.join(host, repository, 'db')
            self._db = None


Obviously,
this is not yet a fully
functional backend implementation.
But for the sake of clarity,
we will dynamically add
the required methods one after another
using a dedicated decorator:

.. jupyter-execute::

    import functools

    def add_method(cls):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(self, *args, **kwargs):
                return func(self, *args, **kwargs)
            setattr(cls, func.__name__, wrapper)
            return func
        return decorator

For instance,
to ensure the connection to the database
is properly closed,
we add a destructor method.
This is not mandatory
and whether it is needed
depends on the backend.

.. jupyter-execute::

    @add_method(SQLite)
    def __del__(self):
        if self._db is not None:
            self._db.close()


We now register our new backend class
under the name ``'sql'``.

.. jupyter-execute::

    audbackend.register('sql', SQLite)


Before we can instantiate an instance,
we implement a method that
creates a new database
(or raises an error if it exists).
And add a table ``data``
that holds the content
and meta information of the files
stored on our backend:

* ``path``: the (virtual) backend path
* ``checksum``: the checksum
* ``content``: the binary content
* ``date``: the date when the file was added
* ``owner``: the owner of the file

.. jupyter-execute::

    import errno
    import os
    import sqlite3 as sl

    @add_method(SQLite)
    def _create(
            self,
    ):
        if os.path.exists(self._path):
            raise FileExistsError(
                errno.EEXIST,
                os.strerror(errno.EEXIST),
                self._path,
            )
        os.mkdir(os.path.dirname(self._path))
        self._db = sl.connect(self._path)
        query = '''
            CREATE TABLE data (
                path TEXT NOT NULL,
                checksum TEXT NOT NULL,
                content BLOB NOT NULL,
                date TEXT NOT NULL,
                owner TEXT NOT NULL,
                PRIMARY KEY (path)
            );
        '''
        with self._db as db:
            db.execute(query)


Now we create a repository.

.. jupyter-execute::
    :hide-output:

    audbackend.create('sql', 'host', 'repo')


We also add a method to access
an existing repository
(or raise an error if
it is not found).

.. jupyter-execute::

    @add_method(SQLite)
    def _access(
            self,
    ):
        if not os.path.exists(self._path):
            raise FileNotFoundError(
                errno.ENOENT,
                os.strerror(errno.ENOENT),
                self._path,
            )
        self._db = sl.connect(self._path)

    backend = audbackend.access('sql', 'host', 'repo')


Next,
we implement a method to check
if a file exists.

.. jupyter-execute::

    @add_method(SQLite)
    def _exists(
            self,
            path: str,
    ) -> bool:
        with self._db as db:
            query = f'''
                SELECT EXISTS (
                    SELECT 1
                        FROM data
                        WHERE path="{path}"
                );
            '''
            result = db.execute(query).fetchone()[0] == 1
        return result

    backend.exists('/file.txt', '1.0.0')


And a method that uploads
a file to our backend.

.. jupyter-execute::

    import datetime
    import getpass

    @add_method(SQLite)
    def _put_file(
            self,
            src_path: str,
            dst_path: str,
            checksum: str,
            verbose: bool,
    ):
        with self._db as db:
            with open(src_path, 'rb') as file:
                content = file.read()
            query = '''
                INSERT INTO data (path, checksum, content, date, owner)
                VALUES (?, ?, ?, ?, ?)
            '''
            owner = getpass.getuser()
            date = datetime.datetime.today().strftime('%Y-%m-%d')
            data = (dst_path, checksum, content, date, owner)
            db.execute(query, data)


Let's put a file on the backend.

.. jupyter-execute::

    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, 'file.txt')
        with open(src_path, 'w') as fp:
            fp.write('SQLite rocks!')
        backend.put_file(src_path, '/file.txt', '1.0.0')
    backend.exists('/file.txt', '1.0.0')


We need three more functions
to access its meta information.

.. jupyter-execute::

    @add_method(SQLite)
    def _checksum(
            self,
            path: str,
    ) -> str:
        with self._db as db:
            query = f'''
                SELECT checksum
                FROM data
                WHERE path="{path}"
            '''
            checksum = db.execute(query).fetchone()[0]
        return checksum

    backend.checksum('/file.txt', '1.0.0')

.. jupyter-execute::

    @add_method(SQLite)
    def _date(
            self,
            path: str,
    ) -> str:
        with self._db as db:
            query = f'''
                SELECT date
                FROM data
                WHERE path="{path}"
            '''
            date = db.execute(query).fetchone()[0]
        return date

    backend.date('/file.txt', '1.0.0')

.. jupyter-execute::

    @add_method(SQLite)
    def _owner(
            self,
            path: str,
    ) -> str:
        with self._db as db:
            query = f'''
                SELECT owner
                FROM data
                WHERE path="{path}"
            '''
            owner = db.execute(query).fetchone()[0]
        return owner

    backend.owner('/file.txt', '1.0.0')


Finally,
we implement a method
to fetch a file
from the backend.

.. jupyter-execute::

    @add_method(SQLite)
    def _get_file(
            self,
            src_path: str,
            dst_path: str,
            verbose: bool,
    ):
        with self._db as db:
            query = f'''
                SELECT content
                FROM data
                WHERE path="{src_path}"
            '''
            content = db.execute(query).fetchone()[0]
            with open(dst_path, 'wb') as fp:
                fp.write(content)


Let's verify the file we put on the backend
contains the expected content.

.. jupyter-execute::

    path = backend.get_file('/file.txt', 'local.txt', '1.0.0')
    with open(path, 'r') as fp:
        display(fp.read())


To inspect the files
on our backend
we provide a listing method.

.. jupyter-execute::

    import typing

    @add_method(SQLite)
    def _ls(
            self,
            path: str,
    ) -> typing.List[str]:

        with self._db as db:

            # list all files and versions under sub-path
            query = f'''
                SELECT path
                FROM data
                WHERE path
                LIKE ? || "%"
            '''
            ls = db.execute(query, [path]).fetchall()
            ls = [x[0] for x in ls]

        if not ls and not path == '/':
            # path has to exists if not root
            raise FileNotFoundError(
                errno.ENOENT,
                os.strerror(errno.ENOENT),
                path,
            )

        return ls


Let's test it.

.. jupyter-execute::

    backend.ls('/')

.. jupyter-execute::

    backend.ls('/file.txt')


To delete a file
from our backend
requires another method.

.. jupyter-execute::

    @add_method(SQLite)
    def _remove_file(
            self,
            path: str,
    ):
        with self._db as db:
            query = f'''
                DELETE
                FROM data
                WHERE path="{path}"
            '''
            db.execute(query)

    backend.remove_file('/file.txt', '1.0.0')
    backend.ls('/')


Finally,
we add a method that
deletes the database
and removes the repository
(or raises an error
if the database does not exist).

.. jupyter-execute::

    @add_method(SQLite)
    def _delete(
            self,
    ):
        if not os.path.exists(self._path):
            raise FileNotFoundError(
                errno.ENOENT,
                os.strerror(errno.ENOENT),
                self._path,
            )
        os.remove(self._path)
        os.rmdir(os.path.dirname(self._path))

    audbackend.delete('sql', 'host', 'repo')


Let's check if the repository
is really gone.

.. jupyter-execute::

    try:
        audbackend.access('sql', 'host', 'repo')
    except audbackend.BackendError as ex:
        display(str(ex.exception))


And that's it,
we have a fully functional backend.

Voilà!


.. reset working directory and clean up
.. jupyter-execute::
    :hide-code:

    import shutil
    os.chdir(_cwd_root)
    shutil.rmtree(_tmp_root)


.. _SQLite: https://sqlite.org/index.html
