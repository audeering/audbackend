audbackend.interface
====================

.. automodule:: audbackend.interface

To access the files on a backend users
can choose between two interfaces
:class:`audbackend.interface.Unversioned`
or
:class:`audbackend.interface.Versioned`:

.. autosummary::
    :toctree:
    :nosignatures:

    Unversioned
    Versioned

Users can implement their own
interface by deriving from
:class:`audbackend.interface.Base`

.. autosummary::
    :toctree:
    :nosignatures:

    Base
