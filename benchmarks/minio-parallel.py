# /// script
# dependencies = [
#   "audbackend[all]",
#   "numpy",
#   "pandas",
#   "tabulate",
# ]
# [tool.uv.sources]
# audbackend = { path = "..", editable = true }
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
    src_path = "/alm/audeering-omni/stage1_2/torch/7289b57d.zip"
    version = "1.0.0"
    dst_path = "./tmp.zip"
    num_iter = 10

    ds = []

    for num_workers in audeer.progress_bar([1, 2, 3, 4, 5, 10]):
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
                "num_workers": num_workers,
                "num_iter": num_iter,
                "elapsed(avg)": str(datetime.timedelta(seconds=np.mean(elapsed))),
                "elapsed(std)": str(datetime.timedelta(seconds=np.std(elapsed))),
            }
        )

        backend.close()

    df = pd.DataFrame(ds)
    df.to_csv("results.csv", index=False)
    df.to_markdown("results.md", index=False)


if __name__ == "__main__":
    main()
