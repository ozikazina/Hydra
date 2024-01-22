# Docs code and macros based on blog post by Antoine Beyeler
# https://bylr.info/articles/2022/05/10/api-doc-with-sphinx-autoapi/

project = 'Hydra'
copyright = '2024, Ondřej Vlček'
author = 'Ondřej Vlček'
language = 'en'

import re
from pathlib import Path

root = Path(__file__).parent.parent.resolve()

R_VERSION = re.compile(r'version.*?(\d,\s*\d,\s*\d)')
with open(root.joinpath('src', 'hydra', '__init__.py'), 'r') as f:
    for line in f:
        if match := R_VERSION.search(line):
            release = re.sub(r'\s*,\s*', '.', match.group(1).strip())
            break
    else:
        raise RuntimeError('Version not found')

# -- General configuration ---------------------------------------------------

extensions = [
    'autoapi.extension'
]

autoapi_dirs = [
    root.joinpath("src", "hydra")
]

autoapi_type = "python"
autoapi_keep_files = True
autodoc_typehints = "signature"
autoapi_member_order = "alphabetical"

autoapi_options = [
    "members",
    # "undoc-members",
    "show-inheritance",
    "show-module-summary",
    # "imported-members",
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------

html_theme = 'furo'
html_static_path = ['_static']

# -- Custom functions --------------------------------------------------------

allowed_blender_names = ["bl_idname", "bl_space_type"]
R_MEMBER_NAME = re.compile(r'bl_\w+$')

def skip_member(app, what, name: str, obj, skip, options):
    if (member := R_MEMBER_NAME.search(name)) and\
        member.group() not in allowed_blender_names:
        return True
    return False

def setup(sphinx):
    sphinx.connect("autoapi-skip-member", skip_member)