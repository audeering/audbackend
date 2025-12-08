Changelog
=========

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog`_,
and this project adheres to `Semantic Versioning`_.


Version 2.2.3 (2025-12-08)
--------------------------

* Added: support for Python 3.14
* Added: support for Artifactory backend
  in Python 3.13
* Fixed: require ``minio!=7.2.19``
  to avoid installing the broken ``minio`` package
* Removed: support for Python 3.9


Version 2.2.2 (2025-01-23)
--------------------------

* Added: support for Python 3.13
  (without Artifactory backend)
* Added: support for Artifactory backend
  in Python 3.12
* Changed: depend on ``dohq-artifactory>=1.0.0``
* Fixed: wrong path names
  in Artifactory backend with ``dohq-artifactory==1.0.0``


Version 2.2.1 (2024-11-27)
--------------------------

* Fixed: ensure we always use MD5 sums
  when comparing files
* Removed: ``audbackend.checksum()``,
  because the special handling
  of parquet file metadata checksums
  introduced potential issues


Version 2.2.0 (2024-11-18)
--------------------------

* Added: ``audbackend.checksum()``
  for calculating MD5 sum of files.
  For parquet files
  it considers the ``"hash"`` metadata entry instead,
  if it is present
* Changed: retry to re-establish connection to backend two times
  before finally failing
* Removed: deprecated functions
  ``audbackend.access()``,
  ``audbackend.create()``,
  ``audbackend.delete()``,
  ``audbackend.register()``
* Fixed: storing of checksum
  on S3/MinIO backends


Version 2.1.0 (2024-10-31)
--------------------------

* Added: ``audbackend.backend.Minio`` backend
  to access MinIO and S3 storages
* Added: support for Python 3.12
  (without Artifactory backend)
* Removed: support for Python 3.8


Version 2.0.1 (2024-05-14)
--------------------------

* Added: support for Python 3.11
* Fixed: ensure execution time of
  ``audbackend.interface.Maven.ls()``
  is independent of repository size
  on all backends


Version 2.0.0 (2024-05-10)
--------------------------

* Added: ``audbackend.interface`` sub-module
  including an backend interface base class
  ``audbackend.interface.Base``,
  and the three interfaces
  ``audbackend.interface.Maven``,
  ``audbackend.interface.Unversioned``,
  ``audbackend.interface.Versioned``
* Added: ``audbackend.backend`` sub-module
  including the backend base class
  ``audbackend.backend.Base``,
  and the two backends
  ``audbackend.backend.Artifactory``,
  ``audbackend.backend.FileSystem``
* Added: ``audbackend.backend.*.copy_file()``
  and ``audbackend.interface.*.copy_file()``
  methods
  to copy a file on the backend
* Added: ``audbackend.backend.*.move_file()``
  and ``audbackend.interface.*.move_file()``
  methods
  to move a file on the backend
* Added: ``validate=False`` argument to the
  ``copy_file()``,
  ``get_archive()``,
  ``get_file()``,
  ``move_file()``,
  ``put_archive()``,
  ``put_file()``
  methods in ``audbackend.backend.*``
  and ``audbackend.interface.*``.
  If ``True``
  the checksum of the resulting file is checked
* Added: ``audbackend.backend.*.create()``
  and ``audbackend.backend.*.delete()``
  class methods
  to create or delete a repository
  on a backend
* Added: ``audbackend.backend.*.open()``
  and ``audbackend.backend.*.close()``
  methods
  to connect to a backend,
  or disconnect from a backend
* Added: ``audbackend.backend.Artifactory.get_authentication()``
  to get the current Artifactory username, password
  from the configuration file/environment variable
* Added: ``authentication`` argument
  to ``audbackend.backend.Artifactory``
  and ``audbackend.backend.Base``
* Added: ``audbackend.backend.Artifactory.path()``
  returning an ``artifactory.ArtifactoryPath`` object
* Added: ``audbackend.backend.Artifactory.authentication``
  attribute,
  holding the current authentication object,
  e.g. user, password tuple
* Fixed: all backend methods now raise a ``ValueError``,
  if a backend path ends on ``"/"``
  with the exception of ``ls()``,
  ``split()``
  and ``join()``,
  as those methods support sub-paths as argument
* Deprecated: ``audbackend.create()``,
  use ``audbackend.backend.*.create()`` instead
* Deprecated: ``audbackend.delete()``,
  use ``audbackend.backend.*.delete()`` instead
* Deprecated: ``audbackend.register()``,
  as we no longer use alias names
  for backends
* Deprecated: ``audbackend.access()``,
  instantiate and open a backend instead
* Deprecated: ``audbackend.Repository``,
  as we no longer use alias names
  for backends
* Removed: ``audbackend.Artifactory``
  and ``audbackend.FileSystem``,
  use
  ``audbackend.backend.Artifactory``
  and ``audbackend.backend.FileSystem``
  instead
* Removed: ``audbackend.available()``


Version 1.0.2 (2024-02-13)
--------------------------

* Added: support for accessing
  remote and virtual repositories
  on Artifactory
* Fixed: match the ``pattern`` argument
  of ``audbackend.Backend.ls()``
  to file basenames
* Fixed: typo in raises section
  of the docstring
  of ``audbackend.exists()``


Version 1.0.1 (2023-10-18)
--------------------------

* Added: ``regex`` argument
  to ``audbackend.Backend._use_legacy_file_structure()``
  to support providing regex pattern
  in the ``extensions`` argument
* Changed: depend on ``dohq-artifactory>=0.9.0``


Version 1.0.0 (2023-10-16)
--------------------------

* Added:
  ``audbackend.Backend.access()``,
  ``audbackend.Backend.available()``,
  ``audbackend.Backend.date()``,
  ``audbackend.Backend.delete()``,
  ``audbackend.Backend.owner()``
* Added:
  ``audbackend.FileSystem._use_legacy_file_structure()``
  to support file structure of existing repositories
* Added: ``audbackend.BackendError`` class to capture errors raised by backend
* Added: ``pattern`` argument to ``audbackend.Backend.ls()``
* Added: docstring examples and usage section
* Changed: ``audbackend.create()`` raises error if repository exists
  (``audbackend.access()`` should be used instead)
* Changed: ``audbackend.Backend.get_archive()``
  and ``audbackend.Backend.put_archive()``
  support same archive types as ``audeer.create_archive()``
* Changed: ``audbackend.Backend.get_file()``
  skips operation if file with same checksum exists on local file system
* Changed: ``audbackend.Backend.get_file()`` uses a temporary directory
  to avoid corrupted files if operation is interrupted
* Changed: ``audbackend.Backend.get_file()``
  and ``audbackend.Backend.put_file()`` raise ``IsADirectoryError``
* Changed: ``audbackend.put_archive()`` raises ``NotADirectoryError``
* Changed: make ``files`` an optional argument of
  ``audbackend.Backend.put_archive()``
* Changed: ``audbackend.Backend.put_file()``
  passes checksum to implementation to avoid re-calculation
* Changed: ``audbackend.Backend.join()`` and ``audbackend.Backend.split()``
  check for invalid characters
* Changed: ``audbackend.Backend.ls()`` returns list of ``(path, ext, version)``
* Changed: ``audbackend.Backend.ls()`` accepts full path
* Changed: calculate checksum with ``audeer.md5()``
* Changed: file structure on ``audbackend.FileSystem``
  and ``audbackend.Artifactory`` from
  ``/sub/file/1.0.0/file-1.0.0.txt``
  to
  ``/sub/1.0.0/file.txt``
* Changed: remove ``ext`` argument
* Changed: path on backend must start with ``"/"``
* Changed: version must be non-empty and may not contain invalid characters
* Changed: option to install only specific backends
  and their dependencies
* Removed:
  ``audbackend.Backend.glob()``,
  ``audbackend.Backend.path()``
* Removed: support for ``Python 3.7``
* Removed: dependency on ``audfactory``


Version 0.3.18 (2023-02-17)
---------------------------

* Fixed: support ``dohq_artifactory.exception.ArtifactoryException``
  which was introduced in ``dohq_artifactory>=0.8``
  and is raised instead of a HTTP request error


Version 0.3.17 (2023-02-13)
---------------------------

* Added: support for Python 3.10
* Changed: depend on ``audfactory>=1.0.10``


Version 0.3.16 (2022-10-13)
---------------------------

* Added: argument ``tmp_root`` to
  ``audbackend.Backend.get_archive()`` and
  ``audbackend.Backend.put_archive()``


Version 0.3.15 (2022-04-01)
---------------------------

* Changed: depend on ``audfactory>=1.0.8``
  to change a critical bug
  when looking for available versions of an artifact


Version 0.3.14 (2022-02-24)
---------------------------

* Changed: check for path name before creating archive
  in ``audbackend.Backend.put_archive()``


Version 0.3.13 (2022-01-03)
---------------------------

* Added: Python 3.9 support
* Removed: Python 3.6 support


Version 0.3.12 (2021-09-28)
---------------------------

* Added: ``verbose`` argument to
  ``Backend.get_archive()``,
  ``Backend.get_file()``,
  ``Backend.put_archive()``,
  ``Backend.put_file()``


Version 0.3.11 (2021-09-28)
---------------------------

* Fixed: catch 403 Error for Artifactory backend paths


Version 0.3.10 (2021-08-05)
---------------------------

* Added: ``audbackend.Backend.ls()``


Version 0.3.9 (2021-07-22)
--------------------------

* Fixed: ignore empty strings in ``backend.join()``


Version 0.3.8 (2021-07-13)
--------------------------

* Added: ``Repository``


Version 0.3.7 (2021-07-13)
--------------------------

* Added: ``Repository``


Version 0.3.6 (2021-06-17)
--------------------------

* Changed: link to ``audfactory`` documentation for Artifactory authentication
* Changed: split up source code into several files


Version 0.3.5 (2021-05-11)
--------------------------

* Added: argument ``folder`` to ``Backend.glob()``


Version 0.3.4 (2021-05-06)
--------------------------

* Added: support files without extension and file extensions with dot(s)


Version 0.3.3 (2021-03-29)
--------------------------

* Fixed: ``audbackend.Artifactory.exists()`` for cases of missing permissions


Version 0.3.2 (2021-03-29)
--------------------------

* Fixed: use ``audfactory >=1.0.3`` as it fixes ``versions()``
  for paths with missing user permissions


Version 0.3.1 (2021-03-26)
--------------------------

* Changed: adjust Python package keywords to ``artifactory``, ``filesystem``
* Fixed: contribution section in documentation now provides correct links
  and explains Artifactory server access for running tests


Version 0.3.0 (2021-03-26)
--------------------------

* Added: open source release on Github
* Changed: use ``audfactory`` >=1.0.0
* Changed: use public Artifactory server for tests


Version 0.2.0 (2021-02-22)
--------------------------

* Added: ``audbackend.FileSystem`` backend
* Changed: rename package to ``audbackend``
* Changed: include ``repository`` argument in the init methods of the backends


Version 0.1.1 (2021-02-19)
--------------------------

* Fixed: missing ``__init__`` file in ``audb_artifactory.core``


Version 0.1.0 (2021-02-19)
--------------------------

* Added: Initial release
* Added: ``audb_artifactory.Artifactory``


.. _Keep a Changelog:
    https://keepachangelog.com/en/1.0.0/
.. _Semantic Versioning:
    https://semver.org/spec/v2.0.0.html
