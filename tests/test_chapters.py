from mutagen.id3 import ID3

from guideaudio.chapters import Chapter, Line, item_starts, line_positions, mark_positions, write_tags
from guideaudio.config import TextPauseConfig
from guideaudio.reader import split_text, text_lines, text_marks, text_timeline
from guideaudio.synth import ClipSpec, synthesize_clips

RATE = 44100
GUIDE = "Grundlagen. Zweiter Satz.\n\n# Der Atombau — Atomic structure\n\nErster Satz. Noch einer.\n\nNeuer Absatz.\n"


def test_text_lines_mark_paragraphs_and_headings():
    blocks = split_text(GUIDE)
    lines = text_lines(blocks)
    assert list(lines.values()) == [
        "Grundlagen.", "Zweiter Satz.", "# Der Atombau — Atomic structure", "\nErster Satz.", "Noch einer.",
        "\nNeuer Absatz.",
    ]
    timeline = text_timeline(blocks, "de", "M1", TextPauseConfig())
    assert all(isinstance(timeline[i], ClipSpec) for i in lines)


def test_line_positions_match_the_chapter_starts(tmp_path, fake_engine):
    blocks = split_text(GUIDE)
    timeline = text_timeline(blocks, "de", "M1", TextPauseConfig())
    synthesize_clips([i for i in timeline if isinstance(i, ClipSpec)], fake_engine, tmp_path)
    starts, total = item_starts(timeline, tmp_path, fake_engine.engine_id, RATE)
    chapters, total2 = mark_positions(timeline, text_marks(blocks), tmp_path, fake_engine.engine_id, RATE)
    lines = line_positions(starts, text_lines(blocks))
    assert total == total2
    heading = next(line for line in lines if line.text.startswith("# "))
    assert heading.start_sample == chapters[0].start_sample


def test_english_guides_get_an_english_sylt(tmp_path):
    path = tmp_path / "t.mp3"
    path.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 413)
    write_tags(path, "T", [Chapter("Atoms", 0)], 44100, RATE, "en", lines=[Line("# Atoms", 0), Line("One.", 22050)])
    sylt = ID3(path).getall("SYLT")[0]
    assert sylt.lang == "eng" and sylt.text == [("# Atoms", 0), ("One.", 500)]


def test_write_tags_without_lines_removes_an_old_sylt(tmp_path):
    path = tmp_path / "t.mp3"
    path.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 413)
    write_tags(path, "T", [], 44100, RATE, lines=[Line("Satz.", 0)])
    write_tags(path, "T", [], 44100, RATE)
    assert ID3(path).getall("SYLT") == []


def test_write_tags_writes_exactly_one_genre(tmp_path):
    path = tmp_path / "t.mp3"
    path.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 413)
    write_tags(path, "T", [], 44100, RATE, genre="Leitfaden")
    write_tags(path, "T", [], 44100, RATE, genre="Geschichte")
    tcon = ID3(path).getall("TCON")
    assert len(tcon) == 1 and tcon[0].text == ["Geschichte"] and tcon[0].encoding == 1
