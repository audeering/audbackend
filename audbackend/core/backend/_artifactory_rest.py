"""Thin REST client for the JFrog Artifactory HTTP API.

Internal module used by :mod:`audbackend.core.backend.artifactory`.
Not a public API.

The client wraps the Artifactory REST endpoints the backend needs:

* ``GET /api/storage/{repo}/{path}`` — file metadata (size, md5, mtime, owner)
* ``GET /{repo}/{path}`` (streamed) — download
* ``PUT /{repo}/{path}`` with ``X-Checksum-Md5`` header — upload
* ``DELETE /{repo}/{path}`` — remove file
* ``POST /api/copy|move/...`` — server-side copy/move
* ``GET /api/storage/{repo}/{sub}?list&deep=1&listFolders=0`` — recursive list
* ``PUT|GET|DELETE /api/repositories/{repo}`` — repository admin
"""

from __future__ import annotations

from collections.abc import Iterator
import datetime
import urllib.parse

import requests


DOWNLOAD_CHUNK_SIZE = 4 * 1024
STREAM_CHUNK_SIZE = 64 * 1024


def _quote(path: str) -> str:
    """URL-quote a path, preserving forward slashes."""
    return urllib.parse.quote(path, safe="/")


def _parse_iso(value: str) -> datetime.datetime:
    """Parse an ISO 8601 timestamp, accepting a trailing ``Z``."""
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.datetime.fromisoformat(value)


class ArtifactoryRestClient:
    """REST client bound to one repository on an Artifactory host.

    The caller owns the :class:`requests.Session` (auth, connection
    pooling, close). The client only issues requests.
    """

    def __init__(
        self,
        host: str,
        repository: str,
        session: requests.Session,
    ):
        self.host = host.rstrip("/")
        self.repository = repository
        self.session = session

    # ------------------------------------------------------------------
    # URL builders
    # ------------------------------------------------------------------

    def _file_url(self, path: str) -> str:
        return f"{self.host}/{self.repository}/{_quote(path.lstrip('/'))}"

    def _storage_url(self, path: str = "") -> str:
        stripped = path.lstrip("/")
        if stripped:
            return f"{self.host}/api/storage/{self.repository}/{_quote(stripped)}"
        return f"{self.host}/api/storage/{self.repository}"

    def _repo_url(self) -> str:
        return f"{self.host}/api/repositories/{_quote(self.repository)}"

    # ------------------------------------------------------------------
    # File metadata
    # ------------------------------------------------------------------

    def stat(self, path: str) -> dict:
        """Return ``{size, md5, mtime, modified_by}`` for a file.

        Raises :class:`FileNotFoundError` if the path does not exist.
        """
        response = self.session.get(self._storage_url(path))
        if response.status_code == 404:
            raise FileNotFoundError(path)
        response.raise_for_status()
        data = response.json()
        checksums = data.get("checksums") or {}
        return {
            "size": int(data.get("size", 0)),
            "md5": checksums.get("md5", ""),
            "mtime": _parse_iso(data["lastModified"]),
            "modified_by": data.get("modifiedBy", ""),
        }

    def exists(self, path: str) -> bool:
        response = self.session.get(self._storage_url(path))
        if response.status_code == 404:
            return False
        response.raise_for_status()
        return True

    # ------------------------------------------------------------------
    # File transfer
    # ------------------------------------------------------------------

    def download(
        self,
        path: str,
        dst_path: str,
        *,
        chunk_size: int = DOWNLOAD_CHUNK_SIZE,
        on_chunk=None,
    ) -> None:
        """Stream an artifact to ``dst_path``.

        ``on_chunk`` is called with the number of bytes written after
        each chunk (for progress bars).
        """
        with self.session.get(self._file_url(path), stream=True) as response:
            response.raise_for_status()
            with open(dst_path, "wb") as fp:
                for data in response.iter_content(chunk_size=chunk_size):
                    fp.write(data)
                    if on_chunk is not None:
                        on_chunk(len(data))

    def stream(
        self,
        path: str,
        *,
        chunk_size: int = STREAM_CHUNK_SIZE,
    ) -> Iterator[bytes]:
        """Yield byte chunks for streaming reads."""
        with self.session.get(self._file_url(path), stream=True) as response:
            response.raise_for_status()
            yield from response.iter_content(chunk_size=chunk_size)

    def upload(
        self,
        src_path: str,
        dst_path: str,
        *,
        md5: str | None = None,
    ) -> None:
        """PUT a local file. When ``md5`` is given, the server validates it."""
        headers = {}
        if md5 is not None:
            headers["X-Checksum-Md5"] = md5
        with open(src_path, "rb") as fp:
            response = self.session.put(
                self._file_url(dst_path),
                data=fp,
                headers=headers,
            )
        response.raise_for_status()

    # ------------------------------------------------------------------
    # File management
    # ------------------------------------------------------------------

    def delete(self, path: str) -> None:
        response = self.session.delete(self._file_url(path))
        if response.status_code == 404:
            raise FileNotFoundError(path)
        response.raise_for_status()

    def copy(self, src_path: str, dst_path: str) -> None:
        self._copy_or_move("copy", src_path, dst_path)

    def move(self, src_path: str, dst_path: str) -> None:
        self._copy_or_move("move", src_path, dst_path)

    def _copy_or_move(self, action: str, src_path: str, dst_path: str) -> None:
        src = f"{self.repository}/{src_path.lstrip('/')}"
        dst = f"/{self.repository}/{dst_path.lstrip('/')}"
        url = f"{self.host}/api/{action}/{_quote(src)}"
        response = self.session.post(url, params={"to": dst})
        response.raise_for_status()

    def list_files(self, sub_path: str) -> list[str]:
        """Recursively list files under ``sub_path``.

        Returns virtual paths (``/dir/file.ext``) relative to the
        repository root. Empty list if ``sub_path`` does not exist.
        """
        stripped = sub_path.strip("/")
        prefix = f"/{stripped}" if stripped else ""
        response = self.session.get(
            self._storage_url(prefix),
            params={"list": "", "deep": 1, "listFolders": 0},
        )
        if response.status_code == 404:
            return []
        response.raise_for_status()
        data = response.json()
        # Each 'uri' is relative to the queried sub_path and starts with '/'.
        return [f"{prefix}{entry['uri']}" for entry in data.get("files", [])]

    # ------------------------------------------------------------------
    # Repository admin
    # ------------------------------------------------------------------

    def repository_exists(self) -> bool:
        # ``/api/repositories/{repo}`` returns 400 on some Artifactory
        # versions when the repo does not exist; ``/api/storage/{repo}``
        # reliably returns 404.
        response = self.session.get(self._storage_url())
        if response.status_code == 404:
            return False
        response.raise_for_status()
        return True

    def create_repository(self, *, package_type: str = "generic") -> None:
        body = {
            "key": self.repository,
            "rclass": "local",
            "packageType": package_type,
        }
        response = self.session.put(self._repo_url(), json=body)
        response.raise_for_status()

    def delete_repository(self) -> None:
        response = self.session.delete(self._repo_url())
        response.raise_for_status()
