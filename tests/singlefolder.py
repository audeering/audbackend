import datetime
import os
import shelve
import shutil
import threading
import typing

import audeer

import audbackend


class SingleFolder(audbackend.Backend):
    r"""Backend implemented in a single folder.

    Files put on the backend
    are stored under a random file name.
    A serialized dictionary
    stores the dependency between
    backend path and the names.
    It also stores the version
    and checksum for every file.

    """
    class Map:
        r"""Provides exclusive access to the map file."""

        def __init__(
                self,
                path: str,
                lock: threading.Lock,
                *,
                flag: str = 'w',
        ):
            self.obj = shelve.open(
                path,
                flag=flag,
                writeback=True,
            )
            self.lock = lock

        def __enter__(self):
            self.lock.acquire()
            return self.obj

        def __exit__(
                self,
                type,
                value,
                traceback,
        ):
            self.obj.close()
            self.lock.release()

    def __init__(
            self,
            host: str,
            repository: str,
    ):
        super().__init__(host, repository)

        self._root = audeer.mkdir(audeer.path(host, repository))
        self._path = audeer.path(self._root, '.map')
        self._lock = threading.Lock()

    def _access(
            self,
    ):
        if not os.path.exists(self._path):
            raise audbackend.core.utils.raise_file_not_found_error(self._path)

        with self.Map(self._path, self._lock):
            pass

    def _checksum(
            self,
            path: str,
            version: str,
    ) -> str:
        with self.Map(self._path, self._lock) as m:
            return m[path][version][1]

    def _create(
            self,
    ):
        if os.path.exists(self._path):
            raise audbackend.core.utils.raise_file_exists_error(self._path)
        with self.Map(self._path, self._lock, flag='n'):
            pass

    def _date(
            self,
            path: str,
            version: str,
    ) -> str:
        with self.Map(self._path, self._lock) as m:
            p = m[path][version][0]
            date = os.path.getmtime(p)
            date = datetime.datetime.fromtimestamp(date)
            date = audbackend.core.utils.date_format(date)
            return date

    def _delete(
            self,
    ):
        if not os.path.exists(self._path):
            raise audbackend.core.utils.raise_file_not_found_error(self._path)
        with self._lock:
            audeer.rmdir(self._root)

    def _exists(
            self,
            path: str,
            version: str,
    ) -> bool:
        with self.Map(self._path, self._lock) as m:
            return path in m and version in m[path]

    def _get_file(
            self,
            src_path: str,
            dst_path: str,
            version: str,
            verbose: bool,
    ):
        with self.Map(self._path, self._lock) as m:
            shutil.copy(m[src_path][version][0], dst_path)

    def _ls(
            self,
            path: str,
    ) -> typing.List[typing.Tuple[str, str]]:

        with self.Map(self._path, self._lock) as m:

            ls = []

            if path.endswith('/'):
                for p in m:
                    if p.startswith(path):
                        for v in m[p]:
                            ls.append((p, v))
            else:
                for p in m:
                    if p == path:
                        for v in m[p]:
                            ls.append((p, v))

            if not ls and not path == '/':
                raise audbackend.core.utils.raise_file_not_found_error(path)

            return ls

    def _owner(
            self,
            path: str,
            version: str,
    ):
        with self.Map(self._path, self._lock) as m:
            p = m[path][version][0]
            return audbackend.core.utils.file_owner(p)

    def _put_file(
            self,
            src_path: str,
            dst_path: str,
            version: str,
            checksum: str,
            verbose: bool,
    ):
        with self.Map(self._path, self._lock) as m:

            if dst_path not in m:
                m[dst_path] = {}

            if version not in m[dst_path]:
                p = audeer.path(self._root, audeer.uid()[:8])
                m[dst_path][version] = (p, checksum)

            shutil.copy(src_path, m[dst_path][version][0])

    def _remove_file(
            self,
            path: str,
            version: str,
    ):
        with self.Map(self._path, self._lock) as m:

            os.remove(m[path][version][0])
            m[path].pop(version)
            if not m[path]:
                m.pop(path)
