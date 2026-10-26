"""Lay out a guide's text as a Markdown reference book (`--markdown`).

Made for encyclopedias but works for any guide: a title page, a table of
contents grouped by part, an overview table per part, every entry with its
section labels as icon headings, the practice and summary paragraphs as
GitHub alert boxes (also shown as boxes by VS Code and Obsidian), and an A–Z
register of the entries. The text stays as written, except the spellings
made for the voice ("M R S A", "I g M") go back to their written form.
"""

import re
from dataclasses import dataclass, field

from guideaudio.encyclopedia import SUMMARY_LABELS, section_label
from guideaudio.reader import Block, Heading, Paragraph, guide_title

PRACTICE = {"de": "Warum ist das im Labor wichtig?", "en": "Why does this matter in the lab?"}
PART_PREFIX = {"de": "Teil ", "en": "Part "}
SUMMARY_TITLE = {"de": "Zusammenfassung", "en": "Summary"}
WORDS = {
    "de": {"contents": "Inhalt", "entry": "Steckbrief", "entries": "Steckbriefe", "parts": "Teile",
           "chapters": "Kapitel", "glance": "Auf einen Blick", "register": "Register A–Z", "group": "Gruppe",
           "number": "Nr.", "layout": "So ist jeder Steckbrief aufgebaut:", "back": "↑ Inhalt"},
    "en": {"contents": "Contents", "entry": "Entry", "entries": "entries", "parts": "parts",
           "chapters": "chapters", "glance": "At a glance", "register": "Index A–Z", "group": "Group",
           "number": "No.", "layout": "Every entry is built like this:", "back": "↑ Contents"},
}
# Icons for section labels that come up often; any other label gets the plain marker.
SECTION_ICONS = {
    "Einordnung": "🧭", "Overview": "🧭", "Mikroskop und Kultur": "🔬", "Die Tests": "🧪",
    "Die Krankheiten": "🩺", "Resistenz und Therapie": "💊", "Wirkung": "⚙️", "Anwendung": "🩹",
    "Nebenwirkungen": "⚠️", "Im Labor": "🧫", "Bildung und Aufgabe": "⚙️", "Probe und Messung": "🧪",
    "Die Werte": "📊", "Fehlerquellen": "⚠️", "Entstehung": "🌱", "Im Ausstrich": "🔬",
}
# Entry icon by a word in the file name; other subjects get the plain bookmark.
ENTRY_ICONS = {"bakterien": "🦠", "viren": "🦠", "pilze": "🦠", "parasiten": "🦠", "chemie": "🧪",
               "haematologie": "🩸"}
# Spoken numbers of the CD markers, longest first so "dreiunddreißig" is not read as "drei".
CD_NUMBERS = {"dreiunddreißig": 33, "dreiundzwanzig": 23, "vierunddreißig": 34, "neunzehn": 19, "dreizehn": 13,
              "zwanzig": 20, "drei": 3, "vier": 4, "fünf": 5, "acht": 8}
PART_ICONS = ["🟣", "🔵", "🔴", "🟠", "🟡", "⚪", "🛡️", "🧫", "⚡", "🟤", "⚫", "🟢"]


def readable(text: str) -> str:
    """Undo the spellings made for the voice: "M R S A" -> "MRSA", "I g M" -> "IgM", "H B s" -> "HBs"."""
    text = re.sub(r"\bI g ([MGAE])\b", r"Ig\1", text).replace("Maldi-Tof", "MALDI-TOF").replace("C T-Wert", "Ct-Wert")
    for spoken, written in (("H b A eins c", "HbA1c"), ("h C G", "hCG"), ("e G F R", "eGFR"),
                            ("p C O zwei", "pCO2"), ("p O zwei", "pO2"), ("N T-pro B N P", "NT-proBNP"),
                            ("J A K zwei", "JAK2"), ("H b A zwei", "HbA2")):
        text = text.replace(spoken, written)
    text = re.sub(r"\bH b(?: ([AFS])\b)?", r"Hb\1", text)
    text = re.sub(rf"\bC D ({'|'.join(CD_NUMBERS)})\b", lambda m: f"CD{CD_NUMBERS[m.group(1)]}", text)
    return re.sub(r"\b[A-Z](?: [A-Z])+(?: [a-z]\b)?\b", lambda m: m.group().replace(" ", ""), text)


