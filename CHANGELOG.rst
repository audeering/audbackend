Changelog
=========

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog`_,
and this project adheres to `Semantic Versioning`_.


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
* Changed: path on backend must start with ``'/'``
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
