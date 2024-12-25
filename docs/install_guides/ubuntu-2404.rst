.. _install-ubuntu-2404:

==================================
Installing Red on Ubuntu 24.04 LTS
==================================

.. include:: _includes/supported-arch-x64+aarch64.rst

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

We recommend adding the ``deadsnakes`` ppa to install Python 3.11:

.. prompt:: bash

    sudo apt update
    sudo apt -y install software-properties-common
    sudo add-apt-repository -y ppa:deadsnakes/ppa

Now install the pre-requirements with apt:

.. prompt:: bash

    sudo apt -y install python3.11 python3.11-dev python3.11-venv git openjdk-17-jre-headless build-essential nano

.. Include common instructions:

.. include:: _includes/create-env-with-venv3.11.rst

.. include:: _includes/install-and-setup-red-unix.rst
