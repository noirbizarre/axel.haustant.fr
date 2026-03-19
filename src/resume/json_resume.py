from datetime import date

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from resume.models import Experience, Project, ResumeData, School
from resume.models import Language as SrcLanguage


class SocialProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    network: str
    username: str | None = None
    url: HttpUrl | None = None

    @classmethod
    def from_profile(cls, src) -> SocialProfile:
        return cls(network=src.name, username=src.display or src.name, url=src.link)


class Basics(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    label: str | None = None
    email: str | None = None
    phone: str | None = None
    website: HttpUrl | None = None
    summary: str | None = None
    profiles: list[SocialProfile] = Field(default_factory=list)

    @classmethod
    def from_data(cls, data: ResumeData) -> Basics:
        profile = data.profile
        return cls(
            name=profile.full_name,
            label=data.about.tagline,
            email=profile.email,
            phone=profile.phone.display if profile.phone and profile.phone.display else None,
            website=next((w.link for w in profile.websites), None) if profile.websites else None,
            summary=data.about.content,
            profiles=[SocialProfile.from_profile(sn) for sn in profile.social],
        )


class WorkEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    position: str | None = None
    location: str | None = None
    startDate: date | None = None
    endDate: date | None = None
    highlights: list[str] = Field(default_factory=list)

    @classmethod
    def from_experience(cls, exp: Experience) -> WorkEntry:
        if exp.content:
            lines = exp.content.split("\n")
            highlights = [
                line.strip("- ").strip() for line in lines if line.lstrip().startswith("-")
            ]
        else:
            highlights = []
        return cls(
            name=exp.company,
            position=exp.role,
            location=exp.location,
            startDate=exp.start,
            endDate=exp.end,
            highlights=highlights,
        )

    @classmethod
    def list_from_data(cls, data: ResumeData) -> list[WorkEntry]:
        return [cls.from_experience(exp) for exp in data.experiences]


class EducationEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    institution: str | None = None
    area: str | None = None
    studyType: str | None = None
    startDate: int | None = None
    endDate: int | None = None

    @classmethod
    def from_school(cls, school: School) -> EducationEntry:
        return cls(
            institution=school.name,
            area=school.section,
            studyType=school.degree,
            startDate=school.from_year,
            endDate=school.to_year,
        )

    @classmethod
    def list_from_data(cls, data: ResumeData) -> list[EducationEntry]:
        return [cls.from_school(school) for school in data.schools]


class SkillEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    level: str | None = None
    keywords: list[str] = Field(default_factory=list)

    @classmethod
    def list_from_data(cls, data: ResumeData) -> list[SkillEntry]:
        skills: list[SkillEntry] = []
        for skill in data.about.skills:
            skills.append(
                cls(
                    name=skill.name,
                    level=str(skill.rate),
                    keywords=[],
                )
            )
        for group in data.skill_groups:
            skills.append(
                cls(
                    name=group.name,
                    keywords=[s.name for s in group.skills],
                )
            )
        return skills


class ProjectEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    description: str | None = None
    url: HttpUrl | None = None

    @classmethod
    def from_project(cls, project: Project) -> ProjectEntry:
        return cls(name=project.name, description=project.description, url=project.url)

    @classmethod
    def list_from_data(cls, data: ResumeData) -> list[ProjectEntry]:
        return [cls.from_project(p) for p in data.projects]


class LanguageEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    language: str
    fluency: str | None = None

    @classmethod
    def from_language(cls, lang: SrcLanguage) -> LanguageEntry:
        return cls(language=lang.name, fluency=lang.level)

    @classmethod
    def list_from_data(cls, data: ResumeData) -> list[LanguageEntry]:
        return [cls.from_language(l) for l in data.about.languages]


class JsonResume(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    language: str
    basics: Basics
    work: list[WorkEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    skills: list[SkillEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    languages: list[LanguageEntry] = Field(default_factory=list)
    schema_: str = Field(
        "https://raw.githubusercontent.com/jsonresume/resume-schema/master/schema.json",
        alias="$schema",
    )

    @classmethod
    def from_data(cls, dataset: ResumeData, lang_code: str) -> JsonResume:
        return cls(
            language=lang_code,
            basics=Basics.from_data(dataset),
            work=WorkEntry.list_from_data(dataset),
            education=EducationEntry.list_from_data(dataset),
            skills=SkillEntry.list_from_data(dataset),
            projects=ProjectEntry.list_from_data(dataset),
            languages=LanguageEntry.list_from_data(dataset),
        )
