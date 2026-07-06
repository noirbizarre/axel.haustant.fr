import json
import re
import sys

from pathlib import Path
from urllib.parse import urlparse

import cyclopts

from cyclopts import App
from rich import traceback
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from weasyprint import HTML

from . import i18n, templates
from .config import Config, Deploy
from .images import (
    ICON_TYPES,
    SOCIAL_PREVIEW_FILENAME,
    generate_favicons,
    generate_qr_code,
    generate_social_preview,
    optimize_avatar,
)
from .json_resume import JsonResume
from .jsonld import generate_jsonld
from .models import load_resume_for_language

traceback.install(show_locals=True, suppress=[sys.exec_prefix, sys.base_exec_prefix])

# Simple CSS minifier — strips comments, collapses whitespace
_CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_CSS_WHITESPACE_RE = re.compile(r"\s+")


def minify_css(css: str) -> str:
    """Strip comments and collapse whitespace from CSS."""
    css = _CSS_COMMENT_RE.sub("", css)
    css = _CSS_WHITESPACE_RE.sub(" ", css)
    # Remove spaces around punctuation
    for ch in "{}:;,>~+":
        css = css.replace(f" {ch} ", ch).replace(f" {ch}", ch).replace(f"{ch} ", ch)
    return css.strip()


ROOT = Path()
DATA = ROOT / "data"
STYLE = ROOT / "style"
IMAGES = ROOT / "images"
OUT = ROOT / "site"
app = App(
    config=[
        cyclopts.config.Env("", command=False),
        cyclopts.config.Toml(
            "pyproject.toml",
            root_keys=["tool", "resume"],
            use_commands_as_keys=False,
            allow_unknown=True,
        ),
    ],
)
app.command(i18n.app)
console = Console()


@app.command
def dev(port: int = 5000, *, config: Config = Config()):
    """
    Run a live-reload dev server
    """
    from livereload import Server

    deploy = Deploy(url=f"http://localhost:{port}")

    def reload():
        build(config=config, deploy=deploy)

    server = Server()

    server.watch(DATA, reload)
    server.watch(STYLE, reload)
    server.watch(IMAGES, reload)
    server.watch(f"{i18n.directory}/**/*.po", reload)
    server.watch(templates.directory, reload)
    server.watch("pyproject.toml", reload)

    reload()
    server.serve(port=port, root="site")


