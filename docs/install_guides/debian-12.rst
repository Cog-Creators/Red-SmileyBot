.. _install-debian-12:

====================================
Installing Red on Debian 12 Bookworm
====================================

.. include:: _includes/supported-arch-x64+aarch64+armv7l.rst

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

Debian 12 "Bookworm" has all required packages available in official repositories. Install them
with apt:

.. prompt:: bash

    sudo apt update
    sudo apt -y install python3 python3-dev python3-venv git openjdk-17-jre-headless build-essential nano

.. Include common instructions:

.. include:: _includes/create-env-with-venv3.11.rst

.. include:: _includes/install-and-setup-red-unix.rst
