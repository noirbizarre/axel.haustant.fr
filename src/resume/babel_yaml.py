"""Custom Babel extractor for YAML skill data files.

Extracts translatable ``name`` fields from skill group definitions
so they appear in the ``.pot`` catalog alongside template strings.
"""

from __future__ import annotations

from typing import IO, Any

import yaml


def extract_skills(
    fileobj: IO[bytes],
    keywords: list[str],
    comment_tags: list[str],
    options: dict[str, Any],
) -> list[tuple[int, str, str, list[str]]]:
    """Extract translatable strings from a skills YAML file.

    The file is expected to be a list of skill groups::

        - name: Programming
          skills:
          - name: Python
            level: 95

    Both group names and individual skill names are extracted.
    """
    data = yaml.safe_load(fileobj)
    if not isinstance(data, list):
        return []

    messages: list[tuple[int, str, str, list[str]]] = []
    for group in data:
        if not isinstance(group, dict):
            continue
        group_name = group.get("name")
        if group_name:
            messages.append((1, "_", group_name, []))
        for skill in group.get("skills", []):
            if isinstance(skill, dict) and skill.get("name"):
                messages.append((1, "_", skill["name"], []))
    return messages