@app.command
def build(*, config: Config = Config(), deploy: Deploy = Deploy()):
    """Build the site using structured data models"""
    languages = config.languages or ["en"]
    default_lang = config.default_language or languages[0]

    with Progress(SpinnerColumn(), TextColumn("{task.description}")) as progress:
        task_i18n = progress.add_task("Compiling translations", total=None)
        i18n.compile_translations()
        progress.update(task_i18n, description="Translations compiled", completed=1)

        task_assets = progress.add_task("Copying assets", total=None)
        out_style_dir = OUT / "style"
        out_style_dir.mkdir(parents=True, exist_ok=True)
        for stylesheet in STYLE.glob("*.css"):
            out_file = out_style_dir / stylesheet.name
            out_file.write_bytes(stylesheet.read_bytes())

        # Read and minify web.css for inline embedding
        web_css_raw = (STYLE / "web.css").read_text(encoding="utf-8")
        inline_css = minify_css(web_css_raw)

        out_images_dir = OUT / "images"
        out_images_dir.mkdir(parents=True, exist_ok=True)
        for image in IMAGES.rglob("*.*"):
            out_file = out_images_dir / image.name
            out_file.write_bytes(image.read_bytes())
        progress.update(task_assets, description="Assets copied", completed=1)

        # Optimize avatar image: resize + generate WebP
        task_avatar = progress.add_task("Optimizing avatar image", total=None)
        avatar_png, avatar_webp = optimize_avatar(IMAGES / "me1.png", out_images_dir)
        progress.update(task_avatar, description="Avatar optimized", completed=1)

        task_favicons = progress.add_task("Generating favicons", total=None)
        generate_favicons(IMAGES / "logo.png", OUT / "images", root_dir=OUT)
        progress.update(task_favicons, description="Favicons generated", completed=1)

        if deploy.url:
            task_qr = progress.add_task("Generating QR code", total=None)
            generate_qr_code(
                OUT / "images" / "qrcode.png",
                deploy.url,
                logo=IMAGES / "logo-bg-white.png",
            )
            progress.update(task_qr, description="QR code generated", completed=1)

        env = templates.get_env(config)
        template = env.get_template("resume.html.j2")

        for lang in languages:
            i18n.set_locale(lang)
            task_lang = progress.add_task(f"Building {lang}", total=None)
            dataset = load_resume_for_language(DATA / lang)
            # Default language outputs to root, others to subdirectories
            out_lang_dir = OUT if lang == default_lang else OUT / lang
            out_lang_dir.mkdir(parents=True, exist_ok=True)
            # Generate JSON-LD structured data for SEO
            jsonld = generate_jsonld(dataset, lang, deploy, config)
            # Render index with structured data
            index_file = out_lang_dir / "index.html"
            index_file.write_text(
                template.render(
                    lang=lang,
                    data=dataset,
                    config=config,
                    deploy=deploy,
                    root=deploy.url,
                    favicons=ICON_TYPES,
                    jsonld=jsonld,
                    social_preview=SOCIAL_PREVIEW_FILENAME,
                    inline_css=inline_css,
                    avatar_png=avatar_png,
                    avatar_webp=avatar_webp,
                )
            )
            progress.update(task_lang, description=f"Built {lang}", completed=1)

            # Generate social preview image
            task_social = progress.add_task(f"Generating social preview for {lang}", total=None)
            avatar_file = OUT / (dataset.profile.avatar or "/images/me1.png").lstrip("/")
            generate_social_preview(
                out_lang_dir,
                full_name=dataset.profile.full_name,
                tagline=dataset.about.tagline or "",
                avatar_path=avatar_file,
                url=deploy.url or "",
            )
            progress.update(
                task_social, description=f"Social preview generated for {lang}", completed=1
            )

            # Generate PDF
            task_pdf = progress.add_task(f"Generating PDF for {lang}", total=None)
            pdf_html = template.render(
                lang=lang,
                data=dataset,
                config=config,
                deploy=deploy,
                root=".",
                pdf=True,
                favicons=ICON_TYPES,
            )
            pdf_path = out_lang_dir / dataset.profile.pdf_filename
            HTML(string=pdf_html, base_url=str(OUT)).write_pdf(str(pdf_path))
            progress.update(task_pdf, description=f"PDF generated: {pdf_path}", completed=1)

        # CNAME for custom domain (GitHub Pages)
        if deploy.url:
            hostname = urlparse(deploy.url).hostname
            if hostname and hostname != "localhost":
                cname_file = OUT / "CNAME"
                cname_file.write_text(hostname)

        # Generate sitemap.xml
        if deploy.url:
            task_sitemap = progress.add_task("Generating sitemap.xml", total=None)
            sitemap_lines = [
                '<?xml version="1.0" encoding="UTF-8"?>',
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
                '        xmlns:xhtml="http://www.w3.org/1999/xhtml">',
            ]
            for lang in languages:
                lang_path = "" if lang == default_lang else f"/{lang}"
                lang_url = f"{deploy.url}{lang_path}/"
                sitemap_lines.append("  <url>")
                sitemap_lines.append(f"    <loc>{lang_url}</loc>")
                for alt_lang in languages:
                    alt_path = "" if alt_lang == default_lang else f"/{alt_lang}"
                    alt_url = f"{deploy.url}{alt_path}/"
                    sitemap_lines.append(
                        f'    <xhtml:link rel="alternate" hreflang="{alt_lang}" href="{alt_url}"/>'
                    )
                sitemap_lines.append("  </url>")
            sitemap_lines.append("</urlset>")
            sitemap_file = OUT / "sitemap.xml"
            sitemap_file.write_text("\n".join(sitemap_lines), encoding="utf-8")
            progress.update(task_sitemap, description="sitemap.xml generated", completed=1)

            # Generate robots.txt
            task_robots = progress.add_task("Generating robots.txt", total=None)
            robots_content = f"User-agent: *\nAllow: /\n\nSitemap: {deploy.url}/sitemap.xml\n"
            robots_file = OUT / "robots.txt"
            robots_file.write_text(robots_content, encoding="utf-8")
            progress.update(task_robots, description="robots.txt generated", completed=1)


