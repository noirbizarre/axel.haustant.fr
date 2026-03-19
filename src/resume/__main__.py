import json
import sys

from pathlib import Path

import cyclopts

from cyclopts import App
from rich import traceback
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from weasyprint import HTML

from . import i18n, templates
from .config import Config, Deploy
from .json_resume import JsonResume
from .models import load_resume_for_language

traceback.install(show_locals=True, suppress=[sys.exec_prefix, sys.base_exec_prefix])


ROOT = Path()
DATA = ROOT / "data"
STYLE = ROOT / "style"
IMAGES = ROOT / "images"
OUT = ROOT / "site"
SETTINGS_FILE = DATA / "settings.yaml"

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
error_console = Console(stderr=True)


@app.command
def dev(port: int = 5000, *, config: Config = Config()):
    """
    Run a live-reload dev server
    """
    from livereload import Server

    def reload():
        build(config=config)
    server = Server()

    server.watch(DATA, reload)
    server.watch(STYLE, reload)
    server.watch(IMAGES, reload)
    server.watch(i18n.directory, reload)
    server.watch(templates.directory, reload)
    server.watch("pyproject.toml", reload)

    reload()
    server.serve(port=port, root="site")


@app.command
def build(*, config: Config = Config(), deploy: Deploy = Deploy()):
    """Build the site using structured data models"""
    print(f"{config=}")
    print(f"{deploy=}")

    languages = config.languages or ["en"]
    default_lang = config.default_language or languages[0]

    env = templates.get_env(config)
    template = env.get_template("resume.html.j2")

    with Progress(SpinnerColumn(), TextColumn("{task.description}")) as progress:
        task_assets = progress.add_task("Copying assets", total=None)
        out_dir = OUT / "style"
        out_dir.mkdir(parents=True, exist_ok=True)
        for stylesheet in STYLE.glob("*.css"):
            out_file = out_dir / stylesheet.name
            out_file.write_bytes(stylesheet.read_bytes())
        out_dir = OUT / "images"
        for image in IMAGES.rglob("*.*"):
            out_file = out_dir / image.name
            out_dir.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_bytes(image.read_bytes())
        progress.update(task_assets, description="Assets copied", completed=1)

        for lang in languages:
            i18n.set_locale(lang)
            task_lang = progress.add_task(f"Building {lang}", total=None)
            dataset = load_resume_for_language(DATA / lang)
            out_lang_dir = OUT / lang
            out_lang_dir.mkdir(parents=True, exist_ok=True)
            # Render index with structured data
            index_file = out_lang_dir / "index.html"
            index_file.write_text(
                template.render(
                    lang=lang, data=dataset, config=config, deploy=deploy, root=deploy.url
                )
            )
            progress.update(task_lang, description=f"Built {lang}", completed=1)

        # Root redirect to default language
        root_index = OUT / "index.html"
        redirect_template = env.get_template("redirect.html.j2")
        root_index.write_text(
            redirect_template.render(
                default_lang=default_lang, config=config, deploy=deploy, root=deploy.url
            )
        )


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
        "location": Prompt.ask("Location", default="Paris"),
        "start": Prompt.ask("Start Date (YYYY-MM)"),
        "end": Prompt.ask("End Date (YYYY-MM)"),
        "role": Prompt.ask("Role/Position"),
    }

    for lang in config.languages or ["en"]:
        i18n.set_locale(lang)
        details = Prompt.ask(f"Details ({lang})")
        file = DATA / lang / "experiences" / f"{name}.md"
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
    html = template.render(lang=locale, data=dataset, config=config, deploy=deploy, root=".", pdf=True)
    OUT.mkdir(parents=True, exist_ok=True)
    pdf_name = output or f"resume-{locale}.pdf"
    out_path = OUT / pdf_name

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
