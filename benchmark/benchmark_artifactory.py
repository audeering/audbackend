#!/usr/bin/env python3
"""Benchmark the public Artifactory backend API.

The script uses only ``audbackend.backend.Artifactory`` and its public
methods, so the same script can be run against any branch — e.g. the
current dohq-artifactory implementation on ``main`` and a future
``requests``-based rewrite — and the numbers are directly comparable.

Usage
-----

Credentials are read by ``Artifactory.get_authentication()``: env vars
``ARTIFACTORY_USERNAME`` / ``ARTIFACTORY_API_KEY`` if set, otherwise
``~/.artifactory_python.cfg`` (or ``ARTIFACTORY_CONFIG_FILE``).

    uv run python benchmark/benchmark_artifactory.py \
        --label main-dohq \
        --runs 5 \
        --output benchmark/results/main-dohq.md

For a quick dry-run:

    uv run python benchmark/benchmark_artifactory.py --quick --runs 2
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
import csv
from dataclasses import dataclass
from dataclasses import field
import os
import statistics
import sys
import tempfile
import time

import audeer

import audbackend


DEFAULT_HOST = os.environ.get(
    "BENCHMARK_ARTIFACTORY_HOST",
    "https://audeering.jfrog.io/artifactory",
)

SIZE_MAP = {
    "1KB": 1024,
    "1MB": 1024 * 1024,
    "10MB": 10 * 1024 * 1024,
    "50MB": 50 * 1024 * 1024,
}


@dataclass
class Result:
    """One benchmark result — a series of timed runs for one case."""

    operation: str
    size: str
    num_workers: int
    extra: str
    runs: int
    timings: list[float] = field(default_factory=list)

    def row(self, label: str) -> dict:
        """Return a flat dict of summary statistics for this result."""
        t = self.timings
        return {
            "label": label,
            "operation": self.operation,
            "size": self.size,
            "num_workers": self.num_workers,
            "extra": self.extra,
            "runs": self.runs,
            "median_s": round(statistics.median(t), 4) if t else "",
            "stdev_s": round(statistics.stdev(t), 4) if len(t) > 1 else 0.0,
            "min_s": round(min(t), 4) if t else "",
            "max_s": round(max(t), 4) if t else "",
        }


def make_random_file(path: str, size: int) -> None:
    """Write a file of exactly ``size`` random bytes."""
    chunk = 1024 * 1024
    with open(path, "wb") as f:
        remaining = size
        while remaining > 0:
            n = min(chunk, remaining)
            f.write(os.urandom(n))
            remaining -= n


def time_op(fn: Callable[[], None]) -> float:
    t0 = time.perf_counter()
    fn()
    return time.perf_counter() - t0


def bench_put_file(backend, local_file, size_label, runs, results):
    """Unique dst per iteration so checksum-skip does not kick in."""
    timings = []
    for i in range(runs):
        dst = f"/put/{size_label}/run_{i}.bin"
        timings.append(time_op(lambda d=dst: backend.put_file(local_file, d)))
    results.append(Result("put_file", size_label, 1, "", runs, timings))


def bench_get_file(
    backend, remote_file, size_label, num_workers, runs, results, tmpdir
):
    """Delete local dst between iterations so checksum-skip does not kick in."""
    timings = []
    dst = audeer.path(tmpdir, f"get_{size_label}_{num_workers}.bin")
    for _ in range(runs):
        if os.path.exists(dst):
            os.remove(dst)
        timings.append(
            time_op(
                lambda d=dst, nw=num_workers: backend.get_file(
                    remote_file, d, num_workers=nw
                )
            )
        )
    results.append(Result("get_file", size_label, num_workers, "", runs, timings))


def bench_metadata(backend, remote_file, size_label, runs, results):
    """Metadata-only operations on an existing file."""
    for op in ("exists", "checksum", "date", "owner"):
        fn = getattr(backend, op)
        timings = [time_op(lambda f=fn: f(remote_file)) for _ in range(runs)]
        results.append(Result(op, size_label, 1, "", runs, timings))


def bench_ls(backend, sub_path, num_files, runs, results):
    timings = [time_op(lambda: backend.ls(sub_path)) for _ in range(runs)]
    results.append(Result("ls", "-", 1, f"{num_files}_files", runs, timings))


def bench_copy_file(backend, src, runs, results):
    timings = []
    for i in range(runs):
        dst = f"/copy/run_{i}.bin"
        timings.append(time_op(lambda d=dst: backend.copy_file(src, d)))
    results.append(Result("copy_file", "1MB", 1, "", runs, timings))


def bench_move_file(backend, local_file, runs, results):
    """Re-upload a fresh source each iteration, since move consumes it."""
    timings = []
    for i in range(runs):
        src = f"/move/src_{i}.bin"
        dst = f"/move/dst_{i}.bin"
        backend.put_file(local_file, src)
        timings.append(time_op(lambda s=src, d=dst: backend.move_file(s, d)))
    results.append(Result("move_file", "1MB", 1, "", runs, timings))


def bench_remove_file(backend, local_file, runs, results):
    """Re-upload before each remove iteration."""
    timings = []
    for i in range(runs):
        path = f"/remove/run_{i}.bin"
        backend.put_file(local_file, path)
        timings.append(time_op(lambda p=path: backend.remove_file(p)))
    results.append(Result("remove_file", "1MB", 1, "", runs, timings))


def bench_put_archive(backend, src_root, runs, results):
    timings = []
    for i in range(runs):
        dst = f"/archive/put_{i}.zip"
        timings.append(time_op(lambda d=dst: backend.put_archive(src_root, d)))
    results.append(Result("put_archive", "1MB", 1, "zip", runs, timings))


def bench_get_archive(backend, remote_archive, tmpdir, runs, results):
    timings = []
    for i in range(runs):
        dst_root = audeer.path(tmpdir, f"get_archive_{i}")
        audeer.mkdir(dst_root)
        timings.append(
            time_op(lambda d=dst_root: backend.get_archive(remote_archive, d))
        )
    results.append(Result("get_archive", "1MB", 1, "zip", runs, timings))


def setup_ls_fixture(backend, num_files, local_file):
    """Populate a directory with ``num_files`` small files for ls benchmarking."""
    sub_path = f"/ls/n_{num_files}/"
    for i in range(num_files):
        backend.put_file(local_file, f"{sub_path.rstrip('/')}/file_{i}.bin")
    return sub_path


def write_results(results, label, md_path, csv_path):
    rows = [r.row(label) for r in results]
    audeer.mkdir(os.path.dirname(md_path) or ".")

    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    header = (
        "| label | operation | size | num_workers | extra | runs | "
        "median(s) | stdev(s) | min(s) | max(s) |\n"
        "|---|---|---|---:|---|---:|---:|---:|---:|---:|\n"
    )
    with open(md_path, "w") as f:
        f.write(f"# Artifactory benchmark results: {label}\n\n")
        f.write(header)
        for r in rows:
            f.write(
                f"| {r['label']} | {r['operation']} | {r['size']} "
                f"| {r['num_workers']} | {r['extra']} | {r['runs']} "
                f"| {r['median_s']} | {r['stdev_s']} "
                f"| {r['min_s']} | {r['max_s']} |\n"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument(
        "--repository",
        default=None,
        help="Repository name; autogenerated if omitted.",
    )
    parser.add_argument("--label", default="run", help="Free-text label (e.g. branch).")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument(
        "--sizes",
        default="1KB,1MB,50MB",
        help="Comma-separated file sizes for put/get benchmarks.",
    )
    parser.add_argument(
        "--ls-sizes",
        default="10,100",
        help="Comma-separated directory sizes for ls benchmark.",
    )
    parser.add_argument(
        "--workers",
        default="1,6",
        help="Comma-separated num_workers values for get_file.",
    )
    parser.add_argument(
        "--skip",
        default="",
        help=(
            "Comma-separated list of operations to skip: "
            "put_file,get_file,metadata,ls,copy_file,move_file,remove_file,"
            "put_archive,get_archive"
        ),
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Shortcut: only 1KB+1MB, workers=1, ls 10, 2 runs.",
    )
    parser.add_argument("--output", default=None, help="Output .md path.")
    parser.add_argument("--keep-repo", action="store_true")
    args = parser.parse_args()

    if args.quick:
        args.sizes = "1KB,1MB"
        args.workers = "1"
        args.ls_sizes = "10"
        if args.runs > 2:
            args.runs = 2

    sizes = [s.strip() for s in args.sizes.split(",") if s.strip()]
    for s in sizes:
        if s not in SIZE_MAP:
            print(f"Unknown size {s!r}. Known: {list(SIZE_MAP)}", file=sys.stderr)
            return 2
    workers = [int(w) for w in args.workers.split(",") if w.strip()]
    ls_sizes = [int(n) for n in args.ls_sizes.split(",") if n.strip()]
    skip = {s.strip() for s in args.skip.split(",") if s.strip()}

    repository = args.repository or f"benchmark-{audeer.uid()[:8]}"
    created_repo = False
    if args.repository is None:
        audbackend.backend.Artifactory.create(args.host, repository)
        created_repo = True
        print(f"Created repository {repository!r} on {args.host}")
    else:
        print(f"Using existing repository {repository!r} on {args.host}")

    results: list[Result] = []
    t_start = time.perf_counter()

    try:
        with audbackend.backend.Artifactory(args.host, repository) as backend:
            with tempfile.TemporaryDirectory() as tmpdir:
                local_files = {}
                for s in sizes:
                    p = audeer.path(tmpdir, f"src_{s}.bin")
                    make_random_file(p, SIZE_MAP[s])
                    local_files[s] = p

                # Warm-up: establish connection pool & auth round-trip
                warmup_src = local_files[sizes[0]]
                backend.put_file(warmup_src, "/warmup.bin")
                backend.remove_file("/warmup.bin")

                if "put_file" not in skip:
                    for s in sizes:
                        print(f"  put_file {s} ...")
                        bench_put_file(backend, local_files[s], s, args.runs, results)

                # For get/metadata we need files already on the backend.
                remote_files = {}
                for s in sizes:
                    remote = f"/bench/{s}.bin"
                    if not backend.exists(remote):
                        backend.put_file(local_files[s], remote)
                    remote_files[s] = remote

                if "get_file" not in skip:
                    for s in sizes:
                        for nw in workers:
                            print(f"  get_file {s} workers={nw} ...")
                            bench_get_file(
                                backend,
                                remote_files[s],
                                s,
                                nw,
                                args.runs,
                                results,
                                tmpdir,
                            )

                if "metadata" not in skip:
                    print("  metadata (exists/checksum/date/owner) ...")
                    bench_metadata(
                        backend, remote_files[sizes[0]], sizes[0], args.runs, results
                    )

                if "ls" not in skip:
                    small = local_files[sizes[0]]
                    for n in ls_sizes:
                        print(f"  ls fixture: uploading {n} files ...")
                        sub = setup_ls_fixture(backend, n, small)
                        print(f"  ls {n} files ...")
                        bench_ls(backend, sub, n, args.runs, results)

                # Mid-size fixture for copy/move/remove/archive
                mid = "1MB" if "1MB" in local_files else sizes[0]
                mid_local = local_files[mid]

                if "copy_file" not in skip:
                    print("  copy_file 1MB ...")
                    copy_src = "/copy/src.bin"
                    if not backend.exists(copy_src):
                        backend.put_file(mid_local, copy_src)
                    bench_copy_file(backend, copy_src, args.runs, results)

                if "move_file" not in skip:
                    print("  move_file 1MB ...")
                    bench_move_file(backend, mid_local, args.runs, results)

                if "remove_file" not in skip:
                    print("  remove_file 1MB ...")
                    bench_remove_file(backend, mid_local, args.runs, results)

                if "put_archive" not in skip or "get_archive" not in skip:
                    # Build a small source tree (~1MB total across 4 files)
                    arc_root = audeer.path(tmpdir, "archive_src")
                    audeer.mkdir(arc_root)
                    for i in range(4):
                        make_random_file(
                            audeer.path(arc_root, f"file_{i}.bin"),
                            256 * 1024,
                        )

                if "put_archive" not in skip:
                    print("  put_archive 1MB zip ...")
                    bench_put_archive(backend, arc_root, args.runs, results)

                if "get_archive" not in skip:
                    print("  get_archive 1MB zip ...")
                    arc_remote = "/archive/download.zip"
                    if not backend.exists(arc_remote):
                        backend.put_archive(arc_root, arc_remote)
                    bench_get_archive(backend, arc_remote, tmpdir, args.runs, results)

    finally:
        if created_repo and not args.keep_repo:
            try:
                audbackend.backend.Artifactory.delete(args.host, repository)
                print(f"Deleted repository {repository!r}")
            except Exception as e:  # pragma: no cover
                print(f"WARNING: could not delete repository: {e}", file=sys.stderr)

    elapsed = time.perf_counter() - t_start
    print(f"Total wall time: {elapsed:.1f}s")

    out = args.output or f"benchmark/results/{args.label}.md"
    csv_path = out.rsplit(".", 1)[0] + ".csv"
    write_results(results, args.label, out, csv_path)
    print(f"Wrote {out}")
    print(f"Wrote {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
