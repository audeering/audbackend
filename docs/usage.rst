Usage
=====

The aim of
:mod:`audbackend`
is to provide an abstract layer
to interface with different
file storage systems.
Instead of directly communicating
with a specific file system,
developers interact
with the abstract class
:class:`audbackend.Backend`.
And only at run-time will
address a concrete system.
This allows users to
execute the same code
on different file systems.

In this tutorial
we will step-by-step
show how to
implement a file system
that is backed by a
single SQLite_ database.

.. set temporal working directory
.. jupyter-execute::
    :hide-code:

    import os
    import audeer

    _cwd_root = os.getcwd()
    _tmp_root = audeer.mkdir(os.path.join('docs', 'tmp'))
    os.chdir(_tmp_root)

.. helper functions
.. jupyter-execute::
    :hide-code:

    import functools

    def add_method(cls):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(self, *args, **kwargs):
                return func(self, *args, **kwargs)
            setattr(cls, func.__name__, wrapper)
            return func
        return decorator


SQLite class
------------

To implement a new backend
we derive from
:class:`audbackend.Backend`.
The constructor takes two arguments:

* ``host``: the host address
* ``repository``: the repository name

We add two hidden class variables:

* ``_path``: the path of the database
* ``_con``: a connection object to the database

To ensure the connection to the database
is properly closed,
we implement a destructor method.
Other methods we will add
dynamically when needed.


.. jupyter-execute::

    import audbackend
    import audeer

    class SQLite(audbackend.Backend):

        def __init__(
                self,
                host: str,
                repository: str,
        ):
            super().__init__(host, repository)
            self._path = audeer.path(host, repository, 'db')
            self._con = None

        def __del__(self):
            if self._con is not None:
                self._con.close()


We now register our new backend class
under the name ``'sql'``.


.. jupyter-execute::

    audbackend.register('sql', SQLite)


Before we can create
an instance of our class,
we implement a method that
creates a new database
or raises an error if it exists.
We add a table ``data``
that holds the following
information about a file
that is stored on our backend:

* ``path``: the (virtual) backend path
* ``checksum``: the checksum
* ``content``: the content stored as a blob
* ``date``: the date when the file was added
* ``owner``: the owner of the file
* ``version``: the version of the file


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
        self._con = sl.connect(self._path)
        query = '''
            CREATE TABLE data (
                path TEXT PRIMARY KEY,
                checksum TEXT NOT NULL,
                content BLOB NOT NULL,
                date TEXT NOT NULL,
                owner TEXT NOT NULL,
                version TEXT NOT NULL
            );
        '''
        with self._con as con:
            con.execute(query)


Now we create the host
and instantiate an instance.

.. jupyter-execute::

    os.mkdir('host')
    audbackend.create('sql', 'host', 'repo')


Once the database exists,
we need a method to access it
or raises an error
if the database is not found.


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
        self._con = sl.connect(self._path)

    backend = audbackend.access('sql', 'host', 'repo')


Before we can actually
add something to our backend,
we need a method that checks
if a file exists.


.. jupyter-execute::

    @add_method(SQLite)
    def _exists(
            self,
            path: str,
            version: str,
    ) -> bool:
        with self._con as con:
            query = f'''
                SELECT EXISTS (
                    SELECT 1
                        FROM data
                        WHERE path="{path}" AND version="{version}"
                );
            '''
            result = con.execute(query).fetchone()[0] == 1
        return result

    backend.exists('/file.txt', '1.0.0')


Since no files exists on our backend yet,
the expected result is ``False``.
We can change that by implementing
a method that stores
a file to our backend.
It is important to note
that the function takes
two path arguments:

* ``src_path``: path to a file on the local file system
* ``dst_path``: virtual path that represents the file on the backend


.. jupyter-execute::

    import datetime

    @add_method(SQLite)
    def _put_file(
            self,
            src_path: str,
            dst_path: str,
            version: str,
            checksum: str,
            verbose: bool,
    ):
        with self._con as con:
            with open(src_path, 'rb') as file:
                content = file.read()
            query = '''
                INSERT INTO data (path, checksum, content, date, owner, version)
                VALUES (?, ?, ?, ?, ?, ?)
            '''
            owner = os.getlogin()
            date = datetime.datetime.today().strftime('%Y-%m-%d')
            data = (dst_path, checksum, content, date, owner, version)
            con.execute(query, data)


We create a temporal file
with some content and
upload it to the backend:


.. jupyter-execute::

    import tempfile

    with tempfile.NamedTemporaryFile() as tmp:
        tmp.write(b'Hello world!')
        backend.put_file(tmp.name, '/file.txt', '1.0.0')
    backend.exists('/file.txt', '1.0.0')


To access meta information
about a file on the backend,
we implement three more methods.


.. jupyter-execute::

    @add_method(SQLite)
    def _checksum(
            self,
            path: str,
            version: str,
    ) -> str:
        with self._con as con:
            query = f'''
                SELECT checksum
                FROM data
                WHERE path="{path}" AND version="{version}"
            '''
            checksum = con.execute(query).fetchone()[0]
        return checksum

    backend.checksum('/file.txt', '1.0.0')


.. jupyter-execute::

    @add_method(SQLite)
    def _date(
            self,
            path: str,
            version: str,
    ) -> str:
        with self._con as con:
            query = f'''
                SELECT date
                FROM data
                WHERE path="{path}" AND version="{version}"
            '''
            checksum = con.execute(query).fetchone()[0]
        return checksum

    backend.date('/file.txt', '1.0.0')


.. jupyter-execute::

    @add_method(SQLite)
    def _owner(
            self,
            path: str,
            version: str,
    ) -> str:
        with self._con as con:
            query = f'''
                SELECT owner
                FROM data
                WHERE path="{path}" AND version="{version}"
            '''
            checksum = con.execute(query).fetchone()[0]
        return checksum

    backend.owner('/file.txt', '1.0.0')


Finally,
we implement a method
that actually gets the file
back from the backend.


.. jupyter-execute::

    @add_method(SQLite)
    def _get_file(
                self,
                src_path: str,
                dst_path: str,
                version: str,
                verbose: bool,
        ):
        with self._con as con:
            query = f'''
                SELECT content
                FROM data
                WHERE path="{src_path}" AND version="{version}"
            '''
            content = con.execute(query).fetchone()[0]
            with open(dst_path, 'wb') as fp:
                fp.write(content)

    path = backend.get_file(
        '/file.txt',
        'local.txt',
        '1.0.0',
    )
    with open(path, 'rb') as fp:
        display(fp.read())


.. reset working directory and clean up
.. jupyter-execute::
    :hide-code:

    import shutil
    os.chdir(_cwd_root)
    shutil.rmtree(_tmp_root)


.. _SQLite: https://sqlite.org/index.html
