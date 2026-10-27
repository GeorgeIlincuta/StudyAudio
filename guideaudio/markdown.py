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
    "Wirkweise": "⚙️", "Hintergrund": "💡", "Probe und Methode": "🧪", "Der Befund": "📋",
    "Grundlage": "💡", "Praxis": "🛠️", "Im Präparat": "🔬", "Das Ergebnis": "📈",
}
# Entry icon by a word in the file name; other subjects get the plain bookmark.
ENTRY_ICONS = {"bakterien": "🦠", "viren": "🦠", "pilze": "🦠", "parasiten": "🦠", "chemie": "🧪",
               "haematologie": "🩸", "haemostase": "🩹", "immunologie": "🛡️",
               "histologie": "🔬", "molekular": "🧬", "urin": "💧",
               "mikrobiologie": "🧫"}
# Spoken numbers of the CD markers, longest first so "dreiunddreißig" is not read as "drei".
CD_NUMBERS = {"achtunddreißig": 38, "dreiunddreißig": 33, "dreiundzwanzig": 23, "vierunddreißig": 34, "neunzehn": 19, "dreizehn": 13,
              "zwanzig": 20, "drei": 3, "vier": 4, "fünf": 5, "acht": 8}
# Spoken numbers of the clotting factors as Roman numerals, longest first so "dreizehn" is not read as "drei".
FACTOR_NUMERALS = {"dreizehn": "XIII", "zwölf": "XII", "zehn": "X", "neun": "IX", "acht": "VIII", "sieben": "VII",
                   "fünf": "V", "drei": "III", "zwei": "II", "vier": "IV", "elf": "XI", "eins": "I"}
# Spoken numbers of the Pap groups and of the T, N, M, G and R stages.
PAP_NUMERALS = {"null": "0", "eins": "I", "zwei": "II", "drei": "III", "vier": "IV", "fünf": "V"}
STAGE_NUMBERS = {"null": 0, "eins": 1, "zwei": 2, "drei": 3, "vier": 4}
PART_ICONS = ["🟣", "🔵", "🔴", "🟠", "🟡", "⚪", "🛡️", "🧫", "⚡", "🟤", "⚫", "🟢"]