def anchor(text: str) -> str:
    return re.sub(r"[^a-z0-9äöüß]+", "-", text.lower()).strip("-")


@dataclass
class _Chapter:
    heading: Heading
    paragraphs: list[str] = field(default_factory=list)
    number: int | None = None  # set for entries


@dataclass
class _Part:
    heading: Heading
    intro: list[str]
    chapters: list[_Chapter] = field(default_factory=list)


def _chapters(blocks: list[Block]) -> list[_Chapter]:
    chapters: list[_Chapter] = []
    for block in blocks:
        if isinstance(block, Heading):
            chapters.append(_Chapter(block))
        elif chapters:
            chapters[-1].paragraphs.append(" ".join(block.sentences))
    return chapters


def _label(paragraph: str) -> str | None:
    return section_label(Paragraph([paragraph]))


def _split_label(paragraph: str, label: str) -> str:
    return paragraph[len(label) + 1:].strip()


def _part_name(part: _Part | None) -> str:
    return part.heading.spoken_title.split(": ", 1)[-1] if part else ""


def _body(chapter: _Chapter, language: str) -> str:
    practice, summary = PRACTICE[language], SUMMARY_LABELS[language]
    out = []
    for paragraph in chapter.paragraphs:
        label = _label(paragraph)
        if paragraph.startswith(practice):
            out.append(f"> [!TIP]\n> **🏥 {practice}** {readable(paragraph[len(practice):].strip())}\n")
        elif label == summary:
            out.append(f"> [!NOTE]\n> **📌 {summary}:** {readable(_split_label(paragraph, label))}\n")
        elif label and chapter.number is not None:
            icon = SECTION_ICONS.get(label, "▸")
            out.append(f"#### {icon} {label}\n\n{readable(_split_label(paragraph, label))}\n")
        else:
            out.append(readable(paragraph) + "\n")
    return "\n".join(out)


def _glance(chapter: _Chapter, language: str) -> str:
    summary = SUMMARY_LABELS[language]
    for paragraph in chapter.paragraphs:
        if _label(paragraph) == summary:
            return readable(re.split(r"(?<=[.!?])\s", _split_label(paragraph, summary))[0])
    return ""


def _heading_block(heading: Heading, level: str, icon: str) -> str:
    subtitle = ""
    if heading.subtitle and heading.subtitle != heading.spoken_title:
        subtitle = f"<sub>{readable(heading.subtitle)}</sub>\n"
    return f'<a id="{anchor(heading.spoken_title)}"></a>\n\n{level} {icon} {readable(heading.spoken_title)}\n{subtitle}'


