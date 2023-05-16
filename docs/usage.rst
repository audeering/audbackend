Usage
=====

The aim of
:mod:`audbackend`
is to provide an abstract layer
to interface with different
file storage systems.
Instead of directly communicating
with a specific file system,
the abstract class
:class:`audbackend.Backend`.
This allows users to
execute the same code
on different systems.
For instance,
in this tutorial
we create a backend that
stores files into
a SQLite_ database.

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


To implement a new backend
we derive from
:class:`audbackend.Backend`.
The constructor takes two arguments:

* ``host``: the host address
* ``repository``: the repository name

In addition we add two hidden class variables:

* ``_path``: the path of the database,
  which we create from the host and repository,
  namely ``'<host>/<repository>/db'``.
* ``_db``: connection object to the database.

To ensure the connection to the database
is properly closed,
we also implement a destructor method.
There are of course more methods
we have to implement,
but for the sake of clarity
we will dynamically add
them when needed.

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
            self._db = None

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
        self._db = sl.connect(self._path)
        query = '''
            CREATE TABLE data (
                path TEXT NOT NULL,
                checksum TEXT NOT NULL,
                content BLOB NOT NULL,
                date TEXT NOT NULL,
                owner TEXT NOT NULL,
                version TEXT NOT NULL,
                PRIMARY KEY (path, version)
            );
        '''
        with self._db as db:
            db.execute(query)


Now we create the host
and instantiate an instance.

.. jupyter-execute::

    os.mkdir('host')
    audbackend.create('sql', 'host', 'repo')


We also add a method to access
an existing database
(or raise an error
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


Now that we have an instance
of the database,
we implement a method to check
if a file exists.

.. jupyter-execute::

    @add_method(SQLite)
    def _exists(
            self,
            path: str,
            version: str,
    ) -> bool:
        with self._db as db:
            query = f'''
                SELECT EXISTS (
                    SELECT 1
                        FROM data
                        WHERE path="{path}" AND version="{version}"
                );
            '''
            result = db.execute(query).fetchone()[0] == 1
        return result

    backend.exists('/file.txt', '1.0.0')


Next,
we implement
a method to upload
files to our backend.
The function takes
two path arguments:

* ``src_path``: path to a file on the local file system.
  This is the file we want to store on the backend.
* ``dst_path``: virtual path that represents the file on the backend.
  It is called virtual because it is
  the same on all backends,
  while under the hood backends
  may use a completely different structure.

When a file is put on the backend
it exists independent of the original file.
The backend path and
``version`` string
provide a unique identifier
to the file.

.. jupyter-execute::

    import datetime
    import getpass

    @add_method(SQLite)
    def _put_file(
            self,
            src_path: str,
            dst_path: str,
            version: str,
            checksum: str,
            verbose: bool,
    ):
        with self._db as db:
            with open(src_path, 'rb') as file:
                content = file.read()
            query = '''
                INSERT INTO data (path, checksum, content, date, owner, version)
                VALUES (?, ?, ?, ?, ?, ?)
            '''
            owner = getpass.getuser()
            date = datetime.datetime.today().strftime('%Y-%m-%d')
            data = (dst_path, checksum, content, date, owner, version)
            db.execute(query, data)


We create a temporal file
with some content and
upload it to the backend:

.. jupyter-execute::

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, '~')
        with open(src_path, 'w') as fp:
            fp.write('Hello world')
        backend.put_file(src_path, '/file.txt', '1.0.0')
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
        with self._db as db:
            query = f'''
                SELECT checksum
                FROM data
                WHERE path="{path}" AND version="{version}"
            '''
            checksum = db.execute(query).fetchone()[0]
        return checksum

    backend.checksum('/file.txt', '1.0.0')

.. jupyter-execute::

    @add_method(SQLite)
    def _date(
            self,
            path: str,
            version: str,
    ) -> str:
        with self._db as db:
            query = f'''
                SELECT date
                FROM data
                WHERE path="{path}" AND version="{version}"
            '''
            checksum = db.execute(query).fetchone()[0]
        return checksum

    backend.date('/file.txt', '1.0.0')

