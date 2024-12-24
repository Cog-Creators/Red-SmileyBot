.. _install-mac:

=======================
Installing Red on macOS
=======================

.. include:: _includes/supported-arch-x64+aarch64.rst

-------------------------------
Installing the pre-requirements
-------------------------------

To install pre-requirements, we first have to install Brew.
In Finder or Spotlight, search for and open *Terminal*. In the terminal, paste the
following, then press Enter:

.. prompt:: bash

    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    brew_location="$([ -n "$HOMEBREW_PREFIX" ] && echo "$HOMEBREW_PREFIX" || ([ "$(/usr/bin/uname -m)" = "arm64" ] && echo /opt/homebrew || echo /usr/local))/bin/brew"
    printf '\neval "$(%s shellenv)"\n' "$brew_location" >> "$([ -n "$ZSH_VERSION" ] && echo ~/.zprofile || ([ -f ~/.bash_profile ] && echo ~/.bash_profile || echo ~/.profile))"
    eval "$("$brew_location" shellenv)"

After the installation, install the required packages by pasting the commands and pressing enter,
one-by-one:

.. prompt:: bash

    brew install python@3.11
    brew install git
    brew install temurin@17

By default, Python installed through Homebrew is not added to the load path.
To fix this, you should run these commands:

.. prompt:: bash

    echo 'export PATH="$(brew --prefix)/opt/python@3.11/bin:$PATH"' >> "$([ -n "$ZSH_VERSION" ] && echo ~/.zprofile || ([ -f ~/.bash_profile ] && echo ~/.bash_profile || echo ~/.profile))"
    export PATH="$(brew --prefix)/opt/python@3.11/bin:$PATH"

.. Include common instructions:

.. include:: _includes/create-env-with-venv3.11.rst

.. include:: _includes/install-and-setup-red-unix.rst