def render_markdown(blocks: list[Block], language: str, source_name: str) -> str:
    words, summary = WORDS[language], SUMMARY_LABELS[language]
    entry_icon = next((icon for word, icon in ENTRY_ICONS.items() if word in source_name.lower()), "🔖")
    front: list[_Chapter] = []
    parts: list[_Part] = []
    for chapter in _chapters(blocks):
        if chapter.heading.spoken_title.startswith(PART_PREFIX[language]):
            parts.append(_Part(chapter.heading, chapter.paragraphs))
        elif parts:
            parts[-1].chapters.append(chapter)
        else:
            front.append(chapter)

    entries: list[tuple[_Chapter, _Part | None]] = []
    sections: list[str] = []
    placed = [(c, None) for c in front] + [(c, p) for p in parts for c in p.chapters]
    for chapter, part in placed:
        if chapter.paragraphs and _label(chapter.paragraphs[0]) not in (None, summary):
            chapter.number = len(entries) + 1
            entries.append((chapter, part))
            if not sections:
                sections = [label for p in chapter.paragraphs if (label := _label(p)) and label != summary]

    title = (guide_title(blocks) or source_name).rstrip(".")
    chapter_count = len(front) + sum(1 + len(p.chapters) for p in parts)
    md = [
        f'<div align="center">\n\n# 📚 {readable(title)}\n\n'
        f"`{len(entries)} {words['entries']}` · `{len(parts)} {words['parts']}` · "
        f"`{chapter_count} {words['chapters']}`\n\n</div>\n"
    ]
    if sections:
        steps = [f"{SECTION_ICONS.get(s, '▸')} {s}" for s in sections] + [f"🏥 {PRACTICE[language]}", f"📌 {summary}"]
        md.append(f"> [!NOTE]\n> **{words['layout']}** {' → '.join(steps)}\n")

    def is_summary(chapter: _Chapter) -> bool:
        return chapter.heading.spoken_title.startswith(SUMMARY_TITLE[language])

    def toc_line(chapter: _Chapter, plain: str) -> str:
        if chapter.number is not None:
            marker = f"`{chapter.number:02d}` {entry_icon} "
        else:
            marker = "📝 " if is_summary(chapter) else plain
        return f"- {marker}[{readable(chapter.heading.spoken_title)}](#{anchor(chapter.heading.spoken_title)})"

    def chapter_md(chapter: _Chapter, part: _Part | None, icon: str, plain_icon: str) -> str:
        if chapter.number is not None:
            group = f" · **{icon} {_part_name(part)}**" if part else ""
            return (_heading_block(chapter.heading, "##", entry_icon)
                    + f"\n> `{words['entry']} {chapter.number:02d}`{group}\n\n" + _body(chapter, language))
        if is_summary(chapter):
            quoted = "\n>\n".join(f"> {readable(p)}" for p in chapter.paragraphs)
            return _heading_block(chapter.heading, "###", "📝") + f"\n{quoted}\n"
        return _heading_block(chapter.heading, "##", plain_icon) + "\n" + _body(chapter, language)

    md.append(f'<a id="contents"></a>\n\n## 🗂️ {words["contents"]}\n')
    md += [toc_line(c, "") for c in front]
    for i, part in enumerate(parts):
        icon = PART_ICONS[i % len(PART_ICONS)]
        md.append(f"\n**{icon} [{part.heading.spoken_title}](#{anchor(part.heading.spoken_title)})**\n")
        md += [toc_line(c, "📖 ") for c in part.chapters]
    if entries:
        md.append(f"\n- 🔤 [{words['register']}](#register)")
    md.append("")

    back = f'<p align="right"><a href="#contents">{words["back"]}</a></p>\n'
    for chapter in front:
        md.append("---\n\n" + chapter_md(chapter, None, "", "🗺️"))
    for i, part in enumerate(parts):
        icon = PART_ICONS[i % len(PART_ICONS)]
        md.append("---\n\n" + _heading_block(part.heading, "#", icon) + "\n"
                  + _body(_Chapter(part.heading, part.intro), language))
        part_entries = [c for c in part.chapters if c.number is not None]
        if part_entries:
            md.append(f"| {words['number']} | {words['entry']} | {words['glance']} |\n|:--:|---|---|")
            md += [f"| `{c.number:02d}` | [**{readable(c.heading.spoken_title)}**](#{anchor(c.heading.spoken_title)}) "
                   f"| {_glance(c, language)} |" for c in part_entries]
            md.append("")
        for chapter in part.chapters:
            md.append(chapter_md(chapter, part, icon, "📖"))
            md.append(back)

    if entries:
        md.append(f'---\n\n<a id="register"></a>\n\n## 🔤 {words["register"]}\n')
        md.append(f"| {words['entry']} | {words['group']} | {words['number']} |\n|---|---|:--:|")
        ordered = sorted(entries, key=lambda e: re.sub(r"^(die|der|das|the) ", "", e[0].heading.spoken_title.lower()))
        md += [f"| [{readable(c.heading.spoken_title)}](#{anchor(c.heading.spoken_title)}) | {_part_name(p)} "
               f"| `{c.number:02d}` |" for c, p in ordered]
        md.append("")
    md.append(f"<sub>{source_name}</sub>\n")
    return "\n".join(md)
