import re

from datetime import date
from pathlib import Path

import yaml

from markdown_it import MarkdownIt
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

FRONT_MATTER_SPLIT = re.compile(r"^---\s*$", re.MULTILINE)


def parse_front_matter(markdown: str) -> tuple[dict, str]:
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
    company: str | None = None
    location: str | None = None
    role: str | None = None
    start: date | None = None
    end: date | None = None
    content: str | None = None  # Raw markdown body
    html: str | None = None  # Rendered HTML

    @field_validator("start", "end", mode="before")
    @classmethod
    def _parse_dates(cls, v):
        if v in (None, ""):
            return None
        return parse_year_or_year_month(str(v))

    @property
    def duration_months(self) -> int | None:
        if self.start and self.end:
            return (self.end.year - self.start.year) * 12 + (self.end.month - self.start.month) + 1
        return None

    @classmethod
    def from_files(cls, dir_path: Path) -> list[Experience]:
        experiences = []
        for md_file in sorted(dir_path.glob("*.md")):
            meta, body = parse_front_matter(md_file.read_text(encoding="utf-8"))
            html = _MD.render(body) if body else None
            experiences.append(cls(**meta, content=body or None, html=html))
        return sorted(experiences, key=lambda e: e.start, reverse=True)


class School(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    section: str | None = None
    degree: str | None = None
    location: str | None = None
    when: int | None = None  # Single year marker
    from_year: int | None = Field(None, alias="from")
    to_year: int | None = Field(None, alias="to")

    @classmethod
    def from_file(cls, yaml_file: Path) -> list[School]:
        return [cls(**d) for d in load_yaml_list(yaml_file)]


class Conference(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    event: str | None = None
    when: int | None = None  # Year

    @classmethod
    def from_file(cls, yaml_file: Path) -> list[Conference]:
        return [cls(**d) for d in load_yaml_list(yaml_file)]


class Expertise(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    lines: list[str] = Field(default_factory=list)

    @classmethod
    def from_file(cls, yaml_file: Path) -> list[Expertise]:
        return [cls(**d) for d in load_yaml_list(yaml_file)]


class Skill(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    level: int = Field(ge=0, le=100)


class SkillGroup(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    skills: list[Skill] = Field(default_factory=list)

    @classmethod
    def from_data(cls, lang_dir: Path) -> list[SkillGroup]:
        skill_group_dicts = load_yaml_list(lang_dir / "skills.yml")
        skill_groups = [
            SkillGroup(name=sg["name"], skills=[Skill(**s) for s in sg.get("skills", [])])
            for sg in skill_group_dicts
        ]
        return skill_groups


class SkillRated(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    rate: int = Field(ge=0, le=100)


class Project(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    url: HttpUrl | None = None
    description: str | None = None

    @classmethod
    def from_file(cls, md_file: Path) -> tuple[list[Project], str]:
        meta, body = parse_front_matter(md_file.read_text(encoding="utf-8"))
        opensource = meta.get("opensource", []) or []
        return [cls(**p) for p in opensource], body.strip()


class Website(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    link: HttpUrl


class SocialNetwork(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    icon: str | None = None
    link: HttpUrl
    display: str | None = None


class Phone(BaseModel):
    model_config = ConfigDict(extra="ignore")
    display: str | None = None
    number: str | None = None


class Language(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    level: str | None = None


class Profile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    first_name: str
    last_name: str
    avatar: str | None = None
    email: str | None = None
    phone: Phone | None = None
    websites: list[Website] = Field(default_factory=list)
    social: list[SocialNetwork] = Field(default_factory=list)
    skills: list[SkillRated] = Field(default_factory=list)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def pdf_filename(self) -> str:
        first = self.first_name.lower().replace(" ", "-")
        last = self.last_name.lower().replace(" ", "-")
        return f"{first}.{last}.pdf"

    @classmethod
    def from_file(cls, yaml_file: Path) -> Profile:
        data = yaml_file.read_text(encoding="utf-8")
        return cls(**yaml.safe_load(data))


class About(BaseModel):
    model_config = ConfigDict(extra="ignore")
    tagline: str | None = None
    languages: list[Language] = Field(default_factory=list)
    skills: list[SkillRated] = Field(default_factory=list)
    content: str | None = None  # Raw markdown biography
    html: str | None = None  # Rendered HTML biography

    @classmethod
    def from_file(cls, md_file: Path) -> About:
        meta, body = parse_front_matter(md_file.read_text(encoding="utf-8"))
        body_clean = body.strip() if body else None
        html = _MD.render(body_clean) if body_clean else None
        return cls(**meta, content=body_clean or None, html=html)


class ResumeData(BaseModel):
    """Aggregated structure for an entire language dataset."""

    model_config = ConfigDict(extra="ignore")
    about: About
    experiences: list[Experience] = Field(default_factory=list)
    schools: list[School] = Field(default_factory=list)
    conferences: list[Conference] = Field(default_factory=list)
    expertise: list[Expertise] = Field(default_factory=list)
    skill_groups: list[SkillGroup] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    profile: Profile
    labels: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_data(cls, lang_dir: Path) -> ResumeData:
        labels_path = lang_dir / "labels.yaml"
        labels = {}
        if labels_path.exists():
            labels_raw = labels_path.read_text(encoding="utf-8")
            labels = yaml.safe_load(labels_raw) or {}
        data = cls(
            about=About.from_file(lang_dir / "about.md"),
            experiences=Experience.from_files(lang_dir / "experiences"),
            schools=School.from_file(lang_dir / "education.yml"),
            conferences=Conference.from_file(lang_dir / "conferences.yml"),
            expertise=Expertise.from_file(lang_dir / "expertise.yml"),
            skill_groups=SkillGroup.from_data(lang_dir),
            projects=Project.from_file(lang_dir / "projects.md")[0],
            profile=Profile.from_file(lang_dir.parent / "profile.yaml"),
            labels=labels,
        )
        return data


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


def load_resume_for_language(lang_dir: Path) -> ResumeData:
    skill_group_dicts = load_yaml_list(lang_dir / "skills.yml")
    skill_groups = [
        SkillGroup(name=sg["name"], skills=[Skill(**s) for s in sg.get("skills", [])])
        for sg in skill_group_dicts
    ]
    labels_path = lang_dir / "labels.yaml"
    labels = {}
    if labels_path.exists():
        labels_raw = labels_path.read_text(encoding="utf-8")
        labels = yaml.safe_load(labels_raw) or {}
    data = ResumeData(
        about=About.from_file(lang_dir / "about.md"),
        experiences=Experience.from_files(lang_dir / "experiences"),
        schools=School.from_file(lang_dir / "education.yml"),
        conferences=Conference.from_file(lang_dir / "conferences.yml"),
        expertise=Expertise.from_file(lang_dir / "expertise.yml"),
        skill_groups=skill_groups,
        projects=Project.from_file(lang_dir / "projects.md")[0],
        profile=Profile.from_file(lang_dir.parent / "profile.yaml"),
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
