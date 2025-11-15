from pathlib import Path
import sys
from cyclopts import App
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown_it import MarkdownIt
import yaml
from rich import traceback

traceback.install(show_locals=True, suppress=[sys.exec_prefix, sys.base_exec_prefix])


DATA = Path() / "data"
STYLE = Path() / "style"
IMAGES = Path() / "images"
OUT = Path() / "site"

app = App()


@app.command
def dev(port: int = 5000):
    """
    Run a live-reload dev server
    """
    from livereload import Server

    # settings = get_settings()
    build()
    server = Server()

    server.watch(DATA, build)
    server.watch(STYLE, build)
    server.watch(IMAGES, build)

    server.serve(port=port, root="site")


@app.command
def build():
    """Build the site using structured data models"""
    from .models import load_resume_for_language, Settings
    from rich.progress import Progress, SpinnerColumn, TextColumn

    settings_raw = (DATA / "settings.yaml").read_text(encoding="utf-8")
    settings = Settings(**(yaml.safe_load(settings_raw) or {}))
    languages = settings.languages or ["en"]
    default_lang = settings.default_language or languages[0]

    md = MarkdownIt()
    env = Environment(loader=FileSystemLoader("data"), autoescape=select_autoescape())
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
            task_lang = progress.add_task(f"Building {lang}", total=None)
            dataset = load_resume_for_language(DATA / lang)
            out_lang_dir = OUT / lang
            out_lang_dir.mkdir(parents=True, exist_ok=True)
            # Render experiences as standalone pages
            for exp_file in (DATA / lang / "experiences").glob("*.md"):
                content = exp_file.read_text(encoding="utf-8")
                html = md.render(content)
                out_file = out_lang_dir / f"{exp_file.stem}.html"
                out_file.write_text(html, encoding="utf-8")
            # Render index with structured data
            index_file = out_lang_dir / "index.html"
            index_file.write_text(template.render(lang=lang, data=dataset))
            progress.update(task_lang, description=f"Built {lang}", completed=1)

        # Root redirect to default language
        root_index = OUT / "index.html"
        root_index.write_text(
            f'<html><head><meta http-equiv="refresh" content="0; url=/{default_lang}/"><title>Redirect</title></head><body>Redirecting to {default_lang}...</body></html>',
            encoding="utf-8",
        )


@app.command
def experience(name: str, lang: str = "en"):
    """Render a single experience by name and language"""
    md = MarkdownIt()
    file = DATA / lang / "experiences" / f"{name}.md"
    content = file.read_text(encoding="utf-8")
    html = md.render(content)
    print(html)


