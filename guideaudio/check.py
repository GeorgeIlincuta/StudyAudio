"""The text rules a guide must follow before it is worth synthesizing.

Supertonic rejects a sentence with an unknown character, and the sentence
splitter turns an abbreviation into a false pause. Both only show up deep
into a long build, so every rule is checked up front, and every problem in
the file is reported in one run rather than one per run.

Errors stop a build. Warnings are things worth a look (a long sentence, a
short chapter) that still produce a correct track.
"""

import re
from dataclasses import dataclass, field

from guideaudio.config import CheckConfig
from guideaudio.reader import TITLE_SEPARATOR, Heading, Paragraph, split_text

# Tested against the real model in GermanAudio; anything else fails synthesis.
ALLOWED_SYMBOLS = set(" ,.:;-–—…!?'\"“”‘’»«€%&#")
GERMAN_LETTERS = set("äöüÄÖÜß")
# Only plain digits; subscripts like the 2 in a water formula are unsupported characters.
_DIGITS = set("0123456789")

_ABBREVIATION = re.compile(
    r"\b(e\.g|i\.e|etc|vs|approx|Mr|Mrs|Dr|Prof|z\. ?B|bzw|ca|usw|Nr|d\. ?h|evtl|ggf|inkl)\."
)
_SENTENCE_END = re.compile(r"[.!?…][\"'“”»«’)\]]*$")


@dataclass(frozen=True)
class ChapterStats:
    title: str
    words: int


@dataclass
class CheckReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    chapters: list[ChapterStats] = field(default_factory=list)
    words: int = 0
    sentences: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def _character_problems(line: str, language: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    digits = sorted({c for c in line if c in _DIGITS})
    if digits:
        errors.append(f"digits {''.join(digits)}; write numbers as words")
    unsupported = sorted({
        c for c in line
        if c not in _DIGITS and not c.isspace()
        and not (c.isalpha() and (c.isascii() or c in GERMAN_LETTERS))
        and c not in ALLOWED_SYMBOLS
    })
    if unsupported:
        errors.append(f"unsupported characters {' '.join(unsupported)}")
    if language == "en":
        german = sorted({c for c in line if c in GERMAN_LETTERS})
        if german:
            warnings.append(f"German letters {' '.join(german)} in an English guide")
    return errors, warnings


def _heading_problems(heading: Heading, language: str, config: CheckConfig) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if heading.spoken_title.endswith("."):
        errors.append("heading ends with a period")
    if len(heading.spoken_title.split()) > config.max_heading_words:
        errors.append(f"heading has more than {config.max_heading_words} words: {heading.spoken_title}")
    if language == "en" and heading.subtitle:
        warnings.append(f"English guides use headings without a translation: {heading.title}")
    if language == "de" and not heading.subtitle:
        warnings.append(f"heading has no English translation after{TITLE_SEPARATOR.rstrip()}: {heading.title}")
    return errors, warnings


def check_text(text: str, language: str, config: CheckConfig = CheckConfig()) -> CheckReport:
    report = CheckReport()
    lines = text.splitlines()

    first = next((l for l in lines if l.strip()), "")
    if first.lstrip().startswith("#"):
        report.errors.append("the first line must be the guide's title, not a heading")
    elif first and not _SENTENCE_END.search(first.strip()):
        report.errors.append("the title on the first line must end with a period")

    for number, line in enumerate(lines, start=1):
        errors, warnings = _character_problems(line, language)
        report.errors += [f"line {number}: {e}" for e in errors]
        report.warnings += [f"line {number}: {w}" for w in warnings]
        for match in _ABBREVIATION.finditer(line):
            report.errors.append(f"line {number}: abbreviation {match.group()!r}; write it out")
        if "..." in line:
            report.errors.append(f"line {number}: three dots; use … and only at the end of a sentence")
        if line.lstrip().startswith("#") and number > 1 and lines[number - 2].strip():
            report.warnings.append(f"line {number}: no empty line before the heading")

    current: str | None = None
    words = 0
    for block in split_text(text):
        if isinstance(block, Heading):
            errors, warnings = _heading_problems(block, language, config)
            report.errors += [f"line {block.line_number}: {e}" for e in errors]
            report.warnings += [f"line {block.line_number}: {w}" for w in warnings]
            if current is not None:
                report.chapters.append(ChapterStats(current, words))
            current, words = block.title, 0
            continue
        assert isinstance(block, Paragraph)
        if not _SENTENCE_END.search(block.sentences[-1]):
            report.errors.append(
                f"line {block.line_number}: paragraph does not end with . ! ? or …"
            )
        for sentence in block.sentences:
            count = len(sentence.split())
            if count > config.long_sentence_words:
                report.warnings.append(
                    f"line {block.line_number}: long sentence ({count} words): {sentence[:60]}…"
                )
        report.sentences += len(block.sentences)
        block_words = sum(len(s.split()) for s in block.sentences)
        report.words += block_words
        if current is not None:
            words += block_words
    if current is not None:
        report.chapters.append(ChapterStats(current, words))

    if not report.chapters:
        report.warnings.append("no chapter headings; the player will show the guide as one block")
    return report
