"""Tests for HTTP/2 download utilities."""

import os

import pytest

import audeer

import audbackend


def test_http2_available():
    """Test that HTTP/2 availability check works."""
    assert audbackend.is_http2_available() is True
    assert audbackend.HTTP2_AVAILABLE is True


def test_http2_downloader_creation():
    """Test Http2Downloader can be created."""
    downloader = audbackend.Http2Downloader("https://example.com")
    assert downloader.http_version == "HTTP/2"
    assert downloader._client is None  # Not opened yet


def test_http2_downloader_http1_fallback():
    """Test Http2Downloader can disable HTTP/2."""
    downloader = audbackend.Http2Downloader("https://example.com", http2=False)
    assert downloader.http_version == "HTTP/1.1"


def test_http2_downloader_context_manager():
    """Test Http2Downloader context manager."""
    downloader = audbackend.Http2Downloader("https://example.com")

    # Before context manager, client is None
    assert downloader._client is None

    with downloader:
        # Inside context manager, client is open
        assert downloader._client is not None

    # After context manager, client is closed
    assert downloader._client is None


def test_http2_downloader_open_close():
    """Test Http2Downloader open and close methods."""
    downloader = audbackend.Http2Downloader("https://example.com")

    # Initially closed
    assert downloader._client is None

    # Open
    downloader.open()
    assert downloader._client is not None

    # Close
    downloader.close()
    assert downloader._client is None


def test_http2_downloader_custom_limits():
    """Test Http2Downloader with custom connection limits."""
    limits = {
        "max_keepalive_connections": 50,
        "max_connections": 200,
    }
    downloader = audbackend.Http2Downloader("https://example.com", limits=limits)

    # Check the limits were set correctly on the downloader
    assert downloader._limits.max_keepalive_connections == 50
    assert downloader._limits.max_connections == 200


def test_http2_downloader_download_not_open():
    """Test that downloading without opening raises error."""
    downloader = audbackend.Http2Downloader("https://example.com")

    with pytest.raises(RuntimeError, match="Client not open"):
        downloader.download_file("/test.txt", "/tmp/test.txt")


def test_http2_downloader_download_files_not_open():
    """Test that bulk download without opening raises error."""
    downloader = audbackend.Http2Downloader("https://example.com")

    with pytest.raises(RuntimeError, match="Client not open"):
        downloader.download_files([("/test.txt", "/tmp/test.txt")])


def test_http2_downloader_download_file(tmpdir):
    """Test download_file method with a real HTTPS endpoint."""
    # Use httpbin.org which is a test HTTP service
    downloader = audbackend.Http2Downloader("https://httpbin.org")
    dst_path = audeer.path(tmpdir, "response.json")

    with downloader:
        # Download a small JSON response
        downloader.download_file("/json", dst_path)

    # Verify file was downloaded
    assert os.path.exists(dst_path)
    with open(dst_path) as f:
        content = f.read()
    assert "slideshow" in content  # httpbin /json returns a slideshow object


def test_http2_downloader_with_progress_callback(tmpdir):
    """Test download_file with progress callback."""
    bytes_downloaded = []

    def progress_callback(n):
        bytes_downloaded.append(n)

    downloader = audbackend.Http2Downloader("https://httpbin.org")
    dst_path = audeer.path(tmpdir, "response.json")

    with downloader:
        downloader.download_file("/json", dst_path, progress_callback=progress_callback)

    # Verify callback was called
    assert len(bytes_downloaded) > 0
    assert sum(bytes_downloaded) > 0


def test_http2_downloader_download_files(tmpdir):
    """Test downloading multiple files in parallel."""
    downloader = audbackend.Http2Downloader("https://httpbin.org")

    # Download multiple endpoints
    files = [
        ("/json", audeer.path(tmpdir, "json.txt")),
        ("/uuid", audeer.path(tmpdir, "uuid.txt")),
    ]

    with downloader:
        downloaded = downloader.download_files(files, num_workers=2)

    # Verify both files were downloaded
    assert len(downloaded) == 2
    for _, dst_path in files:
        assert os.path.exists(dst_path)


def test_http2_downloader_download_files_with_progress(tmpdir):
    """Test downloading multiple files with progress callback."""
    progress_calls = []

    def progress_callback(url, n):
        progress_calls.append((url, n))

    downloader = audbackend.Http2Downloader("https://httpbin.org")

    files = [
        ("/json", audeer.path(tmpdir, "json.txt")),
    ]

    with downloader:
        downloader.download_files(
            files,
            num_workers=1,
            progress_callback=progress_callback,
        )

    # Verify progress callback was called
    assert len(progress_calls) > 0
