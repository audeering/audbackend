audbackend Benchmarks
=====================

Collection of benchmark scripts to evaluate functionality.


Parallel file loading
---------------------

The ``Minio`` backend supports parallel loading of files.
It can be benchmarked with:

.. code-block:: bash

    $ uv run --python 3.12 minio-parallel.py

Run on a server with 10
Intel(R) Xeon(R) Platinum 8275CL CPUs @ 3.00GHz
it resulted in

=========== ======== ============== ==============
num_workers num_iter elapsed (avg)  elapsed (std)
=========== ======== ============== ==============
1           10       0:00:45.036293 0:00:00.011121
2           10       0:00:22.550618 0:00:00.013874
3           10       0:00:15.725117 0:00:00.339047
4           10       0:00:13.304948 0:00:00.917220
5           10       0:00:11.589374 0:00:00.465975
10          10       0:00:13.865395 0:00:00.599119
=========== ======== ============== ==============
