import os
import sys
sys.path.insert(0, os.path.abspath('../htd_client'))


extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.autosummary',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.ifconfig',
    'sphinx.ext.viewcode',
    'sphinx.ext.extlinks',
]

if os.getenv('SPELLCHECK'):
    extensions += ('sphinxcontrib.spelling',)
    spelling_show_suggestions = True
    spelling_lang = 'en_US'

autodoc_default_options = {
    'members': True,
    # 'undoc-members': True,
    'show-inheritence': True,
}

source_suffix = '.rst'
master_doc = 'index'
project = 'htd_client'
year = '2024'
author = 'htd_client contributors'
copyright = f'{year}, {author}'
version = release = '0.0.1'

pygments_style = 'trac'
templates_path = ['.']
extlinks = {
    'issue': ('https://github.com/hikirsch/python-htd_client/issues/%s', '#'),
    'pr': ('https://github.com/hikirsch/python-htd_client/pull/%s', 'PR #'),
}

html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'navigation_depth': -1,  # -1 means show all levels
}

# html_theme_options = {
    # 'githuburl': 'https://github.com/hikirsch/python-htd_client/',
# }

html_use_smartypants = True
html_last_updated_fmt = '%b %d, %Y'
html_split_index = False
html_short_title = f'{project}-{version}'

napoleon_use_ivar = True
napoleon_use_rtype = False
napoleon_use_param = False