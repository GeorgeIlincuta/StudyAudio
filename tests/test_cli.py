import pytest
from mutagen.id3 import ID3

from guideaudio import cli

GUIDE_EN = """Foundations for the lab.

# Atomic structure

Everything is made of atoms. An atom has a nucleus.

# The mole

A mole is a counting unit.
"""

GUIDE_DE = """Grundlagen für das Labor.

# Der Atombau — Atomic structure

Alles besteht aus Atomen.
"""


@pytest.fixture(autouse=True)
def stub_engine(monkeypatch, fake_engine):
    """Never let the CLI tests touch the real model."""
    monkeypatch.setattr(cli, "build_engine", lambda: fake_engine)
    return fake_engine


def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def run(path, tmp_path, *extra):
    return cli.main([str(path), "--cache-dir", str(tmp_path / "cache"), *extra])


@pytest.mark.parametrize(
    ("name", "expected"),
    [("guide_en.txt", "en"), ("Phase1_Guide_DE.txt", "de"), ("guide.txt", None), ("guide_fr.txt", None)],
)
def test_language_comes_from_the_file_name(name, expected, tmp_path):
    assert cli.detect_language(tmp_path / name) == expected


def test_unknown_language_stops_before_reading(tmp_path, capsys):
    path = write(tmp_path, "guide.txt", GUIDE_EN)

    assert run(path, tmp_path, "--check") == 2
    assert "--lang" in capsys.readouterr().err


def test_check_passes_without_synthesizing(tmp_path, capsys, stub_engine):
    path = write(tmp_path, "guide_en.txt", GUIDE_EN)

    assert run(path, tmp_path, "--check") == 0
    out = capsys.readouterr().out
    assert "2 chapters, 4 sentences" in out
    assert "check passed" in out
    assert stub_engine.calls == []


def test_check_errors_fail_and_block_the_build(tmp_path, capsys, stub_engine):
    path = write(tmp_path, "guide_en.txt", GUIDE_EN + "\nIt has 11 protons.\n")

    assert run(path, tmp_path, "-o", str(tmp_path / "x.mp3")) == 1
    assert "digits" in capsys.readouterr().err
    assert stub_engine.calls == []
    assert not (tmp_path / "x.mp3").exists()


@pytest.mark.parametrize(("name", "text", "language"), [("guide_en.txt", GUIDE_EN, "en"), ("guide_de.txt", GUIDE_DE, "de")])
def test_build_reads_every_sentence_in_the_guide_language(name, text, language, tmp_path, stub_engine):
    path = write(tmp_path, name, text)
    out = tmp_path / "guide.mp3"

    assert run(path, tmp_path, "-o", str(out)) == 0
    assert out.stat().st_size > 1000
    assert {call[1] for call in stub_engine.calls} == {language}


def test_build_writes_title_and_chapters_for_the_player(tmp_path):
    out = tmp_path / "guide.mp3"
    run(write(tmp_path, "guide_de.txt", GUIDE_DE), tmp_path, "-o", str(out))

    tags = ID3(out)
    chapters = sorted(tags.getall("CHAP"), key=lambda c: c.start_time)
    assert tags["TIT2"].text == ["Grundlagen für das Labor"]
    assert [c.sub_frames["TIT2"].text[0] for c in chapters] == ["Der Atombau — Atomic structure"]
    assert tags.getall("CTOC")[0].sub_frames["TIT2"].text == ["Inhalt"]
    texts = [t for t, _ in tags.getall("SYLT")[0].text]
    assert texts == ["Grundlagen für das Labor.", "# Der Atombau — Atomic structure", "\nAlles besteht aus Atomen."]
    assert tags.getall("SYLT")[0].lang == "deu"


def test_english_table_of_contents_is_labelled_in_english(tmp_path):
    out = tmp_path / "guide.mp3"
    run(write(tmp_path, "guide_en.txt", GUIDE_EN), tmp_path, "-o", str(out))

    assert ID3(out).getall("CTOC")[0].sub_frames["TIT2"].text == ["Contents"]


def test_lang_flag_overrides_the_file_name(tmp_path, stub_engine):
    path = write(tmp_path, "notes.txt", GUIDE_EN)

    assert run(path, tmp_path, "--lang", "en", "-o", str(tmp_path / "n.mp3")) == 0
    assert {call[1] for call in stub_engine.calls} == {"en"}


def test_limit_reads_only_the_first_sentences_but_keeps_the_full_title(tmp_path, stub_engine):
    out = tmp_path / "preview.mp3"
    run(write(tmp_path, "guide_en.txt", GUIDE_EN), tmp_path, "--limit", "2", "-o", str(out))

    assert [call[0] for call in stub_engine.calls] == ["Foundations for the lab.", "Atomic structure."]
    assert ID3(out)["TIT2"].text == ["Foundations for the lab"]


def test_default_output_is_named_after_the_input_and_a_preview_never_replaces_it(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "OUT_DIR", tmp_path / "out")
    path = write(tmp_path, "guide_en.txt", GUIDE_EN)

    run(path, tmp_path, "--limit", "2")
    run(path, tmp_path)

    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == ["guide_en.mp3", "guide_en_preview.mp3"]


