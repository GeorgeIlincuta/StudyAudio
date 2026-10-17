"""Synthesis cache, rendering, encoding and chapter marks — ported from GermanAudio."""

import numpy as np
import pytest

from guideaudio.assemble import Silence, encode_mp3, render
from guideaudio.audio import read_wav, write_wav
from guideaudio.chapters import mark_positions
from guideaudio.config import TextPauseConfig
from guideaudio.reader import split_text, text_marks, text_timeline
from guideaudio.synth import ClipSpec, clip_path, synthesize_clips

RATE = 44100
GUIDE = "Title.\n\n# Atoms\n\nOne. Two.\n\n# Moles\n\nThree.\n"


def timeline_for(text=GUIDE):
    blocks = split_text(text)
    return text_timeline(blocks, "en", "M1", TextPauseConfig()), text_marks(blocks)


def synthesize(timeline, engine, cache_dir):
    return synthesize_clips([i for i in timeline if isinstance(i, ClipSpec)], engine, cache_dir)


@pytest.mark.parametrize(
    "other",
    [ClipSpec("Other.", "en", "M1"), ClipSpec("Atoms.", "de", "M1"), ClipSpec("Atoms.", "en", "F1")],
)
def test_clip_key_differs_on_text_language_or_voice(other):
    assert ClipSpec("Atoms.", "en", "M1").key("supertonic-3") != other.key("supertonic-3")


def test_same_sentence_in_english_and_german_are_separate_clips(tmp_path, fake_engine):
    report = synthesize_clips(
        [ClipSpec("DNA.", "en", "M1"), ClipSpec("DNA.", "de", "M1"), ClipSpec("DNA.", "en", "M1")],
        fake_engine, tmp_path,
    )

    assert report.synthesized == 2


def test_second_run_reuses_the_cache(tmp_path, fake_engine):
    timeline, _ = timeline_for()
    synthesize(timeline, fake_engine, tmp_path)
    fake_engine.calls.clear()

    report = synthesize(timeline, fake_engine, tmp_path)

    assert report.synthesized == 0
    assert fake_engine.calls == []


def test_one_failure_does_not_stop_the_run_and_leaves_no_file(tmp_path):
    class Flaky:
        engine_id = "flaky"
        sample_rate = RATE

        def synthesize(self, text, language, voice):
            if text == "Two.":
                raise RuntimeError("unsupported character")
            return np.array([0.1, 0.2], dtype=np.float32)

    timeline, _ = timeline_for()
    report = synthesize(timeline, Flaky(), tmp_path)

    assert [spec.text for spec, _ in report.failures] == ["Two."]
    assert not clip_path(tmp_path, ClipSpec("Two.", "en", "M1"), "flaky").exists()


def test_render_length_is_the_sum_of_clips_and_pauses(tmp_path, fake_engine):
    timeline, _ = timeline_for()
    synthesize(timeline, fake_engine, tmp_path)

    expected = 0
    for item in timeline:
        if isinstance(item, Silence):
            expected += int(round(item.seconds * RATE))
        else:
            expected += len(read_wav(clip_path(tmp_path, item, fake_engine.engine_id))[0])

    assert len(render(timeline, tmp_path, fake_engine.engine_id, RATE)) == expected


def test_render_normalizes_every_clip_to_the_target_peak(tmp_path, fake_engine):
    timeline, _ = timeline_for()
    synthesize(timeline, fake_engine, tmp_path)

    samples = render(timeline, tmp_path, fake_engine.engine_id, RATE, target_peak=0.9)

    assert np.abs(samples).max() == pytest.approx(0.9, abs=1e-3)


def test_render_leaves_a_silent_clip_silent(tmp_path, fake_engine):
    timeline, _ = timeline_for("Title.\n")
    write_wav(clip_path(tmp_path, timeline[0], fake_engine.engine_id), np.zeros(100, dtype=np.float32), RATE)

    samples = render(timeline, tmp_path, fake_engine.engine_id, RATE)

    assert np.isfinite(samples).all() and not samples.any()


def test_render_reports_a_missing_clip_by_text(tmp_path, fake_engine):
    timeline, _ = timeline_for()

    with pytest.raises(FileNotFoundError, match="Title"):
        render(timeline, tmp_path, fake_engine.engine_id, RATE)


def test_chapter_marks_are_exact_sample_offsets_of_the_spoken_headings(tmp_path, fake_engine):
    timeline, marks = timeline_for()
    synthesize(timeline, fake_engine, tmp_path)
    samples = render(timeline, tmp_path, fake_engine.engine_id, RATE, target_peak=1.0)

    chapters, total = mark_positions(timeline, marks, tmp_path, fake_engine.engine_id, RATE)

    assert total == len(samples)
    assert [c.title for c in chapters] == ["Atoms", "Moles"]
    for chapter in chapters:
        # each heading starts right after a paragraph pause of silence
        assert not samples[chapter.start_sample - int(1.5 * RATE): chapter.start_sample].any()
        assert samples[chapter.start_sample: chapter.start_sample + 200].any()


def test_encode_mp3_writes_a_real_mp3_across_several_blocks(tmp_path):
    t = np.arange(65 * RATE) / RATE
    path = tmp_path / "nested" / "track.mp3"

    encode_mp3((0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32), RATE, path, bitrate=64)

    head = path.read_bytes()[:3]
    assert head == b"ID3" or (head[0] == 0xFF and head[1] & 0xE0 == 0xE0)
    # 65 s at 64 kbps is about 520 kB; a dropped block would be far smaller
    assert 400_000 < path.stat().st_size < 650_000
