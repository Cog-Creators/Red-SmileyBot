.DEFAULT_GOAL := help

PYTHON ?= python3.8

ROOT_DIR:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

ifneq ($(wildcard $(ROOT_DIR)/.venv/.),)
	VENV_PYTHON = $(ROOT_DIR)/.venv/bin/python
else
	VENV_PYTHON = $(PYTHON)
endif

define HELP_BODY
Usage:
  make <command>

Commands:
  reformat                   Reformat all .py files being tracked by git.
  stylecheck                 Check which tracked .py files need reformatting.
  stylediff                  Show the post-reformat diff of the tracked .py files
                             without modifying them.
  gettext                    Generate pot files.
  upload_translations        Upload pot files to Crowdin.
  download_translations      Download translations from Crowdin.
  bumpdeps                   Run script bumping dependencies.
  newenv                     Create or replace this project's virtual environment.
  syncenv                    Sync this project's virtual environment to Red's latest
                             dependencies.
endef
export HELP_BODY

# Python Code Style
reformat:
	$(VENV_PYTHON) -m black $(ROOT_DIR)
stylecheck:
	$(VENV_PYTHON) -m black --check $(ROOT_DIR)
stylediff:
	$(VENV_PYTHON) -m black --check --diff $(ROOT_DIR)

# Translations
gettext:
	$(PYTHON) -m redgettext --command-docstrings --verbose --recursive redbot --exclude-files "redbot/pytest/**/*"
upload_translations:
	crowdin upload sources
download_translations:
	crowdin download

# Dependencies
bumpdeps:
	$(PYTHON) tools/bumpdeps.py

# Development environment
newenv:
	$(PYTHON) -m venv --clear .venv
	.venv/bin/pip install -U pip wheel
	$(MAKE) syncenv
syncenv:
	.venv/bin/pip install -Ur ./tools/dev-requirements.txt

# Help
help:
	@echo "$$HELP_BODY"
