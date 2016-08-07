from __future__ import unicode_literals

import locale
import os
import shutil
import slugify
import sys

from datetime import datetime

from invoke import run as raw_run, task
from pelican import Pelican
from pelican.settings import read_settings
from jinja2 import Environment, FileSystemLoader


#: Project absolute root path
TASKS_ROOT = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(TASKS_ROOT, '..'))

CONF_FILE = os.path.join(ROOT, 'pelicanconf.py')

# Port for `serve`
PORT = 5000

RSYNC_TARGET = 'ah-core-01:/srv/axel.haustant.fr/'


class objdict(dict):
    def __getattr__(self, name):
        return self[name]


def get_settings():
    return objdict(read_settings(CONF_FILE))


jinja_env = Environment(loader=FileSystemLoader(TASKS_ROOT))


def jinja(template, filename, **ctx):
    template = jinja_env.get_template(template)
    with open(filename, 'wb') as out:
        data = template.render(**ctx)
        out.write(data.encode('utf-8'))


def run(cmd, *args, **kwargs):
    '''Run a command ensuring cwd is project root'''
    return raw_run('cd {0} && {1}'.format(ROOT, cmd), *args, **kwargs)


def prompt(text):
    encoding = sys.stdin.encoding or locale.getpreferredencoding(True)
    return raw_input(text).decode(encoding)


@task
def clean(ctx):
    '''Remove generated files'''
    settings = get_settings()
    if os.path.isdir(settings.OUTPUT_PATH):
        shutil.rmtree(settings.OUTPUT_PATH)
        os.makedirs(settings.OUTPUT_PATH)


@task()
def build(ctx, verbose=False, debug=False):
    '''Build local version of site'''
    cmd = 'pelican -s publishconf.py'
    if verbose:
        cmd += ' -v'
    if verbose:
        cmd += ' -D'
    run(cmd)


@task
def publish(ctx):
    '''Publish using rsync'''
    run('rsync -avz output/ {0}'.format(RSYNC_TARGET))


@task
def draft(ctx, markdown):
    '''Create a draft page'''
    title = prompt('Title:')
    slug = slugify.slugify(title, to_lower=True)
    slug = prompt('Slug ({0}):'.format(slug)) or slug
    category = prompt('Category:')
    summary = prompt('Summary:')
    tags = prompt('Tags:')
    filename = os.path.join('articles',
                            slugify.slugify(category, to_lower=True),
                            '{0}.rst'.format(slug))
    jinja('draft.j2.rst', filename,
          title=title,
          slug=slug,
          category=category,
          summary=summary,
          tags=tags,
          date=datetime.now())


def compile():
    settings = get_settings()
    p = Pelican(settings)
    try:
        p.run()
    except SystemExit as e:
        pass


@task
def watch(ctx):
    '''Serve the blog and watch changes'''
    from livereload import Server

    settings = get_settings()
    compile()
    server = Server()
    server.watch(CONF_FILE, compile)

    server.watch('theme', compile)
    server.watch(settings.I18N_GETTEXT_LOCALEDIR, compile)

    for root in getattr(settings, 'DATA_PATHS', []):
        for data in getattr(settings, 'DATA', []):
            path = os.path.join(root, data)
            if os.path.exists(path):
                server.watch(path, compile)

    paths = settings.ARTICLE_PATHS + settings.PAGE_PATHS + settings.PLUGIN_PATHS
    for path in paths:
        server.watch(path, compile)

    server.serve(port=PORT, root=settings.OUTPUT_PATH)


@task
def i18n(ctx):
    '''Extract translatable strings'''
    run('pybabel extract -F babel.cfg -o translations/messages.pot .')
    run('pybabel update -i translations/messages.pot -d translations -l fr')


@task
def i18nc(ctx):
    '''Compile translations'''
    run('pybabel compile -d translations')
