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
