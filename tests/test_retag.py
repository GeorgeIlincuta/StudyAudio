from pathlib import Path

import pytest
from mutagen.id3 import ID3

from guideaudio import cli
from guideaudio.retag import audio_digest

GUIDE = """Grundlagen für das Labor.

# Der Atombau — Atomic structure

Alles besteht aus Atomen. Ein Atom hat einen Kern.
"""


@pytest.fixture
def built(tmp_path, monkeypatch, fake_engine):
    """A guide built with the fake engine (so its clips are cached), then stripped of its SYLT."""
    monkeypatch.setattr(cli, "build_engine", lambda: fake_engine)
    monkeypatch.setattr(cli, "engine_identity", lambda: (fake_engine.engine_id, fake_engine.sample_rate))
    guide = tmp_path / "guide_de.txt"
    guide.write_text(GUIDE, encoding="utf-8")
    out = tmp_path / "guide_de.mp3"
    cache = tmp_path / "c"
    assert cli.main([str(guide), "-o", str(out), "--cache-dir", str(cache)]) == 0
    tags = ID3(out)
    tags.delall("SYLT")
    tags.delall("TCON")
    tags.save(out, v2_version=3)
    return guide, out, cache


def retag(guide: Path, out: Path, cache: Path) -> int:
    return cli.main([str(guide), "--retag", "-o", str(out), "--cache-dir", str(cache)])


def test_retag_adds_the_text_and_keeps_the_audio(built):
    guide, out, cache = built
    before = audio_digest(out)
    chapters_before = [c.start_time for c in ID3(out).getall("CHAP")]

    assert retag(guide, out, cache) == 0

    tags = ID3(out)
    assert audio_digest(out) == before
    sylt = tags.getall("SYLT")[0]
    assert sylt.lang == "deu"
    assert [t for t, _ in sylt.text] == [
        "Grundlagen für das Labor.", "# Der Atombau — Atomic structure", "\nAlles besteht aus Atomen.",
        "Ein Atom hat einen Kern.",
    ]
    assert [c.start_time for c in tags.getall("CHAP")] == chapters_before


def test_retag_needs_no_engine(built, monkeypatch):
    guide, out, cache = built
    monkeypatch.setattr(cli, "build_engine", lambda: pytest.fail("retag must not load the TTS model"))
    assert retag(guide, out, cache) == 0


def test_retag_stops_on_a_missing_clip_and_changes_nothing(built, capsys):
    guide, out, cache = built
    for wav in cache.rglob("*.wav"):
        wav.unlink()
        break
    original = out.read_bytes()

    assert retag(guide, out, cache) == 1
    assert out.read_bytes() == original
    assert "not in the cache" in capsys.readouterr().err


def test_retag_refuses_when_the_text_no_longer_matches_the_audio(built, capsys, fake_engine):
    guide, out, cache = built
    guide.write_text(GUIDE.replace("Ein Atom hat einen Kern.", "Ein Atom hat einen Kern, der jetzt viel länger beschrieben wird."),
                     encoding="utf-8")
    blocks = cli.split_text(cli.read_text(guide))
    timeline = cli.text_timeline(blocks, "de", cli.VoiceConfig().for_language("de"), cli.TextPauseConfig())
    cli.synthesize_clips([s for s in timeline if isinstance(s, cli.ClipSpec)], fake_engine, cache)
    original = out.read_bytes()

    assert retag(guide, out, cache) == 1
    assert out.read_bytes() == original
    assert "does not match" in capsys.readouterr().err


def test_retag_of_a_missing_file_fails(tmp_path, monkeypatch, fake_engine):
    monkeypatch.setattr(cli, "engine_identity", lambda: (fake_engine.engine_id, fake_engine.sample_rate))
    guide = tmp_path / "guide_de.txt"
    guide.write_text(GUIDE, encoding="utf-8")
    assert retag(guide, tmp_path / "nope.mp3", tmp_path / "c") == 1


def test_engine_identity_is_the_paced_id_without_loading_the_model(monkeypatch):
    import guideaudio.tts.supertonic as supertonic

    monkeypatch.setattr(supertonic.SupertonicEngine, "__init__", lambda *a, **k: pytest.fail("model loaded"))
    engine_id, rate = cli.engine_identity()
    assert engine_id.startswith("supertonic-3+pace")
    assert rate > 0


def test_retag_adds_the_genre_and_keeps_the_audio(built):
    guide, out, cache = built
    before = audio_digest(out)
    assert ID3(out).getall("TCON") == []

    assert retag(guide, out, cache) == 0

    assert ID3(out)["TCON"].text == ["Leitfaden"]
    assert audio_digest(out) == before
