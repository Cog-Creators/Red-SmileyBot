.. _deprecated-functionality:

===================================================
Future changes (currently deprecated functionality)
===================================================

.. include:: _includes/preamble.rst

.. contents::
    :depth: 4
    :local:

For Developers
**************

Removals
~~~~~~~~

``SimpleMenu.select_menu`` attribute
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. deprecated-removed:: 3.5.14 60

The `SimpleMenu.select_menu` attribute has been deprecated.

Any behaviour enabled by the usage of this attribute should no longer be depended on.
If you need this for something and cannot replace it with the other functionality,
create an issue on Red's issue tracker.

Downloader's shared libraries
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. deprecated:: 3.2.0

Shared libraries have been deprecated in favor of pip-installable libraries.
Shared libraries do not provide any functionality that can't already be achieved
with pip requirements *and* as such don't provide much value in return for
the added complexity.

Known issues, especially those related to hot-reload, were not handled automatically
for shared libraries, same as they are not handled for the libraries installed
through pip.
