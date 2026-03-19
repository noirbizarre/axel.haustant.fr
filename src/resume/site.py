import sys

from rich import traceback
from rich.progress import Progress, SpinnerColumn, TextColumn

from . import i18n, templates
from .config import Config, Deploy
from .models import load_resume_for_language

traceback.install(show_locals=True, suppress=[sys.exec_prefix, sys.base_exec_prefix])



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
