"""Generate JSON-LD structured data from resume content for SEO."""

from __future__ import annotations

import json

from typing import Any

from .config import Config, Deploy
from .models import ResumeData, School


def generate_jsonld(data: ResumeData, lang: str, deploy: Deploy, config: Config) -> str:
    """Build a schema.org JSON-LD ``@graph`` from loaded resume data.

    Returns a JSON string ready to embed in a ``<script type="application/ld+json">`` tag.
    """
    base_url = (deploy.url or "").rstrip("/")
    graph: list[dict[str, Any]] = [
        _person(data, base_url),
        _website(data, base_url, config),
        _profile_page(data, lang, base_url, config.default_language),
    ]
    payload: dict[str, Any] = {
        "@context": "https://schema.org",
        "@graph": graph,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Internal builders
# ---------------------------------------------------------------------------


def _person(data: ResumeData, base_url: str) -> dict[str, Any]:
    profile = data.profile
    about = data.about

    person: dict[str, Any] = {
        "@type": "Person",
        "@id": f"{base_url}/#person",
        "name": profile.full_name,
        "givenName": profile.first_name,
        "familyName": profile.last_name,
        "url": base_url or None,
    }

    if about.tagline:
        person["jobTitle"] = about.tagline

    if about.content:
        person["description"] = about.content

    if profile.email:
        person["email"] = f"mailto:{profile.email}"

    if profile.phone and profile.phone.number:
        person["telephone"] = profile.phone.number

    if profile.avatar:
        person["image"] = f"{base_url}{profile.avatar}" if base_url else profile.avatar

    # sameAs — social profiles and websites
    same_as: list[str] = []
    for sn in profile.social:
        same_as.append(str(sn.link))
    for site in profile.websites:
        same_as.append(str(site.link))
    if same_as:
        person["sameAs"] = same_as

    # knowsAbout — aggregated from skill groups
    knows_about: list[str] = []
    for group in data.skill_groups:
        for skill in group.skills:
            knows_about.append(skill.name)
    if knows_about:
        person["knowsAbout"] = knows_about

    # knowsLanguage
    if about.languages:
        person["knowsLanguage"] = [
            {"@type": "Language", "name": lang_entry.name, "alternateName": lang_entry.level}
            for lang_entry in about.languages
        ]

    # alumniOf — education
    if data.schools:
        person["alumniOf"] = [_educational_org(school) for school in data.schools]

    # worksFor — current employer (first experience without an end date)
    current = next((exp for exp in data.experiences if exp.end is None), None)
    if current and current.company:
        person["worksFor"] = {
            "@type": "Organization",
            "name": current.company,
        }

    return {k: v for k, v in person.items() if v is not None}


def _educational_org(school: School) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "@type": "EducationalOrganization",
        "name": school.name,
    }
    if school.location:
        entry["address"] = {
            "@type": "PostalAddress",
            "addressLocality": school.location,
        }
    return entry


def _website(data: ResumeData, base_url: str, config: Config) -> dict[str, Any]:
    site: dict[str, Any] = {
        "@type": "WebSite",
        "@id": f"{base_url}/#website",
        "name": data.profile.full_name,
        "url": base_url,
    }
    if config.languages:
        site["inLanguage"] = config.languages
    return site


def _profile_page(data: ResumeData, lang: str, base_url: str, default_lang: str) -> dict[str, Any]:
    lang_path = "" if lang == default_lang else f"/{lang}"
    page_url = f"{base_url}{lang_path}/"
    page: dict[str, Any] = {
        "@type": "ProfilePage",
        "@id": f"{page_url}#webpage",
        "url": page_url,
        "name": data.profile.full_name,
        "isPartOf": {"@id": f"{base_url}/#website"},
        "mainEntity": {"@id": f"{base_url}/#person"},
        "about": {"@id": f"{base_url}/#person"},
        "inLanguage": lang,
    }
    if data.about.tagline:
        page["name"] = f"{data.profile.full_name} \u2014 {data.about.tagline}"
    return page
