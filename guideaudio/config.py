"""Tunable settings for the whole pipeline.

Every value a user might reasonably want to change lives here, so that
changing the feel of the track never means editing pipeline code.
"""

from dataclasses import dataclass
from pathlib import Path

# Audio format, fixed across the pipeline. Supertonic emits 44.1 kHz.
SAMPLE_RATE = 44100
MP3_BITRATE = 64  # kbps, mono — ~60 MB for two hours
# Every clip is scaled so its loudest sample hits this level (1.0 is full
# scale). Supertonic clips peak around 0.45 on their own, which plays back
# noticeably quiet; 0.95 leaves a little headroom for the MP3 encoder.
TARGET_PEAK = 0.95

# Anchored to the project folder, not the current directory, so the cache is
# shared and reused no matter where the command is run from.
PROJECT_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_DIR / "cache" / "audio"
OUT_DIR = PROJECT_DIR / "out"

LANGUAGES = ("en", "de")


@dataclass(frozen=True)
class TextPauseConfig:
    """Silence while reading a guide aloud, in seconds."""

    after_sentence: float = 0.6
    after_paragraph: float = 1.5


@dataclass(frozen=True)
class VoiceConfig:
    """Supertonic preset voice name per language.

    An unknown name fails at synthesis time, not at import time, so confirm a
    new name with a short `--limit` preview before building a whole guide.
    "M1" is the voice verified in GermanAudio's listening test.
    """

    de: str = "M1"
    en: str = "M1"

    def for_language(self, language: str) -> str:
        return getattr(self, language)


@dataclass(frozen=True)
class CheckConfig:
    """Limits the text check enforces or warns about."""

    max_heading_words: int = 4
    long_sentence_words: int = 25
    min_chapter_words: int = 300
    max_chapter_words: int = 650
    words_per_minute: int = 110


@dataclass(frozen=True)
class PaceConfig:
    """Keeps short sentences from being rushed.

    Supertonic picks its tempo from the length of the input: a short
    sentence like "Teil eins ist die allgemeine Chemie." comes out 25 to 60
    percent faster than a long one. Every clip is measured after synthesis,
    and one spoken faster than the target is synthesized again, slower.
    The target is the pace measured on long sentences in both languages.
    """

    target_chars_per_second: float = 16.5
    # A clip up to this fraction above the target counts as normal pace.
    tolerance: float = 0.08
    # Never slow a clip below this engine speed, however fast it measured.
    # Supertonic rejects anything below 0.7.
    min_speed: float = 0.7
    # Synthesis attempts per clip, including the first.
    max_attempts: int = 3
