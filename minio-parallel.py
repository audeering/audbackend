# /// script
# dependencies = [
#   "audbackend[all]",
#   "numpy",
#   "pandas",
#   "tabulate",
# ]
# [tool.uv.sources]
# audbackend = { path = ".", editable = true }
# ///
import datetime
import os
import time

import numpy as np
import pandas as pd

import audeer

import audbackend


def main():
    host = "s3.dualstack.eu-north-1.amazonaws.com"
    repository = "audmodel-internal"
    dst_path = "./tmp.zip"
    num_iter = 10

    for name, src_path, version in [
        ("50mb", "/alm/speechgpt/vocoder/torch/a384dab4.zip", "1.0.0"),
        ("5gb", "/alm/speechgpt/torch/36f24586.zip", "1.0.0"),
    ]:
        ds = []

        for num_workers in audeer.progress_bar([1, 5, 10]):
            backend = audbackend.backend.Minio(host, repository)
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
                    num_workers=num_workers,
                )
                elapsed.append(time.time() - t)

            ds.append(
                {
                    "backend": backend.__class__.__name__,
                    "num_workers": num_workers,
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
