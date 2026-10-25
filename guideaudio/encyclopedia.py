"""The structure an encyclopedia keeps: every entry walks through the same sections.

An encyclopedia ("encyclopedia_*.txt") is a guide whose chapters are mostly
entries, one per item of its topic: one bacterium, one drug, one lab test.
Each section of an entry is a paragraph that opens with a short label and a
colon ("Einordnung: ...", "Die Tests: ..."), and the last one is always the
summary ("Kurz gesagt: ..."). Hearing the same labels in the same order is
what lets a listener jump into any entry and know where they are.

The sections differ per topic, so they are not configured: the first entry
sets them, and every later entry is held to it. A chapter is an entry when
its first paragraph opens with a label; overview, part and summary chapters
start with plain prose and are left alone. Problems are warnings, never
errors: an uneven entry still synthesizes into a correct track.
"""

import re
from dataclasses import dataclass, field

from guideaudio.reader import Block, Heading, Paragraph

SUMMARY_LABELS = {"de": "Kurz gesagt", "en": "In short"}

# One to four words, the first capitalized, then a colon: "Mikroskop und Kultur: ...".
_LABEL = re.compile(r"^([A-ZÄÖÜ][\w-]*(?: [\w-]+){0,3}):\s")


@dataclass
class EncyclopediaReport:
    sections: list[str] = field(default_factory=list)
    entries: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class _Chapter:
    heading: Heading
    paragraphs: list[Paragraph] = field(default_factory=list)


def section_label(paragraph: Paragraph) -> str | None:
    match = _LABEL.match(paragraph.sentences[0])
    return match.group(1) if match else None


def _chapters(blocks: list[Block]) -> list[_Chapter]:
    chapters: list[_Chapter] = []
    for block in blocks:
        if isinstance(block, Heading):
            chapters.append(_Chapter(block))
        elif chapters:
            chapters[-1].paragraphs.append(block)
    return chapters


def _sequence(labels: list[str]) -> str:
    return " → ".join(labels) if labels else "none"


def check_entries(blocks: list[Block], language: str) -> EncyclopediaReport:
    report = EncyclopediaReport()
    summary = SUMMARY_LABELS[language]
    for chapter in _chapters(blocks):
        if not chapter.paragraphs or section_label(chapter.paragraphs[0]) in (None, summary):
            continue
        labels = [label for p in chapter.paragraphs if (label := section_label(p))]
        where = f"line {chapter.heading.line_number}: entry {chapter.heading.spoken_title!r}"
        report.entries.append(chapter.heading.spoken_title)
        if not report.sections:
            report.sections = labels
            if labels[-1] != summary:
                report.warnings.append(f"{where} does not end with a {summary!r} section")
            continue
        if labels != report.sections:
            report.warnings.append(
                f"{where} has the sections {_sequence(labels)}; "
                f"the first entry set {_sequence(report.sections)}"
            )
    if not report.entries:
        report.warnings.append(
            "no entries found; start each entry's first paragraph with a section label and a colon"
        )
    return report