@app.command
def json(lang: str | None = None, output: str | None = None):
    """Export resume(s) to JSON Resume format.

    Without --lang exports all languages as an array.
    With --lang exports a single resume object.
    """
    import json as _json
    from .models import load_resume_for_language, Settings
    from rich.console import Console

    console = Console()
    settings_raw = (DATA / "settings.yaml").read_text(encoding="utf-8")
    settings = Settings(**(yaml.safe_load(settings_raw) or {}))
    languages = settings.languages or ["en"]

    target_langs = [lang] if lang else languages

    def serialize_url(val):
        return str(val) if val else None

    def build_resume(lang_code: str):
        dataset = load_resume_for_language(DATA / lang_code)
        me = dataset.me
        basics = {
            "name": me.full_name,
            "label": me.tagline,
            "email": me.email,
            "phone": me.phone.display if me.phone and me.phone.display else None,
            "website": serialize_url(next((w.link for w in me.websites), None)),
            "summary": me.content,
            "profiles": [
                {
                    "network": sn.name,
                    "username": sn.display or sn.name,
                    "url": serialize_url(sn.link),
                }
                for sn in me.social
            ],
        }
        basics = {k: v for k, v in basics.items() if v}
        work = []
        for exp in dataset.experiences:
            highlights = [
                line.strip("- ")
                for line in (exp.content.split("\n") if exp.content else [])
                if line.startswith("-")
            ]
            w = {
                "name": exp.company,
                "position": exp.role,
                "location": exp.where,
                "startDate": exp.start.isoformat() if exp.start else None,
                "endDate": exp.end.isoformat() if exp.end else None,
                "highlights": highlights,
            }
            w = {k: v for k, v in w.items() if v not in (None, [], "")}
            work.append(w)
        education = []
        for school in dataset.schools:
            e = {
                "institution": school.name,
                "area": school.section,
                "studyType": school.degree,
                "startDate": str(school.from_year) if school.from_year else None,
                "endDate": str(school.to_year) if school.to_year else None,
            }
            e = {k: v for k, v in e.items() if v}
            education.append(e)
        skills = []
        for skill in me.skills:
            skills.append(
                {"name": skill.name, "level": str(skill.rate), "keywords": []}
            )
        for group in dataset.skill_groups:
            skills.append(
                {"name": group.name, "keywords": [s.name for s in group.skills]}
            )
        projects = []
        for p in dataset.projects:
            proj = {
                "name": p.name,
                "description": p.description,
                "url": serialize_url(p.url),
            }
            proj = {k: v for k, v in proj.items() if v}
            projects.append(proj)
        languages_section = []
        for l in me.languages:
            entry = {"language": l.name}
            if l.level:
                entry["fluency"] = l.level
            languages_section.append(entry)
        return {
            "language": lang_code,
            "basics": basics,
            "work": work,
            "education": education,
            "skills": skills,
            "projects": projects,
            "languages": languages_section,
            "$schema": "https://raw.githubusercontent.com/jsonresume/resume-schema/master/schema.json",
        }

    if lang and lang not in languages:
        console.print(f"[red]Language '{lang}' not in settings: {languages}[/red]")
        return

    result = [build_resume(l) for l in target_langs]
    payload = result[0] if lang else result
    json_text = _json.dumps(payload, ensure_ascii=False, indent=2)
    if output:
        out_path = Path(output)
        out_path.write_text(json_text, encoding="utf-8")
        console.print(f"[green]Wrote {out_path}[/green]")
    else:
        print(json_text)


@app.command
def pdf(lang: str = "en", output: str | None = None):
    """Generate PDF version of the resume (per language)."""
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn

    console = Console()
    try:
        from weasyprint import HTML, CSS  # type: ignore
    except ImportError:
        console.print(
            "[red]WeasyPrint not installed. Please add 'weasyprint' to dependencies and reinstall.[/red]"
        )
        return
    from .models import load_resume_for_language

    env = Environment(loader=FileSystemLoader("data"), autoescape=select_autoescape())
    try:
        template = env.get_template("resume.pdf.html.j2")
    except Exception as exc:
        console.print(f"[red]Template error:[/red] {exc}")
        return

    try:
        dataset = load_resume_for_language(DATA / lang)
    except Exception as exc:
        console.print(f"[red]Data loading failed:[/red] {exc}")
        return

    html = template.render(data=dataset, lang=lang)
    OUT.mkdir(parents=True, exist_ok=True)
    pdf_name = output or f"resume-{lang}.pdf"
    out_path = OUT / pdf_name
    css_files = (
        [CSS(filename=str(STYLE / "pdf.css"))] if (STYLE / "pdf.css").exists() else []
    )

    with Progress(SpinnerColumn(), TextColumn("{task.description}")) as progress:
        task = progress.add_task(f"Rendering PDF for {lang}", total=None)
        try:
            HTML(string=html, base_url=str(Path.cwd())).write_pdf(
                str(out_path), stylesheets=css_files
            )
        except Exception as exc:
            console.print(f"[red]PDF generation failed:[/red] {exc}")
            return
        progress.update(task, description=f"PDF written: {out_path}", completed=1)


if __name__ == "__main__":
    app()
