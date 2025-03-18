# Anything imported here will be available globally in templates
# You can add more imports and functions to helpers.py as necessary to
# make features available in your templates.

# More info
# https://docs.pylonsproject.org/projects/pyramid_cookbook/en/latest
# /templates/templates.html

from privatim.git_info import get_git_revision_hash
from markupsafe import Markup   # noqa: F401


git_revision = get_git_revision_hash()
