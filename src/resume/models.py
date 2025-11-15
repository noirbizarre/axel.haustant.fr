from __future__ import annotations
from datetime import date
from typing import List, Optional, Tuple
from pathlib import Path
import re
import yaml
from pydantic import BaseModel, Field, HttpUrl, ConfigDict, validator
from markdown_it import MarkdownIt

FRONT_MATTER_SPLIT = re.compile(r"^---\s*$", re.MULTILINE)


def parse_front_matter(markdown: str) -> Tuple[dict, str]:
    """
    Split a markdown string into (front_matter_dict, body_markdown).
    Returns ({}, original_markdown) if no front matter found.
    """
    parts = FRONT_MATTER_SPLIT.split(markdown, maxsplit=2)
    if len(parts) >= 3:
        _, raw_meta, body = parts[0], parts[1], parts[2]
        meta = yaml.safe_load(raw_meta) or {}
        return meta, body.lstrip()
    return {}, markdown


def parse_year_or_year_month(value: str) -> date:
    """
    Accept 'YYYY' or 'YYYY-MM' and return a date at first day of month.
    """
    if not value:
        raise ValueError("Empty date value")
    if re.fullmatch(r"\d{4}-\d{2}", value):
        year, month = map(int, value.split("-"))
        return date(year, month, 1)
    if re.fullmatch(r"\d{4}", value):
        return date(int(value), 1, 1)
    raise ValueError(f"Unsupported date format: {value}")


class Experience(BaseModel):
    model_config = ConfigDict(extra="ignore")
    company: Optional[str] = None
    where: Optional[str] = None
    role: Optional[str] = None
    start: Optional[date] = None
    end: Optional[date] = None
    content: Optional[str] = None  # Raw markdown body
    html: Optional[str] = None  # Rendered HTML

    @validator("start", "end", pre=True)
    def _parse_dates(cls, v):
        if v in (None, ""):
            return None
        return parse_year_or_year_month(str(v))

    @property
    def duration_months(self) -> Optional[int]:
        if self.start and self.end:
            return (
                (self.end.year - self.start.year) * 12
                + (self.end.month - self.start.month)
                + 1
            )
        return None


class School(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    section: Optional[str] = None
    degree: Optional[str] = None
    where: Optional[str] = None
    when: Optional[int] = None  # Single year marker
    from_year: Optional[int] = Field(None, alias="from")
    to_year: Optional[int] = Field(None, alias="to")


class Conference(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    event: Optional[str] = None
    when: Optional[int] = None  # Year


class Expertise(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    lines: List[str] = Field(default_factory=list)


class Skill(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    level: int = Field(ge=0, le=100)


class SkillGroup(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    skills: List[Skill] = Field(default_factory=list)


class SkillRated(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    rate: int = Field(ge=0, le=100)


class Project(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    url: Optional[HttpUrl] = None
    description: Optional[str] = None


class Website(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    link: HttpUrl


class SocialNetwork(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    icon: Optional[str] = None
    link: HttpUrl
    display: Optional[str] = None


class Phone(BaseModel):
    model_config = ConfigDict(extra="ignore")
    display: Optional[str] = None
    number: Optional[str] = None


class Language(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    level: Optional[str] = None


class Me(BaseModel):
    model_config = ConfigDict(extra="ignore")
    first_name: str
    last_name: str
    tagline: Optional[str] = None
    avatar: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[Phone] = None
    websites: List[Website] = Field(default_factory=list)
    social: List[SocialNetwork] = Field(default_factory=list)
    languages: List[Language] = Field(default_factory=list)
    skills: List[SkillRated] = Field(default_factory=list)
    content: Optional[str] = None  # Raw markdown biography
    html: Optional[str] = None  # Rendered HTML biography

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class ResumeData(BaseModel):
    """Aggregated structure for an entire language dataset."""

    model_config = ConfigDict(extra="ignore")
    me: Me
    experiences: List[Experience] = Field(default_factory=list)
    schools: List[School] = Field(default_factory=list)
    conferences: List[Conference] = Field(default_factory=list)
    expertise: List[Expertise] = Field(default_factory=list)
    skill_groups: List[SkillGroup] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    labels: dict[str, str] = Field(default_factory=dict)


class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    url: Optional[HttpUrl] = None
    languages: List[str] = Field(default_factory=list)
    google_analytics: str | None = None

    @property
    def default_language(self) -> Optional[str]:
        return self.languages[0] if self.languages else None


# ---------------------------
# Loading helpers
# ---------------------------


def load_yaml_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8") or ""
    data = yaml.safe_load(raw) or []
    return data if isinstance(data, list) else []


_MD = MarkdownIt()


def load_experiences(dir_path: Path) -> List[Experience]:
    experiences = []
    for md_file in sorted(dir_path.glob("*.md")):
        meta, body = parse_front_matter(md_file.read_text(encoding="utf-8"))
        html = _MD.render(body) if body else None
        experiences.append(Experience(**meta, content=body or None, html=html))
    return experiences


def load_projects(md_file: Path) -> Tuple[List[Project], str]:
    meta, body = parse_front_matter(md_file.read_text(encoding="utf-8"))
    opensource = meta.get("opensource", []) or []
    return [Project(**p) for p in opensource], body.strip()


def load_me(md_file: Path) -> Me:
    meta, body = parse_front_matter(md_file.read_text(encoding="utf-8"))
    body_clean = body.strip() if body else None
    html = _MD.render(body_clean) if body_clean else None
    return Me(**meta, content=body_clean or None, html=html)


def load_resume_for_language(lang_dir: Path) -> ResumeData:
    me = load_me(lang_dir / "me.md")
    experiences = load_experiences(lang_dir / "experiences")
    schools = [School(**d) for d in load_yaml_list(lang_dir / "education.yml")]
    conferences = [
        Conference(**d) for d in load_yaml_list(lang_dir / "conferences.yml")
    ]
    expertise_items = [
        Expertise(**d) for d in load_yaml_list(lang_dir / "expertise.yml")
    ]
    skill_group_dicts = load_yaml_list(lang_dir / "skills.yml")
    skill_groups = [
        SkillGroup(name=sg["name"], skills=[Skill(**s) for s in sg.get("skills", [])])
        for sg in skill_group_dicts
    ]
    projects_list, _projects_body = load_projects(lang_dir / "projects.md")
    labels_path = lang_dir / "labels.yaml"
    labels = {}
    if labels_path.exists():
        labels_raw = labels_path.read_text(encoding="utf-8")
        labels = yaml.safe_load(labels_raw) or {}
    data = ResumeData(
        me=me,
        experiences=experiences,
        schools=schools,
        conferences=conferences,
        expertise=expertise_items,
        skill_groups=skill_groups,
        projects=projects_list,
        labels=labels,
    )
    return data


def load_all(data_root: Path) -> dict[str, ResumeData]:
    """
    Load datasets for each language directory (e.g. 'en', 'fr').
    """
    result = {}
    for lang_dir in data_root.iterdir():
        if lang_dir.is_dir():
            try:
                result[lang_dir.name] = load_resume_for_language(lang_dir)
            except Exception as exc:
                print(f"Failed loading {lang_dir.name}: {exc}")
    return result
