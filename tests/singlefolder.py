import datetime
import os
import pickle
import shutil
import threading

import audeer

import audbackend


class SingleFolder(audbackend.backend.Base):
    r"""Backend implemented in a single folder.

    Files put on the backend
    are stored under a random file name.
    A serialized dictionary
    stores the dependency between
    backend path and the names.
    It also stores checksum for every file.

    """

    class Map:
        r"""Provides exclusive access to the map file."""

        def __init__(
            self,
            path: str,
            lock: threading.Lock,
        ):
            self.path = path
            self.obj = {}
            self.lock = lock

        def __enter__(self):
            self.lock.acquire()
            if os.path.exists(self.path):
                with open(self.path, "rb") as fp:
                    self.obj = pickle.load(fp)
            return self.obj

        def __exit__(
            self,
            type,
            value,
            traceback,
        ):
            with open(self.path, "wb") as fp:
                pickle.dump(self.obj, fp)
            self.lock.release()

    def __init__(
        self,
        host: str,
        repository: str,
    ):
        super().__init__(host, repository)

        self._root = audeer.mkdir(audeer.path(host, repository))
        self._path = audeer.path(self._root, ".map")
        self._lock = threading.Lock()

    def _open(
        self,
    ):
        if not os.path.exists(self._path):
            raise audbackend.core.utils.raise_file_not_found_error(self._path)

        with self.Map(self._path, self._lock):
            pass

    def _checksum(
        self,
        path: str,
    ) -> str:
        with self.Map(self._path, self._lock) as m:
            return m[path][1]

    def _create(
        self,
    ):
        if os.path.exists(self._path):
            raise audbackend.core.utils.raise_file_exists_error(self._path)
        with self.Map(self._path, self._lock):
            pass

    def _date(
        self,
        path: str,
    ) -> str:
        with self.Map(self._path, self._lock) as m:
            p = m[path][0]
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
    ) -> bool:
        with self.Map(self._path, self._lock) as m:
            return path in m

    def _get_file(
        self,
        src_path: str,
        dst_path: str,
        verbose: bool,
    ):
        with self.Map(self._path, self._lock) as m:
            shutil.copy(m[src_path][0], dst_path)

    def _ls(
        self,
        path: str,
    ) -> list[str]:
        with self.Map(self._path, self._lock) as m:
            ls = []

            for p in m:
                if p.startswith(path):
                    ls.append(p)

            return ls

    def _owner(
        self,
        path: str,
    ):
        with self.Map(self._path, self._lock) as m:
            p = m[path][0]
            return audbackend.core.utils.file_owner(p)

    def _put_file(
        self,
        src_path: str,
        dst_path: str,
        checksum: str,
        verbose: bool,
    ):
        with self.Map(self._path, self._lock) as m:
            if dst_path not in m or checksum != m[dst_path][1]:
                m[dst_path] = {}
                p = audeer.path(self._root, audeer.uid()[:8])
                m[dst_path] = (p, checksum)

            shutil.copy(src_path, m[dst_path][0])

    def _remove_file(
        self,
        path: str,
    ):
        with self.Map(self._path, self._lock) as m:
            os.remove(m[path][0])
            m.pop(path)
