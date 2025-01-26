.. _install-fedora:

==============================
Installing Red on Fedora Linux
==============================

.. include:: _includes/supported-arch-x64+aarch64.rst

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

Fedora Linux 40 and above has all required packages available in official repositories. Install
them with dnf:

.. prompt:: bash

    sudo dnf -y install python3.11 python3.11-devel git java-17-openjdk-headless @development-tools nano

.. Include common instructions:

.. include:: _includes/create-env-with-venv3.11.rst

.. include:: _includes/install-and-setup-red-unix.rst
