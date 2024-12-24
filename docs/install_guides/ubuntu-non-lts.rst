.. _install-ubuntu-non-lts:

=========================================
Installing Red on Ubuntu non-LTS versions
=========================================

.. include:: _includes/supported-arch-x64+aarch64.rst

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

Now install the pre-requirements with apt:

.. prompt:: bash

    sudo apt update
    sudo apt -y install python3.11 python3.11-dev python3.11-venv git openjdk-17-jre-headless build-essential nano

.. Include common instructions:

.. include:: _includes/create-env-with-venv3.11.rst

.. include:: _includes/install-and-setup-red-unix.rst
