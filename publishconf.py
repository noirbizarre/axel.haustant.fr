#!/usr/bin/env python
# -*- coding: utf-8 -*- #
import os
import sys
sys.path.append(os.curdir)
from pelicanconf import *  # noqa

SITEURL = 'https://axel.haustant.fr'
RELATIVE_URLS = False

FEED_ALL_ATOM = 'feeds/all.atom.xml'
CATEGORY_FEED_ATOM = 'feeds/{slug}.atom.xml'

DELETE_OUTPUT_DIRECTORY = True

# Following items are often useful when publishing

#DISQUS_SITENAME = ""
#GOOGLE_ANALYTICS = ""

PLUGINS += (  # noqa
    'image_optimizer',
    'gzip_cache',
)

GOOGLE_ANALYTICS = 'UA-77403008-1'
