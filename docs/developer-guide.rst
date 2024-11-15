.. _developer-guide:

Developer guide
===============

The aim of
:mod:`audbackend`
is to provide an
abstract interface for
any kind of file storage system.
Even those,
that have not been
invented yet :)

This tutorial is divided
into two parts.
In :ref:`develop-new-interface`,
we show how to create a custom interface
that manages user content.
Under :ref:`develop-new-backend`,
we take a deep dive
and develop a backend
that stores files into
a SQLite_ database.


.. _develop-new-interface:

Develop new interface
---------------------

We can implement our own interface
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
``"/user.map"``.
To access and update
the database
we implement the following
helper class.


.. code-block:: python

    import os
    import pickle

    import audbackend


    class UserDB:
        r"""User database.

        Temporarily get user database
        and write changes back to the backend.

        """
        def __init__(self, backend: audbackend.backend.Base):
            self.backend = backend
            self.remote_file = "/.db.pkl"
            self.local_file = audeer.path(".db.pkl")

        def __enter__(self) -> dict:
            if self.backend.exists(self.remote_file):
                self.backend.get_file(self.remote_file, self.local_file)
            if os.path.exists(self.local_file):
                with open(self.local_file, "rb") as file:
                    self._map = pickle.load(file)
            else:
                self._map = {}
            return self._map

        def __exit__(self, exc_type, exc_val, exc_tb):
            with open(self.local_file, "wb") as file:
                pickle.dump(self._map, file, protocol=pickle.HIGHEST_PROTOCOL)
            self.backend.put_file(self.local_file, self.remote_file)
            os.remove(self.local_file)

Now,
we implement the interface.

.. code-block:: python

    class UserContent(audbackend.interface.Base):

        def add_user(self, username: str, password: str):
            r"""Add user to database."""
            with UserDB(self.backend) as map:
                map[username] = password

        def upload(self, username: str, password: str, path: str):
            r"""Upload user file."""
            with UserDB(self.backend) as map:
                if username not in map or map[username] != password:
                    raise ValueError("User does not exist or wrong password.")
                self.backend.put_file(path, f"/{username}/{os.path.basename(path)}")

        def ls(self, username: str) -> list:
            r"""List files of user."""
            with UserDB(self.backend) as map:
                if username not in map:
                    return []
            return self.backend.ls(f"/{username}/")


Let's create a repository
with our custom interface,
and upload a file:


>>> import audeer
>>> host = audeer.mkdir("host")
>>> audbackend.backend.FileSystem.create(host, "repo")
>>> backend = audbackend.backend.FileSystem(host, "repo")
>>> backend.open()
>>> interface = UserContent(backend)
>>> interface.add_user("audeering", "pa$$word")
>>> file = audeer.touch("local.txt")
>>> interface.upload("audeering", "pa$$word", file)
>>> interface.ls("audeering")
['/audeering/local.txt']


At the end we clean up and delete our repo.

>>> backend.close()
>>> audbackend.backend.FileSystem.delete(host, "repo")


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
:file:`audbackend/core/backend/base.py`,
we need to implement the following private methods:

* ``_access()``
* ``_checksum()``
* ``_close()``
* ``_create()``
* ``_date()``
* ``_delete()``
* ``_exists()``
* ``_get_file()``
* ``_ls()``
* ``_open()``
* ``_owner()``
* ``_put_file()``
* ``_remove_file()``

We call the class ``SQLite``.
and we add two more attributes
in the constructor:

* ``_path``: the path of the database,
  which we derive from the host and repository,
  namely ``"<host>/<repository>/db"``.
* ``_db``: connection object to the database.

.. code-block:: python

    import os

    import audbackend


    class SQLite(audbackend.backend.Base):

        def __init__(
                self,
                host: str,
                repository: str,
        ):
            super().__init__(host, repository)
            self._path = os.path.join(host, repository, "db")
            self._db = None


Obviously,
this is not yet a fully
functional backend implementation.
But for the sake of clarity,
we will dynamically add
the required methods one after another
using a dedicated decorator:

.. code-block:: python

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

.. code-block:: python

    @add_method(SQLite)
    def __del__(self):
        if self._db is not None:
            self._db.close()


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

.. code-block:: python

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
        query = """
            CREATE TABLE data (
                path TEXT NOT NULL,
                checksum TEXT NOT NULL,
                content BLOB NOT NULL,
                date TEXT NOT NULL,
                owner TEXT NOT NULL,
                PRIMARY KEY (path)
            );
        """
        with self._db as db:
            db.execute(query)

Now we create a repository.

>>> SQLite.create(host, "repo")

Before we can access the repository
we add a method to open
an existing database
(or raise an error
it is not found).

.. code-block:: python

    @add_method(SQLite)
    def _open(
            self,
    ):
        if not os.path.exists(self._path):
            raise FileNotFoundError(
                errno.ENOENT,
                os.strerror(errno.ENOENT),
                self._path,
            )
        self._db = sl.connect(self._path)

Now we instantiate an object of our backend
and access the repository we created.
We then wrap the object
with the :class:`audbackend.interface.Versioned` interface.

>>> backend = SQLite(host, "repo")
>>> backend.open()
>>> interface = audbackend.interface.Versioned(backend)

Next,
we implement a method to check
if a file exists.