.. jupyter-execute::

    @add_method(SQLite)
    def _owner(
            self,
            path: str,
            version: str,
    ) -> str:
        with self._db as db:
            query = f'''
                SELECT owner
                FROM data
                WHERE path="{path}" AND version="{version}"
            '''
            checksum = db.execute(query).fetchone()[0]
        return checksum

    backend.owner('/file.txt', '1.0.0')


Finally,
we implement a method
to retrieve files
from the backend
and store it into a local file.

.. jupyter-execute::

    @add_method(SQLite)
    def _get_file(
                self,
                src_path: str,
                dst_path: str,
                version: str,
                verbose: bool,
        ):
        with self._db as db:
            query = f'''
                SELECT content
                FROM data
                WHERE path="{src_path}" AND version="{version}"
            '''
            content = db.execute(query).fetchone()[0]
            with open(dst_path, 'wb') as fp:
                fp.write(content)


We get a copy from the backend
and verify in contains the expected content.

.. jupyter-execute::

    path = backend.get_file('/file.txt', 'local.txt', '1.0.0')
    with open(path, 'r') as fp:
        display(fp.read())


Then we modify it and
store it again on the backend,
but under a different version.

.. jupyter-execute::

    with open(path, 'a') as fp:
        fp.write('. Goodbye!')
    backend.put_file(path, '/file.txt', '2.0.0')


We can also upload
the file as an archive
under a different sub-path
(``'/a/'``).

.. jupyter-execute::

    backend.put_archive('.', '/a/file.zip', '2.0.0', files=[path])


It is possible to automatically extract an archive
when retrieving it from backend.

.. jupyter-execute::

    paths = backend.get_archive('/a/file.zip', '.', '2.0.0')
    with open(paths[0], 'r') as fp:
        display(fp.read())


To inspect the files
on our backend
we add a listing method.
The return value
of the method is
list with tuples
``(path, version)``.
It is possible to list
files for a sub-path
(ends on ``'/'``).
In that case,
we return all paths
that start with that sub-path
(or raise an error
if it does not exist).


.. jupyter-execute::

    import typing

    @add_method(SQLite)
    def _ls(
            self,
            path: str,
    ) -> typing.List[typing.Tuple[str, str]]:

        with self._db as db:
            if path.endswith('/'):
                query = f'''
                    SELECT path, version
                    FROM data
                    WHERE path
                    LIKE ? || "%"
                '''
                ls = db.execute(query, [path]).fetchall()
            else:
                query = f'''
                    SELECT path, version
                    FROM data
                    WHERE path="{path}"
                '''
                ls = db.execute(query).fetchall()

        if not ls and not path == '/':
            raise FileNotFoundError(
                errno.ENOENT,
                os.strerror(errno.ENOENT),
                path,
            )
        return ls


Some examples how to use the method.

.. jupyter-execute::

    display(
        backend.ls('/'),
        backend.ls('/a/'),
        backend.ls('/file.txt'),
        backend.ls('/file.txt', latest_version=True),
    )


It is also possible
to directly request the version(s)
of a path.

.. jupyter-execute::

    display(
        backend.versions('/file.txt'),
        backend.latest_version('/file.txt'),
    )


We also want to delete files
from our backend,
so we implement an according method.

.. jupyter-execute::

    @add_method(SQLite)
    def _remove_file(
            self,
            path: str,
            version: str,
    ):
        with self._db as db:
            query = f'''
                DELETE
                FROM data
                WHERE path="{path}" AND version="{version}"
            '''
            db.execute(query)

    backend.remove_file('/file.txt', '2.0.0')
    backend.remove_file('/a/file.zip', '2.0.0')
    backend.ls('/')


Finally,
we add one more method that
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


To verify we really have
delete the repository,
we try to access it.
This will raise a
:class:`audbackend.BackendError`,
which wraps the original
exception by the backend.

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
