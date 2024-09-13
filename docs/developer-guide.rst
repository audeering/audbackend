.. _developer-guide:

Developer guide
===============

The aim of
:mod:`audbackend`
is to provide an
abstract backend for
any kind of file storage system,
that follow the :mod:`fsspec` specifications.

This tutorial shows
how to develop a new backend.


.. _develop-new-backend:

Develop new backend
-------------------

We can implement our own backend
by deriving from
:class:`audbackend.AbstractBackend`.
Afterwards,
you need to provide implementations
for the following methods:

* ``checksum()``
* ``copy_file()``
* ``date()``
* ``exists()``
* ``get_file()``
* ``ls()``
* ``move_file()``
* ``path()``
* ``put_file()``
* ``remove_file()``


For instance,
we can create an backend
to manage user content.
It provides one additional method:

* ``add_user()`` to register a user

We store user information
in a database under
``"/.user.map"`` on the backend.
To access and update
the database
we implement the following
helper class.


.. code-block:: python

    import os
    import shelve

    import audbackend
    import fsspec


    class UserDB:
        r"""User database.

        Temporarily get user database
        and write changes back to the backend.

        """
        def __init__(self, fs: fsspec.AbstractFileSystem):
            self.backend = audbackend.Unversioned(fs)
            self.remote_file = "/.user.db"
            self.local_file = ".db"

        def __enter__(self) -> shelve.Shelf:
            if self.backend.exists(self.remote_file):
                self.backend.get_file(self.remote_file, self.local_file)
                self._map = shelve.open(self.local_file, flag="w", writeback=True)
            else:
                self._map = shelve.open(self.local_file, writeback=True)
            return self._map

        def __exit__(self, exc_type, exc_val, exc_tb):
            self._map.close()
            self.backend.put_file(self.local_file, self.remote_file)
            os.remove(self.local_file)


Now,
we implement the backend.

.. code-block:: python

    class UserContent(audbackend.AbstractBackend):

        def add_user(self, user: str, password: str):
            r"""Add user to database."""
            with UserDB(self.fs) as map:
                map[user] = password

        def checksum(self, path: str, *, user: str, password: str):
            path = self.path(path, user=user, password=password)
            return self._checksum(path)

        def copy_file(
            self,
            src_path: str,
            dst_path: str,
            *,
            user: str,
            password: str,
            validate: bool = False,
            verbose: bool = False,
        ):
            src_path = self.path(src_path, user=user, password=password)
            dst_path = self.path(dst_path, user=user, password=password)
            self._copy_file(src_path, dst_path, validate, verbose)

        def date(self, path: str, *, user: str, password: str):
            path = self.path(path, user=user, password=password)
            return self._date(path)

        def exists(self, path: str, *, user: str, password: str):
            path = self.path(path, user=user, password=password)
            return self._exists(path)

        def get_file(
            self,
            src_path: str,
            dst_path: str,
            *,
            user: str,
            password: str,
            validate: bool = False,
            verbose: bool = False,
        ):
            src_path = self.path(src_path, user=user, password=password)
            return self._get_file(src_path, dst_path, validate, verbose)

        def ls(
            self,
            path: str = "/",
            *,
            user: str,
            password: str,
            pattern: str = None,
            suppress_backend_errors: bool = False,
        ):
            path = self.path(path, allow_sub_path=True, user=user, password=password)
            return self._ls(path, suppress_backend_errors, pattern)
            # paths = [path.replace(self.sep + user, "") for path in paths]
            # return paths

        def move_file(
            self,
            src_path: str,
            dst_path: str,
            *,
            user: str,
            password: str,
            validate: bool = False,
            verbose: bool = False,
        ):
            src_path = self.path(src_path, user=user, password=password)
            dst_path = self.path(dst_path, user=user, password=password)
            self._move_file(src_path, dst_path, validate, verbose)

        def path(
            self,
            path: str,
            *,
            user: str,
            password: str,
            allow_sub_path: bool = False,
        ):
            with UserDB(self.fs) as db:
                if user not in db or db[user] != password:
                    raise ValueError("User does not exist or wrong password.")
            path = self._path(path, allow_sub_path)
            return self.join(self.sep, user, path)

        def put_file(
            self,
            src_path: str,
            dst_path: str,
            *,
            user: str,
            password: str,
            validate: bool = False,
            verbose: bool = False,
        ):
            dst_path = self.path(dst_path, user=user, password=password)
            return self._put_file(src_path, dst_path, validate, verbose)

        def remove_file(path: str, *, user: str, password: str):
            path = self.path(path, user=user, password=password)
            self._remove_file(path)


Let's create a dir file system
with a repository folder
with our custom backend,
and upload a file:

>>> import audeer
>>> repo = audeer.mkdir("./repo")
>>> filesystem = fsspec.filesystem("dir", path=repo)
>>> backend = UserContent(filesystem)
>>> backend.add_user("test", "pa$$word")
>>> _ = audeer.touch("local.txt")
>>> backend.put_file("local.txt", "/file.txt", user="test", password="pa$$word")
>>> backend.ls("/", user="test", password="pa$$word")
['/test/file.txt']

At the end we clean up and delete our repo.

>>> audeer.rmdir(repo)