@app.command
def experience(name: str, config: Config = Config()):
    """Prompt for a new experience"""
    env = templates.get_env(config)
    try:
        template = env.get_template("experience.md.j2")
    except Exception as exc:
        console.print(f"[red]Template error:[/red] {exc}")
        return False

    data = {
        "company": Prompt.ask("Company"),
        "url": Prompt.ask("Company URL", default=""),
        "location": Prompt.ask("Location", default="Paris"),
        "start": Prompt.ask("Start Date (YYYY-MM)"),
        "end": Prompt.ask("End Date (YYYY-MM)"),
        "role": Prompt.ask("Role/Position"),
    }

    for lang in config.languages or ["en"]:
        i18n.set_locale(lang)
        details = Prompt.ask(f"Details ({lang})")
        file = DATA / lang / "experiences" / f"{name}.md"
        file.parent.mkdir(parents=True, exist_ok=True)
        md = template.render(experience=data, details=details)
        file.write_text(md, encoding="utf-8")


@app.command(name="json")
def as_json_resume(locale: str | None = None, output: str | None = None, config: Config = Config()):
    """Export resume(s) to JSON Resume format.

    Without --lang exports all languages as an array.
    With --lang exports a single resume object.
    """
    languages = config.languages or ["en"]

    target_langs = [locale] if locale else languages

    if locale and locale not in languages:
        console.print(f"[red]Language '{locale}' not in settings: {languages}[/red]")
        return False

    result_models = [
        JsonResume.from_data(load_resume_for_language(DATA / lang), lang) for lang in target_langs
    ]
    payload = (
        result_models[0].model_dump(by_alias=True, exclude_none=True, mode="json")
        if locale
        else [m.model_dump(by_alias=True, exclude_none=True, mode="json") for m in result_models]
    )
    json_text = json.dumps(payload, ensure_ascii=False, indent=2)
    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json_text, encoding="utf-8")
        console.print(f"[green]Wrote {out_path}[/green]")
    else:
        console.print_json(json_text)


@app.command
def pdf(
    locale: str = "en",
    output: str | None = None,
    config: Config = Config(),
    deploy: Deploy = Deploy(),
):
    """Generate PDF version of the resume (per language)."""
    env = templates.get_env(config)
    try:
        template = env.get_template("resume.html.j2")
    except Exception as exc:
        console.print(f"[red]Template error:[/red] {exc}")
        return False

    try:
        dataset = load_resume_for_language(DATA / locale)
    except Exception as exc:
        console.print(f"[red]Data loading failed:[/red] {exc}")
        return False

    i18n.set_locale(locale)
    html = template.render(
        lang=locale, data=dataset, config=config, deploy=deploy, root=".", pdf=True
    )
    out_lang_dir = OUT / locale
    out_lang_dir.mkdir(parents=True, exist_ok=True)
    pdf_name = output or dataset.profile.pdf_filename
    out_path = out_lang_dir / pdf_name

    with Progress(SpinnerColumn(), TextColumn("{task.description}")) as progress:
        task = progress.add_task(f"Rendering PDF for {locale}", total=None)
        try:
            HTML(string=html, base_url=config.root).write_pdf(
                str(out_path),
            )
        except Exception as exc:
            console.print(f"[red]PDF generation failed:[/red] {exc}")
            return False
        progress.update(task, description=f"PDF written: {out_path}", completed=1)


if __name__ == "__main__":
    app()