def test_second_build_reuses_the_cache(tmp_path, stub_engine, capsys):
    path = write(tmp_path, "guide_en.txt", GUIDE_EN)
    run(path, tmp_path, "-o", str(tmp_path / "a.mp3"))
    stub_engine.calls.clear()

    run(path, tmp_path, "-o", str(tmp_path / "b.mp3"))

    assert stub_engine.calls == []
    assert "0 new" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("name", "expected"),
    [("phase1_guide_de.txt", "Leitfaden"), ("story_grundlagen_phase1_de.txt", "Geschichte"),
     ("Story_X_en.txt", "Geschichte"), ("my_story_de.txt", "Leitfaden"),
     ("encyclopedia_bakterien_de.txt", "Enzyklopädie"), ("my_encyclopedia_de.txt", "Leitfaden")],
)
def test_guide_genre_from_the_file_name(name, expected):
    from pathlib import Path

    assert cli.guide_genre(Path(name)) == expected


def test_build_writes_the_genre(tmp_path):
    guide = tmp_path / "guide.mp3"
    run(write(tmp_path, "guide_de.txt", GUIDE_DE), tmp_path, "-o", str(guide))
    assert ID3(guide)["TCON"].text == ["Leitfaden"]

    story = tmp_path / "story.mp3"
    run(write(tmp_path, "story_labor_de.txt", GUIDE_DE), tmp_path, "-o", str(story))
    assert ID3(story)["TCON"].text == ["Geschichte"]

    encyclopedia = tmp_path / "encyclopedia.mp3"
    run(write(tmp_path, "encyclopedia_labor_de.txt", GUIDE_DE), tmp_path, "-o", str(encyclopedia))
    assert ID3(encyclopedia)["TCON"].text == ["Enzyklopädie"]


ENCYCLOPEDIA_DE = """Bakterien.

# Escherichia coli — Escherichia coli

Einordnung: Ein Darmbakterium.

Kurz gesagt: Häufig im Urin.
"""


def test_markdown_writes_the_book_without_synthesizing(tmp_path, stub_engine):
    output = tmp_path / "book.md"

    assert run(write(tmp_path, "encyclopedia_bakterien_de.txt", ENCYCLOPEDIA_DE), tmp_path,
               "--markdown", "-o", str(output)) == 0

    assert "## 🦠 Escherichia coli" in output.read_text(encoding="utf-8")
    assert stub_engine.calls == []


def test_check_of_an_encyclopedia_lists_its_sections(tmp_path, capsys):
    assert run(write(tmp_path, "encyclopedia_bakterien_de.txt", ENCYCLOPEDIA_DE), tmp_path, "--check") == 0

    assert "1 entries, each with the sections: Einordnung → Kurz gesagt" in capsys.readouterr().out


def _library(tmp_path):
    from mutagen.id3 import TIT2

    root = tmp_path / "MTL"
    track = root / "Enzyklopädie" / "encyclopedia_bakterien_de.mp3"
    track.parent.mkdir(parents=True)
    track.write_bytes(bytes(10))
    tag = ID3()
    tag.add(TIT2(encoding=3, text=["01 · Bakterien nach Gruppen"]))
    tag.save(track)
    return root


def test_build_numbers_the_title_from_the_library(tmp_path):
    path = write(tmp_path, "encyclopedia_viren_de.txt", GUIDE_DE)
    out = tmp_path / "encyclopedia_viren_de.mp3"
    root = _library(tmp_path)

    assert run(path, tmp_path, "-o", str(out), "--title", "Viren nach Gruppen", "--library", str(root)) == 0

    assert ID3(out)["TIT2"].text == ["02 · Viren nach Gruppen"]


def test_a_preview_build_is_not_numbered(tmp_path):
    path = write(tmp_path, "encyclopedia_viren_de.txt", GUIDE_DE)
    out = tmp_path / "v.mp3"
    root = _library(tmp_path)

    assert run(path, tmp_path, "-o", str(out), "--title", "Viren", "--library", str(root), "--limit", "1") == 0

    assert ID3(out)["TIT2"].text == ["Viren"]


def test_publish_copies_the_built_track_into_the_library(tmp_path, capsys):
    path = write(tmp_path, "encyclopedia_viren_de.txt", GUIDE_DE)
    out = tmp_path / "encyclopedia_viren_de.mp3"
    root = _library(tmp_path)

    assert run(path, tmp_path, "-o", str(out), "--library", str(root), "--publish") == 0

    assert (root / "Enzyklopädie" / "encyclopedia_viren_de.mp3").read_bytes() == out.read_bytes()
    assert "phone: not connected" in capsys.readouterr().out


def test_publish_is_refused_for_a_preview(tmp_path):
    path = write(tmp_path, "encyclopedia_viren_de.txt", GUIDE_DE)
    root = _library(tmp_path)

    assert run(path, tmp_path, "-o", str(tmp_path / "v.mp3"), "--library", str(root), "--limit", "1", "--publish") == 2
