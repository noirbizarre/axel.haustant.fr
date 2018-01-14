#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

import json
import os

from dateutil.parser import parse

AUTHOR = 'Axel Haustant'
SITENAME = 'Axel Haustant'
SITEURL = 'https://axel.haustant.fr'

TIMEZONE = 'Europe/Paris'

DEFAULT_LANG = 'fr'

THEME = 'theme'

PATH = os.path.dirname(__file__)
OUTPUT_PATH = os.path.join(PATH, 'output')
ARTICLE_PATHS = [
    # 'articles',
]

CONTACT_EMAIL = 'axel-[at]-haustant.fr'

# PAGE_PATHS = [
#     'pages',
# ]


# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Blogroll
LINKS = (('Pelican', 'http://getpelican.com/'),
         ('Python.org', 'http://python.org/'),
         ('Jinja2', 'http://jinja.pocoo.org/'),
         ('You can modify those links in your config file', '#'),)

# Social widget
SOCIAL = (('You can add links in your config file', '#'),
          ('Another social link', '#'),)

DEFAULT_PAGINATION = 10

# Uncomment following line if you want document-relative URLs when developing
# RELATIVE_URLS = True


PLUGIN_PATHS = [
    # 'plugins',
    'local_plugins',
]

PLUGINS = [
    'sitemap',
    'frontmark',
    'data',
    # 'cv2pdf',
    'i18n_subsites',
]

DATA_PATHS = [
    'data.fr',
]

DATA = [
    'me.md',
    'education.yml',
    'experiences',
    'expertise.yml',
    'projects.md',
    'skills.yml',
    'jsonld.json',
]

I18N_SUBSITES = {
    'en': {
        'DATA_PATHS': ['data.en']
    }
}

SITEMAP = {
    'format': 'xml',
    'priorities': {
        'articles': 0.5,
        'indexes': 0.5,
        'pages': 0.5
    },
    'changefreqs': {
        'articles': 'daily',
        'indexes': 'daily',
        'pages': 'monthly'
    }
}


# Jinja Configuration
JINJA_ENVIRONMENT = {
    'extensions': ['jinja2.ext.i18n']
}
I18N_GETTEXT_LOCALEDIR = 'translations'
I18N_TEMPLATES_LANG = 'en'
I18N_GETTEXT_NEWSTYLE = True


SOCIAL = {
    'github': 'http://github.com/noirbizarre',
    'twitter': 'http://twitter.com/noirbizarre',
    'linkedin': 'http://fr.linkedin.com/in/axelhaustant/',
    'viadeo': 'http://www.viadeo.com/p/00216b5hkf3xcvsh',
    'phone': 'tel:+33781149707',
}


def json_filter(value):
    return json.dumps(value)


def dtformat(value, format='%c'):
    if not value:
        return None
    return parse(value).strftime(format).title()


JINJA_FILTERS = {
    'json': json_filter,
    'dtformat': dtformat,
}
