"""Even out the speaking pace between short and long sentences.

Supertonic decides how fast to speak from the input alone, and it rushes
short inputs: in the German guide, "Teil eins ist die allgemeine Chemie."
came out at 26 characters per second, long sentences at 16.5. Its `speed`
argument scales the duration almost linearly, so a clip that measures too
fast is synthesized again at `speed * target / measured`. The engine's output
also varies a little from call to call, so a few attempts are allowed and
the one closest to the target pace is kept.

This wraps any engine whose `synthesize` takes a `speed`, and is itself an
ordinary engine to the rest of the pipeline.
"""

import numpy as np

from guideaudio.config import PaceConfig
from guideaudio.tts.supertonic import DEFAULT_SPEED

# A sample below this fraction of the clip's peak counts as silence when
# measuring where speech starts and ends.
_SILENCE_FRACTION = 0.02


def speech_seconds(samples: np.ndarray, sample_rate: int) -> float:
    """Length of the clip from the first to the last audible sample."""
    level = np.abs(samples)
    peak = float(level.max()) if len(level) else 0.0
    if peak == 0.0:
        return 0.0
    audible = np.flatnonzero(level > _SILENCE_FRACTION * peak)
    return (audible[-1] - audible[0] + 1) / sample_rate


class PacedEngine:
    def __init__(self, inner, pace: PaceConfig, base_speed: float = DEFAULT_SPEED):
        self._inner = inner
        self._pace = pace
        self._base_speed = base_speed
        self.sample_rate = inner.sample_rate
        # The pace settings decide the audio, so they belong in the cache key:
        # changing them re-synthesizes instead of reusing clips made under old ones.
        self.engine_id = (
            f"{inner.engine_id}+pace{pace.target_chars_per_second:g}"
            f"/{pace.tolerance:g}/{pace.min_speed:g}/{pace.max_attempts}"
        )

    def synthesize(self, text: str, language: str, voice: str) -> np.ndarray:
        target = self._pace.target_chars_per_second
        speed = self._base_speed
        best: tuple[float, np.ndarray] | None = None

        for _ in range(self._pace.max_attempts):
            samples = self._inner.synthesize(text, language, voice, speed=speed)
            seconds = speech_seconds(samples, self.sample_rate)
            if seconds == 0.0:
                return samples
            rate = len(text) / seconds
            if rate <= target * (1 + self._pace.tolerance):
                return samples
            if best is None or abs(rate - target) < best[0]:
                best = (abs(rate - target), samples)
            speed = max(self._pace.min_speed, speed * target / rate)

        assert best is not None
        return best[1]

