# -*- coding: utf-8 -*-
'''
PDF Generator
-------

The pdf plugin generates PDF files from reStructuredText and Markdown sources.
'''

from __future__ import unicode_literals, print_function

from io import open
from pelican import signals
from pelican.generators import Generator
from pelican.readers import MarkdownReader
from weasyprint import HTML

import os
import logging

logger = logging.getLogger(__name__)


def cv_as_pdf(pelican):
    filename = os.path.join(pelican.output_path, 'index.html')
    # output = os.path.join(pelican.output_path, 'cv.pdf')
    # with open(filename) as infile:
    #     html = infile.read()
    #     html = html.replace('/theme', 'file://{0}/theme'.format(pelican.output_path))
    # HTML(string=html).write_pdf(output)


def register():
    signals.finalized.connect(cv_as_pdf)
