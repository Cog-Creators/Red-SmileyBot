.. _windows-install-guide:

=========================
Installing Red on Windows
=========================

.. include:: _includes/supported-arch-x64.rst

-------------------------------
Installing the pre-requirements
-------------------------------

Please install the pre-requirements by following instructions from one of the following subsections.

.. contents:: Choose a method of installing pre-requirements:
    :local:

----

*********************************************
Using PowerShell and Chocolatey (recommended)
*********************************************

To install via PowerShell, search "powershell" in the Windows start menu,
right-click on it and then click "Run as administrator".

Then run each of the following commands:

.. prompt:: powershell

    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    choco upgrade git --params "/GitOnlyOnPath /WindowsTerminal" -y
    choco upgrade visualstudio2022-workload-vctools -y
    choco upgrade python311 -y

For Audio support, you should also run the following command before exiting:

.. prompt:: powershell

    choco upgrade temurin17 -y


From here, exit the prompt then continue onto `creating-venv-windows`.

----

********************************
Manually installing dependencies
********************************

.. attention:: There are additional configuration steps required which are
               not documented for installing dependencies manually.
               These dependencies are only listed separately here for
               reference purposes.

* `MSVC Build tools <https://www.visualstudio.com/downloads/#build-tools-for-visual-studio-2019>`_

* `Python 3.8.1 - 3.11.x <https://www.python.org/downloads/windows/>`_

.. attention:: Please make sure that the box to add Python to PATH is CHECKED, otherwise
               you may run into issues when trying to run Red.

* `Git 2.11+ <https://git-scm.com/download/win>`_

.. attention:: Please choose the option to "Git from the command line and also from 3rd-party software" in Git's setup.

* `Java 17 <https://adoptium.net/temurin/releases/?version=17>`_ - needed for Audio

From here, continue onto `creating-venv-windows`.

----

.. _creating-venv-windows:

------------------------------
Creating a Virtual Environment
------------------------------

.. tip::

    If you want to learn more about virtual environments, see page: `about-venvs`.

We require installing Red into a virtual environment. Don't be scared, it's very
straightforward.

First, choose a directory where you would like to create your virtual environment. It's a good idea
to keep it in a location which is easy to type out the path to. From now, we'll call it
``redenv`` and it will be located in your home directory.

Start with opening a command prompt (open Start, search for "command prompt", then click it).

.. note:: 

    You shouldn't run command prompt as administrator when creating your virtual environment, or
    running Red.

.. warning::

    These commands will not work in PowerShell - you have to use command prompt as said above.

Then create your virtual environment with the following command

.. prompt:: batch

    py -3.11 -m venv "%userprofile%\redenv"

And activate it with the following command

.. prompt:: batch

    "%userprofile%\redenv\Scripts\activate.bat"

.. important::

    You must activate the virtual environment with the above command every time you open a new
    Command Prompt to run, install or update Red.


.. _installing-red-windows:

--------------
Installing Red
--------------

.. attention:: You may need to restart your computer after installing dependencies
               for the PATH changes to take effect.

Run **one** of the following set of commands, depending on what extras you want installed

  * Normal installation:

    .. prompt:: batch
        :prompts: (redenv) C:\\>

        python -m pip install -U pip wheel
        python -m pip install -U Red-DiscordBot

  * With PostgreSQL support:

    .. prompt:: batch
        :prompts: (redenv) C:\\>

        python -m pip install -U pip wheel
        python -m pip install -U Red-DiscordBot[postgres]

--------------------------
Setting Up and Running Red
--------------------------

After installation, set up your instance with the following command:

.. prompt:: batch
    :prompts: (redenv) C:\\>

    redbot-setup

This will set the location where data will be stored, as well as your
storage backend and the name of the instance (which will be used for
running the bot).

Once done setting up the instance, run the following command to run Red:

.. prompt:: batch
    :prompts: (redenv) C:\\>

    redbot <your instance name>

It will walk through the initial setup, asking for your token and a prefix.
`See how to obtain a token. <../bot_application_guide>`

.. tip::
   If it's the first time you're using Red, you should check our `getting-started` guide
   that will walk you through all essential information on how to interact with Red.
