"""HTTP/2 download utilities for bulk operations.

This module provides HTTP/2 support for downloading multiple files
efficiently using connection multiplexing.

Requires the ``http2`` optional dependency:

.. code-block:: bash

    pip install audbackend[http2]

"""

from __future__ import annotations

from collections.abc import Callable
from collections.abc import Sequence
import os
from typing import Any


def _check_httpx_available():
    """Check if httpx is installed."""
    try:
        import httpx  # noqa: F401

        return True
    except ImportError:
        return False


HTTP2_AVAILABLE = _check_httpx_available()


class Http2Downloader:
    """HTTP/2 client for efficient bulk downloads.

    This class provides HTTP/2 multiplexing for downloading multiple files
    in parallel over fewer TCP connections, reducing connection overhead
    for bulk operations.

    Args:
        base_url: Base URL for the server
        auth: Authentication tuple (username, password) or None
        http2: Enable HTTP/2 (default: True)
        limits: Connection pool limits. If None, uses defaults
            optimized for bulk downloads (100 max connections)
        timeout: Request timeout in seconds (default: 30.0)
        verify: SSL verification (default: True)

    Raises:
        ImportError: If httpx is not installed

    Example:
        >>> downloader = Http2Downloader(
        ...     "https://s3.example.com",
        ...     auth=("access_key", "secret_key"),
        ... )
        >>> with downloader:
        ...     downloader.download_file("/bucket/file.txt", "/tmp/file.txt")

    """

    def __init__(
        self,
        base_url: str,
        *,
        auth: tuple[str, str] | None = None,
        http2: bool = True,
        limits: dict[str, int] | None = None,
        timeout: float = 30.0,
        verify: bool = True,
    ):
        if not HTTP2_AVAILABLE:
            raise ImportError(
                "httpx is required for HTTP/2 support. "
                "Install with: pip install audbackend[http2]"
            )

        import httpx

        # Default limits optimized for bulk downloads
        if limits is None:
            limits = {
                "max_keepalive_connections": 100,
                "max_connections": 100,
            }

        self._base_url = base_url.rstrip("/")
        self._auth = auth
        self._http2 = http2
        self._timeout = timeout
        self._verify = verify
        self._limits = httpx.Limits(**limits)
        self._client: httpx.Client | None = None

    def __enter__(self) -> "Http2Downloader":
        """Open the HTTP/2 client."""
        self.open()
        return self

    def __exit__(self, *args: Any) -> None:
        """Close the HTTP/2 client."""
        self.close()

    def open(self) -> None:
        """Open the HTTP/2 client connection pool."""
        import httpx

        self._client = httpx.Client(
            base_url=self._base_url,
            auth=self._auth,
            http2=self._http2,
            limits=self._limits,
            timeout=self._timeout,
            verify=self._verify,
        )

    def close(self) -> None:
        """Close the HTTP/2 client connection pool."""
        if self._client is not None:
            self._client.close()
            self._client = None

    @property
    def http_version(self) -> str:
        """Return the HTTP version being used."""
        return "HTTP/2" if self._http2 else "HTTP/1.1"

    def download_file(
        self,
        url: str,
        dst_path: str,
        *,
        chunk_size: int = 64 * 1024,
        progress_callback: Callable[[int], None] | None = None,
    ) -> None:
        """Download a single file.

        Args:
            url: URL path to download (relative to base_url)
            dst_path: Local destination path
            chunk_size: Download chunk size in bytes (default: 64KB)
            progress_callback: Optional callback called with bytes downloaded

        Raises:
            RuntimeError: If client is not open

        """
        if self._client is None:
            raise RuntimeError("Client not open. Use 'with' statement or call open().")

        # Ensure parent directory exists
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)

        with self._client.stream("GET", url) as response:
            response.raise_for_status()
            with open(dst_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=chunk_size):
                    f.write(chunk)
                    if progress_callback:
                        progress_callback(len(chunk))

    def download_files(
        self,
        files: Sequence[tuple[str, str]],
        *,
        num_workers: int = 10,
        chunk_size: int = 64 * 1024,
        progress_callback: Callable[[str, int], None] | None = None,
        verbose: bool = False,
    ) -> list[str]:
        """Download multiple files in parallel.

        Uses HTTP/2 multiplexing for efficient parallel downloads.

        Args:
            files: List of (url, dst_path) tuples
            num_workers: Number of parallel download workers (default: 10)
            chunk_size: Download chunk size in bytes (default: 64KB)
            progress_callback: Optional callback(url, bytes_downloaded)
            verbose: Show progress bar

        Returns:
            List of successfully downloaded file paths

        Raises:
            RuntimeError: If client is not open

        """
        if self._client is None:
            raise RuntimeError("Client not open. Use 'with' statement or call open().")

        import audeer

        downloaded = []

        def download_one(url: str, dst_path: str) -> str:
            """Download a single file."""
            callback = None
            if progress_callback:

                def callback(n: int) -> None:
                    progress_callback(url, n)

            self.download_file(
                url, dst_path, chunk_size=chunk_size, progress_callback=callback
            )
            return dst_path

        # Use audeer.run_tasks for parallel execution
        params = [([url, dst_path], {}) for url, dst_path in files]
        results = audeer.run_tasks(
            download_one,
            params,
            num_workers=num_workers,
            progress_bar=verbose,
            task_description="Download files (HTTP/2)",
        )
        downloaded = [r for r in results if r is not None]

        return downloaded


def is_http2_available() -> bool:
    """Check if HTTP/2 support is available.

    Returns:
        True if httpx is installed and HTTP/2 is available

    """
    return HTTP2_AVAILABLE
