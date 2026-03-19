import subprocess

from contextvars import ContextVar

from babel.support import NullTranslations, Translations
from cyclopts import App

from .config import Config

app = App(name="i18n", help="Internationalization commands")
domain = "resume"
mapping_file = "babel.cfg"
directory = "locales"

LOCALE: ContextVar[str] = ContextVar("LOCALE", default="en")


def set_locale(locale: str):
    LOCALE.set(locale)


class ContextTranslations:
    def __init__(self, locales: list[str]):
        self.locales = {
            locale: Translations.load(directory, locales=[locale], domain=domain)
            for locale in locales
        }
        print(f"{self.locales=}")

    @property
    def locale(self) -> str:
        return LOCALE.get()

    @property
    def translations(self) -> NullTranslations:
        return self.locales[self.locale]

    def gettext(self, message: str):
        return self.translations.gettext(message)

    def ngettext(self, singular: str, plural: str, num: int):
        return self.translations.ngettext(singular, plural, num)


@app.command
def extract(config: Config = Config()):
    """Extract and update translatable strings"""
    # Create or update .pot Catalog file
    subprocess.run(f"pybabel extract -F {mapping_file} -o {directory}/{domain}.pot .", shell=True)
    # Update .po files for each language
    subprocess.run(f"pybabel update -i {directory}/{domain}.pot -d {directory}", shell=True)


@app.command
def compile(config: Config = Config()):
    """Compile translated strings"""
    subprocess.run(f"pybabel compile -d {directory}", shell=True)
