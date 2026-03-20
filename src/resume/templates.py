import re

from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from .config import Config
from .i18n import ContextTranslations

directory = "templates"

ICONS_DIR = Path("images") / "icons"

# Inject class="icon" and aria-hidden="true" into the root <svg> tag
_SVG_TAG_RE = re.compile(r"<svg\b", re.IGNORECASE)


def _make_icon_helper(root: Path):
    """Create an icon() helper bound to a project root directory."""
    icons_dir = root / ICONS_DIR

    @lru_cache(maxsize=None)
    def _read_svg(path: Path) -> str:
        return path.read_text(encoding="utf-8").strip()

    def icon(name: str, cls: str = "") -> Markup:
        """Read an SVG icon file and return it as inline markup.

        Args:
            name: Icon name (without .svg extension), matching a file in images/icons/.
            cls: Optional extra CSS class(es) to add alongside "icon".
        """
        svg_path = icons_dir / f"{name}.svg"
        if not svg_path.exists():
            return Markup(f"<!-- icon not found: {name} -->")

        svg = _read_svg(svg_path)
        classes = f"icon icon-{name} {cls}".strip()
        svg = _SVG_TAG_RE.sub(
            f'<svg class="{classes}" aria-hidden="true"',
            svg,
            count=1,
        )
        return Markup(svg)

    return icon


def get_env(config: Config) -> Environment:
    env = Environment(
        loader=FileSystemLoader(config.root / directory),
        autoescape=select_autoescape(),
        extensions=["jinja2.ext.i18n"],
    )
    env.install_gettext_translations(ContextTranslations(config.languages))
    env.globals["icon"] = _make_icon_helper(config.root)
    return env
