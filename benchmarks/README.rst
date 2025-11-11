audbackend Benchmarks
=====================

Collection of benchmark scripts to evaluate functionality.


Parallel file loading
---------------------

The ``Minio`` backend support parallel loading of files.
It can be benchmarked with:

.. code-block:: bash

    $ uv run --python 3.12 minio-parallel.py

Run on a server with 10
Intel(R) Xeon(R) Platinum 8275CL CPUs @ 3.00GHz
it resulted in

=========== ======== ============== ==============
num_workers num_iter elapsed (avg)  elapsed (std)
=========== ======== ============== ==============
1           10       0:01:05.592122 0:00:04.613981
2           10       0:00:23.792445 0:00:03.151314
3           10       0:00:15.051508 0:00:00.020850
4           10       0:00:12.270467 0:00:00.744683
5           10       0:00:13.566350 0:00:00.284529
10          10       0:00:13.096010 0:00:00.575895
=========== ======== ============== ==============
