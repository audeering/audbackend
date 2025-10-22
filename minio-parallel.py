import datetime
import os
import time

import numpy as np
import pandas as pd

import audeer

import audbackend


class FastMinioBackend(audbackend.backend.Minio):
    r"""Alternative MinIO backend implementation for benchmarking."""

    def __init__(
        self,
        host: str,
        repository: str,
        *,
        num_workers: int = 1,
        chunk_size: int | None = None,
    ):
        super().__init__(
            host,
            repository,
            # num_workers=num_workers,
            # chunk_size=chunk_size,
        )
        self.num_workers = num_workers
        self.chunk_size = chunk_size

    def _get_file(
        self,
        src_path: str,
        dst_path: str,
        verbose: bool,
    ):
        r"""Get file from backend."""
        src_path = self.path(src_path)
        src_size = self._client.stat_object(self.repository, src_path).size

        def job(offset: int, length: int):
            try:
                # Fetch byte range from remote file
                response = self._client.get_object(
                    self.repository,
                    src_path,
                    offset=offset,
                    length=length,
                )
                data = response.read()
                # Write into correct spot in local file
                with open(dst_path, "r+b") as fp:
                    fp.seek(offset)
                    fp.write(data)
            except Exception as e:  # pragma: no cover
                raise RuntimeError(f"Error downloading file: {e}")
            finally:
                response.close()
                response.release_conn()

        params = []
        for offset in range(0, src_size, self.chunk_size):
            length = min(self.chunk_size, src_size - offset)
            params.append(([offset, length], {}))
        # Pre-allocate local file of same size
        with open(dst_path, "wb") as f:
            f.truncate(src_size)
        audeer.run_tasks(
            job,
            params,
            num_workers=self.num_workers,
            progress_bar=verbose,
        )


def main():
    host = "s3.dualstack.eu-north-1.amazonaws.com"
    repository = "audmodel-internal"
    dst_path = "./tmp.zip"
    num_iter = 10

    for name, src_path, version in [
        ("50mb", "/alm/speechgpt/vocoder/torch/a384dab4.zip", "1.0.0"),
        # ("5gb", "/alm/speechgpt/torch/36f24586.zip", "1.0.0"),
    ]:
        ds = []

        for backend_cls, num_workers, chunk_size in audeer.progress_bar(
            [
                # (Minio, 1, None),
                # (Minio, 5, 1024 * 1024),
                # (Minio, 10, 1024 * 1024),
                # (Minio, 5, 10 * 1024 * 1024),
                # (Minio, 10, 10 * 1024 * 1024),
                # (Minio, 5, 50 * 1024 * 1024),
                # (Minio, 10, 50 * 1024 * 1024),
                (FastMinioBackend, 5, 1024 * 1024),
                (FastMinioBackend, 10, 1024 * 1024),
                (FastMinioBackend, 5, 10 * 1024 * 1024),
                (FastMinioBackend, 10, 10 * 1024 * 1024),
                (FastMinioBackend, 5, 50 * 1024 * 1024),
                (FastMinioBackend, 10, 50 * 1024 * 1024),
            ]
        ):
            backend = backend_cls(
                host,
                repository,
                num_workers=num_workers,
                chunk_size=chunk_size,
            )
            backend.open()

            elapsed = []

            for _ in range(num_iter):
                if os.path.exists(dst_path):
                    os.remove(dst_path)

                interface = audbackend.interface.Maven(backend)

                t = time.time()
                interface.get_file(
                    src_path=src_path,
                    dst_path=dst_path,
                    version=version,
                )
                elapsed.append(time.time() - t)

            ds.append(
                {
                    "backend": backend.__class__.__name__,
                    "num_workers": num_workers,
                    "chunk_size[MB]": (
                        int(chunk_size / (1024 * 1024)) if chunk_size else 0
                    ),
                    "num_iter": num_iter,
                    "elapsed(avg)": str(datetime.timedelta(seconds=np.mean(elapsed))),
                    "elapsed(std)": str(datetime.timedelta(seconds=np.std(elapsed))),
                }
            )

            backend.close()

        df = pd.DataFrame(ds)
        df.to_csv(f"results-{name}.csv", index=False)
        df.to_markdown(f"results-{name}.md", index=False)


if __name__ == "__main__":
    main()
