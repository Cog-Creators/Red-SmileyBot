.. _install-ubuntu-2004:

==================================
Installing Red on Ubuntu 20.04 LTS
==================================

.. include:: _includes/supported-arch-x64+aarch64.rst

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

Ubuntu 20.04 LTS has all required packages available in official repositories. Install them
with apt:

.. prompt:: bash

    sudo apt update
    sudo apt -y install python3.9 python3.9-dev python3.9-venv git openjdk-17-jre-headless build-essential nano

.. Include common instructions:

.. include:: _includes/create-env-with-venv3.9.rst

.. include:: _includes/install-and-setup-red-unix.rst
