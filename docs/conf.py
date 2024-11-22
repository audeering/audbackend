from datetime import date

import toml

import audeer

import audbackend


config = toml.load(audeer.path("..", "pyproject.toml"))


# Project -----------------------------------------------------------------
project = config["project"]["name"]
author = ", ".join(author["name"] for author in config["project"]["authors"])
copyright = f"2021-{date.today().year} audEERING GmbH"
version = audbackend.__version__
title = "Documentation"


# General -----------------------------------------------------------------
master_doc = "index"
source_suffix = ".rst"
exclude_patterns = [
    "api-src",
    "build",
    "tests",
    "Thumbs.db",
    ".DS_Store",
]
pygments_style = None
extensions = [
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
    "sphinx_copybutton",
    "sphinx_apipages",
]

napoleon_use_ivar = True  # List of class attributes
autodoc_inherit_docstrings = False  # disable docstring inheritance
intersphinx_mapping = {
    "audeer": ("https://audeering.github.io/audeer/", None),
    "pandas": ("https://pandas.pydata.org/pandas-docs/stable/", None),
    "python": ("https://docs.python.org/3/", None),
}
linkcheck_ignore = [
    "https://gitlab.audeering.com",
]
# Ignore package dependencies during building the docs
# This fixes URL link issues with pandas and sphinx_autodoc_typehints
autodoc_mock_imports = [
    "pandas",
]


# HTML --------------------------------------------------------------------
html_theme = "sphinx_audeering_theme"
html_theme_options = {
    "display_version": True,
    "logo_only": False,
    "footer_links": False,
}
html_context = {
    "display_github": True,
}
html_title = title
