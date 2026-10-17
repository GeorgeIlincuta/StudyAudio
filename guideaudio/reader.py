"""Read a guide: plain text in, one clip per sentence out.

Synthesizing sentence by sentence rather than the whole text at once keeps
every engine input short, and gives the clip cache its properties: an
interrupted run resumes, and editing one sentence re-synthesizes one clip.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from guideaudio.assemble import Silence, TimelineItem
from guideaudio.config import TextPauseConfig
from guideaudio.synth import ClipSpec


class LoadError(Exception):
    """Raised when the input file cannot be used. Carries every problem found."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("\n".join(problems))


# Space + em dash + space, the same separator the Hörplayer splits section titles on.
TITLE_SEPARATOR = " — "


@dataclass(frozen=True)
class Heading:
    """A chapter heading line.

    German guides write "# Der Atombau — Atomic structure": only the German
    part is spoken, and the player shows the English part underneath.
    English guides write "# Atomic structure" with no second part.
    """

    spoken_title: str
    subtitle: str | None
    line_number: int = 0

    @property
    def title(self) -> str:
        return f"{self.spoken_title}{TITLE_SEPARATOR}{self.subtitle}" if self.subtitle else self.spoken_title

    @property
    def spoken(self) -> str:
        return self.spoken_title if self.spoken_title[-1] in ".!?…" else f"{self.spoken_title}."


@dataclass(frozen=True)
class Paragraph:
    sentences: list[str]
    line_number: int = 0


Block = Paragraph | Heading
Marks = dict[int, str]  # timeline index -> chapter title

# Terminal punctuation, then any closing quotes or brackets, then whitespace.
_CANDIDATE_END = re.compile(r"[.!?…]+[\"'“”»«’)\]]*\s+")


def _is_sentence_end(paragraph: str, match: re.Match) -> bool:
    """Reject the two commonest false ends.

    A period followed by a lowercase word is almost always an abbreviation
    ("ca. zehn", "approx. ten"), and a period straight after a digit is an
    ordinal ("am 3. Mai"). Getting one of these wrong only costs a short
    pause mid-sentence, so the rules stay deliberately small.
    """
    next_char = paragraph[match.end()]
    if next_char.islower():
        return False
    punctuation = match.group().rstrip()
    after_digit = match.start() > 0 and paragraph[match.start() - 1].isdigit()
    return not (punctuation == "." and after_digit)


def split_sentences(paragraph: str) -> list[str]:
    sentences: list[str] = []
    start = 0
    for match in _CANDIDATE_END.finditer(paragraph):
        if _is_sentence_end(paragraph, match):
            sentences.append(paragraph[start:match.end()].strip())
            start = match.end()
    tail = paragraph[start:].strip()
    if tail:
        sentences.append(tail)
    return sentences


def _parse_heading(line: str, line_number: int) -> Heading | None:
    text = " ".join(line.lstrip()[1:].split())
    if not text:
        return None
    spoken, _, subtitle = text.partition(TITLE_SEPARATOR.strip())
    return Heading(spoken.strip(), subtitle.strip() or None, line_number)


def split_text(text: str) -> list[Block]:
    """Paragraphs at blank lines, sentences within them, line wraps joined.

    A line starting with "#" is a chapter heading and always stands alone,
    even without blank lines around it.
    """
    blocks: list[Block] = []
    pending: list[str] = []
    pending_start = 0

    def flush() -> None:
        joined = " ".join(" ".join(pending).split())
        if joined:
            blocks.append(Paragraph(split_sentences(joined), pending_start))
        pending.clear()

    for number, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("#"):
            flush()
            heading = _parse_heading(line, number)
            if heading is not None:
                blocks.append(heading)
        elif not line.strip():
            flush()
        else:
            if not pending:
                pending_start = number
            pending.append(line)
    flush()
    return blocks


def read_text(path: Path) -> str:
    path = Path(path)
    try:
        return path.read_text(encoding="utf-8-sig")
    except OSError as error:
        raise LoadError([f"cannot read {path}: {error}"]) from error
    except UnicodeDecodeError as error:
        raise LoadError([f"{path} is not valid UTF-8"]) from error


def load_guide(path: Path) -> list[Block]:
    blocks = split_text(read_text(path))
    if not blocks:
        raise LoadError([f"{path} contains no text"])
    return blocks


def limit_sentences(blocks: list[Block], limit: int) -> list[Block]:
    """The first `limit` sentences, keeping their paragraph grouping."""
    kept: list[Block] = []
    remaining = limit
    for block in blocks:
        if remaining <= 0:
            break
        if isinstance(block, Heading):
            kept.append(block)
            remaining -= 1
            continue
        kept.append(Paragraph(block.sentences[:remaining], block.line_number))
        remaining -= len(kept[-1].sentences)
    return kept


def guide_title(blocks: list[Block]) -> str | None:
    """The guide's first sentence without its final punctuation."""
    for block in blocks:
        if isinstance(block, Heading):
            return None
        return block.sentences[0].rstrip(".!?… ")
    return None


def text_timeline(
    blocks: list[Block], language: str, voice: str, pauses: TextPauseConfig
) -> list[TimelineItem]:
    timeline: list[TimelineItem] = []
    for block in blocks:
        if isinstance(block, Heading):
            timeline.append(ClipSpec(block.spoken, language, voice))
            timeline.append(Silence(pauses.after_paragraph))
            continue
        for index, sentence in enumerate(block.sentences):
            is_last = index == len(block.sentences) - 1
            timeline.append(ClipSpec(sentence, language, voice))
            timeline.append(Silence(pauses.after_paragraph if is_last else pauses.after_sentence))
    return timeline


def text_marks(blocks: list[Block]) -> Marks:
    """Where each heading's spoken clip sits in `text_timeline`, keyed by timeline index."""
    marks: Marks = {}
    index = 0
    for block in blocks:
        if isinstance(block, Heading):
            marks[index] = block.title
            index += 2
        else:
            index += 2 * len(block.sentences)
    return marks