def readable(text: str) -> str:
    """Undo the spellings made for the voice: "M R S A" -> "MRSA", "I g M" -> "IgM", "H B s" -> "HBs"."""
    text = re.sub(r"\bI g ([MGAED])\b", r"Ig\1", text).replace("Maldi-Tof", "MALDI-TOF").replace("C T-Wert", "Ct-Wert")
    for spoken, written in (("B C R-A B L eins", "BCR-ABL1"), ("S A R S-CoV-zwei", "SARS-CoV-2"),
                            ("sechzehn S r R N A", "16S rRNA"), ("m R N A", "mRNA"), ("t R N A", "tRNA"),
                            ("r R N A", "rRNA"), ("c f D N A", "cfDNA"), ("c t D N A", "ctDNA"), ("c D N A", "cDNA"),
                            ("q P C R", "qPCR"), ("C zweihundertzweiundachtzig Y", "C282Y"),
                            ("G zwanzigtausendzweihundertzehn A", "G20210A"), ("V sechshundertsiebzehn F", "V617F"),
                            ("C Y P zwei D sechs", "CYP2D6"), ("M R drei", "MR3"), ("M R vier", "MR4"),
                            ("m e c A", "mecA"), ("v a n A", "vanA"), ("R Nasen", "RNasen"), ("R Nase", "RNase"),
                            ("R fünfhundertsechs Q", "R506Q"), ("H dreiundsechzig D", "H63D"),
                            ("T siebenhundertneunzig M", "T790M"), ("B siebenundfünfzig null eins", "B*57:01"),
                            ("H b A eins c", "HbA1c"), ("h C G", "hCG"), ("e G F R", "eGFR"),
                            ("p C O zwei", "pCO2"), ("p O zwei", "pO2"), ("N T-pro B N P", "NT-proBNP"),
                            ("J A K zwei", "JAK2"), ("H b A zwei", "HbA2"), ("a P T T", "aPTT"), ("v W F", "vWF"),
                            ("Anti-X a", "Anti-Xa"), ("t P A", "tPA"), ("A D A M T S dreizehn", "ADAMTS13"),
                            ("P F vier", "PF4"), ("P A I eins", "PAI-1"), ("d R V V T", "dRVVT"),
                            ("A B null", "AB0"), ("d s D N A", "dsDNA"), ("C eins", "C1"), ("C drei d", "C3d"),
                            ("C drei", "C3"), ("C vier", "C4"), ("H E p-zwei", "HEp-2"), ("P R drei", "PR3"),
                            ("Scl-siebzig", "Scl-70"), ("D Q zwei", "DQ2"), ("D Q acht", "DQ8"),
                            ("S m", "Sm"), ("B siebenundzwanzig", "B27"),
                            ("F y a", "Fya"), ("F y b", "Fyb"), ("J k a", "Jka"), ("J k b", "Jkb"),
                            ("A eins", "A1"), ("A zwei", "A2"), ("H E R zwei", "HER2"),
                            ("K i siebenundsechzig", "Ki-67"), ("C K sieben", "CK7"), ("C K zwanzig", "CK20"),
                            ("P D L eins", "PD-L1"), ("S hundert", "S100"), ("T T F eins", "TTF-1"),
                            ("C I N eins", "CIN1"), ("C I N zwei", "CIN2"), ("C I N drei", "CIN3"),
                            ("S G L T-zwei", "SGLT2"), ("Rili-B Ä K", "Rili-BÄK"), ("Teil B eins", "Teil B1"),
                            ("Teil B zwei", "Teil B2"), ("Protein vierzehn drei drei", "Protein 14-3-3"),
                            ("drei M R G N", "3MRGN"), ("vier M R G N", "4MRGN")):
        text = re.sub(rf"\b{re.escape(spoken)}\b", written, text)
    text = re.sub(r"\b(Blutgruppen?|Gruppe) null\b", r"\1 0", text)
    text = re.sub(r"\bH b\b(?: ([AFS])\b)?", r"Hb\1", text)
    numeral = "|".join(FACTOR_NUMERALS)
    factor = rf"(?:{numeral})\b(?: a\b)?"
    text = re.sub(rf"\bFaktor(?:s|en)?[- ]{factor}(?:(?:, | und | bis ){factor})*",
                  lambda m: re.sub(rf"({numeral})\b( a\b)?",
                                   lambda n: FACTOR_NUMERALS[n.group(1)] + ("a" if n.group(2) else ""), m.group()),
                  text)
    text = re.sub(rf"\bC D ({'|'.join(CD_NUMBERS)})\b", lambda m: f"CD{CD_NUMBERS[m.group(1)]}", text)
    text = re.sub(rf"\bPap ({'|'.join(PAP_NUMERALS)})\b(?: D (eins|zwei)\b| ([ab])\b)?",
                  lambda m: f"Pap {PAP_NUMERALS[m.group(1)]}"
                            + (f"D{STAGE_NUMBERS[m.group(2)]}" if m.group(2) else m.group(3) or ""), text)
    stage = "|".join(STAGE_NUMBERS)
    # N and M only after a T stage, so the influenza subtype "H eins N eins" stays as spoken.
    text = re.sub(rf"\b(p )?T ({stage})\b(?: ([abc])\b)?(?: N ({stage})\b)?(?: M ({stage})\b)?",
                  lambda m: f"{'p' if m.group(1) else ''}T{STAGE_NUMBERS[m.group(2)]}{m.group(3) or ''}"
                            + (f" N{STAGE_NUMBERS[m.group(4)]}" if m.group(4) else "")
                            + (f" M{STAGE_NUMBERS[m.group(5)]}" if m.group(5) else ""), text)
    text = re.sub(rf"\b([GR]) ({stage})\b", lambda m: f"{m.group(1)}{STAGE_NUMBERS[m.group(2)]}", text)
    text = re.sub(rf"\b([NM]) ({stage})\b",
                  lambda m: m.group() if re.search(r"\b[A-Z] \w+ $", m.string[:m.start()])
                  else f"{m.group(1)}{STAGE_NUMBERS[m.group(2)]}", text)
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