.. code-block:: python

    @add_method(SQLite)
    def _exists(
            self,
            path: str,
    ) -> bool:
        with self._db as db:
            query = f"""
                SELECT EXISTS (
                    SELECT 1
                        FROM data
                        WHERE path="{path}"
                );
            """
            result = db.execute(query).fetchone()[0] == 1
        return result

>>> interface.exists("/file.txt", "1.0.0")
False

And a method that uploads
a file to our backend.

.. code-block:: python

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
            with open(src_path, "rb") as file:
                content = file.read()
            query = """
                INSERT INTO data (path, checksum, content, date, owner)
                VALUES (?, ?, ?, ?, ?)
            """
            owner = getpass.getuser()
            date = datetime.datetime.today().strftime("%Y-%m-%d")
            data = (dst_path, checksum, content, date, owner)
            db.execute(query, data)

Let's put a file on the backend.

>>> file = audeer.touch("file.txt")
>>> interface.put_file(file, "/file.txt", "1.0.0")
>>> interface.exists("/file.txt", "1.0.0")
True

We need three more functions
to access its meta information.

.. code-block:: python

    @add_method(SQLite)
    def _checksum(
            self,
            path: str,
    ) -> str:
        with self._db as db:
            query = f"""
                SELECT checksum
                FROM data
                WHERE path="{path}"
            """
            checksum = db.execute(query).fetchone()[0]
        return checksum

.. code-block:: python

    @add_method(SQLite)
    def _date(
            self,
            path: str,
    ) -> str:
        with self._db as db:
            query = f"""
                SELECT date
                FROM data
                WHERE path="{path}"
            """
            date = db.execute(query).fetchone()[0]
        return date

.. code-block:: python

    @add_method(SQLite)
    def _owner(
            self,
            path: str,
    ) -> str:
        with self._db as db:
            query = f"""
                SELECT owner
                FROM data
                WHERE path="{path}"
            """
            owner = db.execute(query).fetchone()[0]
        return owner

Implementing a copy function is optional.
But the default implementation
will temporarily download the file
and then upload it again.
Hence,
we provide a more efficient implementation.

.. code-block:: python

    @add_method(SQLite)
    def _copy_file(
            self,
            src_path: str,
            dst_path: str,
            verbose: bool,
    ):
        with self._db as db:
            query = f"""
                SELECT *
                FROM data
                WHERE path="{src_path}"
            """
            (_, checksum, content, _, owner) = db.execute(query).fetchone()
            date = datetime.datetime.today().strftime("%Y-%m-%d")
            query = """
                INSERT INTO data (path, checksum, content, date, owner)
                VALUES (?, ?, ?, ?, ?)
            """
            data = (dst_path, checksum, content, date, owner)
            db.execute(query, data)

>>> interface.copy_file("/file.txt", "/copy/file.txt", version="1.0.0")
>>> interface.exists("/copy/file.txt", "1.0.0")
True

Implementing a move function is also optional,
but it is more efficient if we provide one.

.. code-block:: python

    @add_method(SQLite)
    def _move_file(
            self,
            src_path: str,
            dst_path: str,
            verbose: bool,
    ):
        with self._db as db:
            query = f"""
                UPDATE data
                SET path="{dst_path}"
                WHERE path="{src_path}"
            """
            db.execute(query)

>>> interface.move_file("/copy/file.txt", "/move/file.txt", version="1.0.0")
>>> interface.exists("/move/file.txt", "1.0.0")
True

We implement a method
to fetch a file
from the backend.

.. code-block:: python

    @add_method(SQLite)
    def _get_file(
            self,
            src_path: str,
            dst_path: str,
            verbose: bool,
    ):
        with self._db as db:
            query = f"""
                SELECT content
                FROM data
                WHERE path="{src_path}"
            """
            content = db.execute(query).fetchone()[0]
            with open(dst_path, "wb") as fp:
                fp.write(content)

Which we then use to download the file.

>>> interface.get_file("/file.txt", audeer.path("local.txt"), "1.0.0")
'...local.txt'

To inspect the files
on our backend
we provide a listing method.

.. code-block:: python

    @add_method(SQLite)
    def _ls(
            self,
            path: str,
    ) -> list[str]:

        with self._db as db:

            # list all files and versions under sub-path
            query = f"""
                SELECT path
                FROM data
                WHERE path
                LIKE ? || "%"
            """
            ls = db.execute(query, [path]).fetchall()
            ls = [x[0] for x in ls]

        return ls

Let's test it.

>>> interface.ls("/")
[('/file.txt', '1.0.0'), ('/move/file.txt', '1.0.0')]
>>> interface.ls("/file.txt")
[('/file.txt', '1.0.0')]

To delete a file
from our backend
requires another method.

.. code-block:: python

    @add_method(SQLite)
    def _remove_file(
            self,
            path: str,
    ):
        with self._db as db:
            query = f"""
                DELETE
                FROM data
                WHERE path="{path}"
            """
            db.execute(query)

>>> interface.remove_file("/file.txt", "1.0.0")
>>> interface.ls("/")
[('/move/file.txt', '1.0.0')]

We add a method to close the connection
to a database and call it.

.. code-block:: python

    @add_method(SQLite)
    def _close(
            self,
    ):
        self._db.close()

>>> backend.close()

Finally,
we add a method that
deletes the database
and removes the repository
(or raises an error
if the database does not exist).

.. code-block:: python

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

>>> SQLite.delete(host, "repo")

And that's it,
we have a fully functional backend.

Voilà!

.. _SQLite: https://sqlite.org/index.html
