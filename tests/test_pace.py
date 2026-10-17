import numpy as np
import pytest

from guideaudio.config import PaceConfig
from guideaudio.pace import PacedEngine, speech_seconds

RATE = 44100
PACE = PaceConfig(target_chars_per_second=16.0, tolerance=0.08, min_speed=0.6, max_attempts=3)


class RushingEngine:
    """Speaks short texts too fast, like Supertonic: at speed 1.0 a text of
    under 40 characters runs at 24 chars/s, a longer one at 16 chars/s.
    Duration scales with 1/speed. Each clip has 0.3 s of silence at both ends."""

    engine_id = "rushing"
    sample_rate = RATE

    def __init__(self):
        self.speeds: list[float] = []

    def synthesize(self, text, language, voice, speed=1.0):
        self.speeds.append(speed)
        chars_per_second = (24.0 if len(text) < 40 else 16.0) * speed
        speech = np.full(int(len(text) / chars_per_second * RATE), 0.5, dtype=np.float32)
        edge = np.zeros(int(0.3 * RATE), dtype=np.float32)
        return np.concatenate([edge, speech, edge])


def rate(samples, text):
    return len(text) / speech_seconds(samples, RATE)


def test_speech_seconds_ignores_leading_and_trailing_silence():
    samples = np.concatenate([np.zeros(RATE), np.full(2 * RATE, 0.4), np.zeros(RATE)]).astype(np.float32)

    assert speech_seconds(samples, RATE) == pytest.approx(2.0, abs=0.01)


def test_speech_seconds_of_a_silent_clip_is_zero():
    assert speech_seconds(np.zeros(RATE, dtype=np.float32), RATE) == 0.0


def test_a_clip_at_normal_pace_is_synthesized_once():
    inner = RushingEngine()
    text = "This is a long sentence that the engine reads at a normal pace."

    PacedEngine(inner, PACE, base_speed=1.0).synthesize(text, "en", "M1")

    assert inner.speeds == [1.0]


def test_a_rushed_short_sentence_is_slowed_to_the_target_pace():
    inner = RushingEngine()
    text = "Part one is chemistry."

    samples = PacedEngine(inner, PACE, base_speed=1.0).synthesize(text, "en", "M1")

    assert inner.speeds[0] == 1.0
    assert inner.speeds[1] == pytest.approx(16.0 / 24.0, rel=0.02)
    assert rate(samples, text) == pytest.approx(16.0, rel=PACE.tolerance)


def test_speed_never_drops_below_the_minimum():
    inner = RushingEngine()
    slow_floor = PaceConfig(target_chars_per_second=8.0, tolerance=0.08, min_speed=0.6, max_attempts=3)

    PacedEngine(inner, slow_floor, base_speed=1.0).synthesize("Part one is chemistry.", "en", "M1")

    assert min(inner.speeds) == pytest.approx(0.6)


def test_stops_after_the_maximum_number_of_attempts_and_keeps_the_closest():
    class Erratic(RushingEngine):
        """Ignores the speed and returns 24, 21, then 19 chars/s: always too fast."""

        def synthesize(self, text, language, voice, speed=1.0):
            self.speeds.append(speed)
            chars_per_second = (24.0, 21.0, 19.0)[len(self.speeds) - 1]
            return np.full(int(len(text) / chars_per_second * RATE), 0.5, dtype=np.float32)

    inner = Erratic()
    text = "Part one is chemistry."
    samples = PacedEngine(inner, PACE, base_speed=1.0).synthesize(text, "en", "M1")

    assert len(inner.speeds) == PACE.max_attempts
    assert rate(samples, text) == pytest.approx(19.0, rel=0.01)


def test_engine_id_includes_the_pace_so_changing_it_resynthesizes():
    inner = RushingEngine()

    assert PacedEngine(inner, PACE).engine_id != inner.engine_id
    assert PacedEngine(inner, PACE).engine_id != PacedEngine(
        inner, PaceConfig(target_chars_per_second=15.0)
    ).engine_id


def test_sample_rate_is_passed_through():
    assert PacedEngine(RushingEngine(), PACE).sample_rate == RATE
