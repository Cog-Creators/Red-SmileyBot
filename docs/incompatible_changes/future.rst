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
