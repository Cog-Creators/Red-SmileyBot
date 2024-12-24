.. _install-raspberry-pi-os-11:

======================================================
Installing Red on Raspberry Pi OS (Legacy) 11 Bullseye
======================================================

.. include:: _includes/supported-arch-aarch64+armv7l.rst

.. note::

    While we do provide support and install instructions for running Red
    on Raspberry Pi OS (Legacy) 11 Bullseye, we highly recommend installing/upgrading to
    the new version - Raspberry Pi OS 12 Bookworm.

    If you're not sure what version you are using,
    you can check your version of Raspberry Pi OS by running:

    .. prompt:: bash

        lsb_release -a

    If you're running Bookworm already, read `install-raspberry-pi-os-12` document instead.

    If you're using Bullseye, please consider performing a clean install of Bookworm if possible.

.. include:: _includes/linux-preamble.rst

-------------------------------
Installing the pre-requirements
-------------------------------

Raspberry Pi OS "Bullseye" has all required packages available in official repositories. Install them
with apt:

.. prompt:: bash

    sudo apt update
    sudo apt -y install python3 python3-dev python3-venv git openjdk-17-jre-headless build-essential nano

.. Include common instructions:

.. include:: _includes/create-env-with-venv3.9.rst

.. include:: _includes/install-and-setup-red-unix.rst
