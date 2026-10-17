import pytest

from guideaudio.assemble import Silence
from guideaudio.config import TextPauseConfig
from guideaudio.reader import (
    Heading,
    LoadError,
    Paragraph,
    guide_title,
    limit_sentences,
    load_guide,
    split_sentences,
    split_text,
    text_marks,
    text_timeline,
)
from guideaudio.synth import ClipSpec

PAUSES = TextPauseConfig(after_sentence=0.6, after_paragraph=1.5)

GUIDE_EN = """Foundations for the lab.

# Atomic structure

Everything is made of atoms. An atom has a nucleus.

The nucleus is tiny.

# The mole

A mole is a counting unit.
"""

GUIDE_DE = """Grundlagen für das Labor.

# Der Atombau — Atomic structure

Alles besteht aus Atomen.
"""


def sentences(blocks):
    return [b.sentences for b in blocks if isinstance(b, Paragraph)]


def test_splits_sentences_on_terminal_punctuation():
    assert split_sentences("One. Two! Three? Four…") == ["One.", "Two!", "Three?", "Four…"]


def test_period_before_a_lowercase_word_does_not_split():
    assert split_sentences("It costs approx. ten euros. Done.") == ["It costs approx. ten euros.", "Done."]


def test_blank_lines_separate_paragraphs_and_line_wraps_are_joined():
    blocks = split_text("First line\nstill first. Second.\n\n  \nNew paragraph.")

    assert sentences(blocks) == [["First line still first.", "Second."], ["New paragraph."]]


def test_english_heading_has_no_subtitle():
    heading = split_text(GUIDE_EN)[1]

    assert heading == Heading("Atomic structure", None, 3)
    assert heading.title == "Atomic structure"
    assert heading.spoken == "Atomic structure."


def test_german_heading_speaks_only_the_german_part():
    heading = split_text(GUIDE_DE)[1]

    assert heading.title == "Der Atombau — Atomic structure"
    assert heading.spoken == "Der Atombau."


def test_paragraphs_remember_their_first_line():
    blocks = split_text(GUIDE_EN)

    assert [b.line_number for b in blocks if isinstance(b, Paragraph)] == [1, 5, 7, 11]


def test_guide_title_is_the_first_line_without_its_period():
    assert guide_title(split_text(GUIDE_EN)) == "Foundations for the lab"


def test_guide_title_is_none_when_the_text_starts_with_a_heading():
    assert guide_title(split_text("# Atomic structure\n\nText.")) is None


@pytest.mark.parametrize("language", ["en", "de"])
def test_timeline_uses_the_guide_language_for_every_clip(language):
    timeline = text_timeline(split_text(GUIDE_EN), language, "M1", PAUSES)

    clips = [item for item in timeline if isinstance(item, ClipSpec)]
    assert clips and all(clip.language == language and clip.voice == "M1" for clip in clips)


def test_timeline_pauses_between_sentences_and_longer_after_paragraphs_and_headings():
    timeline = text_timeline(split_text(GUIDE_EN), "en", "M1", PAUSES)

    texts_and_pauses = [
        item.text if isinstance(item, ClipSpec) else item.seconds for item in timeline
    ]
    assert texts_and_pauses[:8] == [
        "Foundations for the lab.", 1.5,
        "Atomic structure.", 1.5,
        "Everything is made of atoms.", 0.6,
        "An atom has a nucleus.", 1.5,
    ]


def test_marks_point_at_the_spoken_headings():
    blocks = split_text(GUIDE_EN)
    timeline = text_timeline(blocks, "en", "M1", PAUSES)

    marks = text_marks(blocks)

    assert marks == {2: "Atomic structure", 10: "The mole"}
    for index in marks:
        assert timeline[index].text == f"{marks[index]}."
        assert isinstance(timeline[index + 1], Silence)


def test_limit_counts_a_heading_as_one_sentence():
    limited = limit_sentences(split_text(GUIDE_EN), 3)

    assert [type(b).__name__ for b in limited] == ["Paragraph", "Heading", "Paragraph"]
    assert limited[2].sentences == ["Everything is made of atoms."]


def test_load_guide_reads_utf8_with_bom(tmp_path):
    path = tmp_path / "guide_de.txt"
    path.write_bytes("﻿".encode() + GUIDE_DE.encode("utf-8"))

    assert guide_title(load_guide(path)) == "Grundlagen für das Labor"


def test_load_guide_rejects_an_empty_file(tmp_path):
    path = tmp_path / "empty.txt"
    path.write_text("  \n\n", encoding="utf-8")

    with pytest.raises(LoadError, match="contains no text"):
        load_guide(path)


def test_load_guide_rejects_non_utf8(tmp_path):
    path = tmp_path / "latin1.txt"
    path.write_bytes("Größe.".encode("latin-1"))

    with pytest.raises(LoadError, match="not valid UTF-8"):
        load_guide(path)
