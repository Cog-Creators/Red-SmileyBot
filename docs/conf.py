#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Red - Discord Bot documentation build configuration file, created by
# sphinx-quickstart on Thu Aug 10 23:18:25 2017.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

sys.path.insert(0, os.path.abspath(".."))

os.environ["BUILDING_DOCS"] = "1"


# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.doctest",
    "sphinxcontrib_trio",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# General information about the project.
project = "Red - Discord Bot"
copyright = "2018-2020, Cog Creators"
author = "Cog Creators"

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
from redbot.core import __version__
from discord import __version__ as dpy_version

# The short X.Y version.
version = __version__
# The full version, including alpha/beta/rc tags.
release = __version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = None

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = False

# Role which is assigned when you make a simple reference within backticks
default_role = "any"

# Includes substitutions for all files
with open("prolog.txt", "r") as file:
    rst_prolog = file.read()

# Adds d.py version to available substitutions in all files
rst_prolog += f"\n.. |DPY_VERSION| replace:: {dpy_version}"

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
# html_theme_options = {}

html_context = {
    # Enable the "Edit in GitHub link within the header of each page.
    "display_github": True,
    "github_user": "Cog-Creators",
    "github_repo": "Red-DiscordBot",
    "github_version": "V3/develop/docs/",
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ['_static']

# Custom sidebar templates, must be a dictionary that maps document names
# to template names.
#
# This is required for the alabaster theme
# refs: http://alabaster.readthedocs.io/en/latest/installation.html#sidebars
# html_sidebars = {
#     "**": [
#         "about.html",
#         "navigation.html",
#         "relations.html",  # needs 'show_related': True theme option to display
#         "searchbox.html",
#         "donate.html",
#     ]
# }


# -- Options for HTMLHelp output ------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = "Red-DiscordBotdoc"


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    # 'papersize': 'letterpaper',
    # The font size ('10pt', '11pt' or '12pt').
    #
    # 'pointsize': '10pt',
    # Additional stuff for the LaTeX preamble.
    #
    # 'preamble': '',
    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, "Red-DiscordBot.tex", "Red - Discord Bot Documentation", "Cog Creators", "manual")
]


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [(master_doc, "red-discordbot", "Red - Discord Bot Documentation", [author], 1)]


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (
        master_doc,
        "Red-DiscordBot",
        "Red - Discord Bot Documentation",
        author,
        "Red-DiscordBot",
        "One line description of project.",
        "Miscellaneous",
    )
]


# -- Options for linkcheck builder ----------------------------------------

# A list of regular expressions that match URIs that should not be
# checked when doing a linkcheck build.
linkcheck_ignore = [r"https://java.com*", r"https://chocolatey.org*"]
linkcheck_retries = 3


# -- Options for extensions -----------------------------------------------

# Intersphinx
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "dpy": (f"https://discordpy.readthedocs.io/en/v{dpy_version}/", None),
    "motor": ("https://motor.readthedocs.io/en/stable/", None),
    "babel": ("http://babel.pocoo.org/en/stable/", None),
}

# Extlinks
# This allows to create links to d.py docs with
# :dpy_docs:`link text <site_name.html>`
extlinks = {
    "dpy_docs": (f"https://discordpy.readthedocs.io/en/v{dpy_version}/%s", None),
    "issue": ("https://github.com/Cog-Creators/Red-DiscordBot/issues/%s", "#"),
    "ghuser": ("https://github.com/%s", "@"),
}

# Doctest
# If this string is non-empty, all blocks with ``>>>`` in them will be
# tested, not just the ones explicitly marked with ``.. doctest::``
doctest_test_doctest_blocks = ""

# Autodoc options
autodoc_default_options = {"show-inheritance": True}
autodoc_typehints = "none"
