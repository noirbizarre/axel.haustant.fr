from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import Config
from .i18n import ContextTranslations

directory = "templates"

def get_env(config: Config) -> Environment:
    env = Environment(
        loader=FileSystemLoader(config.root / directory),
        autoescape=select_autoescape(),
        extensions=["jinja2.ext.i18n"],
    )
    env.install_gettext_translations(ContextTranslations(config.languages))
    return env
