"""Command-line entry point — check a guide, then build it into a chaptered MP3.

    python -m guideaudio phase1_guide_en.txt --check
    python -m guideaudio phase1_guide_de.txt --limit 20 -o out/preview_de.mp3
    python -m guideaudio phase1_guide_de.txt
    python -m guideaudio encyclopedia_bakterien_de.txt --markdown
"""

import argparse
import sys
import wave
from pathlib import Path

from guideaudio.assemble import encode_mp3, render
from guideaudio.chapters import Chapter, item_starts, line_positions, write_tags
from guideaudio.check import CheckReport, check_text
from guideaudio.config import (
    CACHE_DIR,
    LANGUAGES,
    MP3_BITRATE,
    OUT_DIR,
    CheckConfig,
    PaceConfig,
    TextPauseConfig,
    VoiceConfig,
)
from guideaudio.reader import (
    LoadError,
    guide_title,
    limit_sentences,
    read_text,
    split_text,
    text_lines,
    text_marks,
    text_timeline,
)
from guideaudio.markdown import render_markdown
from guideaudio.retag import RetagError, retag_file
from guideaudio.synth import ClipSpec, synthesize_clips


def engine_identity() -> tuple[str, int]:
    """The paced engine's cache id and sample rate, without loading the model (retag only needs the cache keys)."""
    from types import SimpleNamespace

    from guideaudio.config import SAMPLE_RATE
    from guideaudio.pace import PacedEngine
    from guideaudio.tts.supertonic import SupertonicEngine

    paced = PacedEngine(SimpleNamespace(engine_id=SupertonicEngine.engine_id, sample_rate=SAMPLE_RATE), PaceConfig())
    return paced.engine_id, paced.sample_rate


def build_engine():
    """Indirection so tests can substitute a fake without touching the model."""
    from guideaudio.pace import PacedEngine
    from guideaudio.tts.supertonic import SupertonicEngine

    return PacedEngine(SupertonicEngine(), PaceConfig())


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="guideaudio",
        description="Read an English or German study guide aloud into a chaptered MP3.",
    )
    parser.add_argument("input", type=Path, help="the guide, a UTF-8 .txt file")
    parser.add_argument(
        "--lang", choices=LANGUAGES, default=None,
        help="language of the guide (default: from a file name ending in _en or _de)",
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help="output MP3 path (default: out/<input name>.mp3)",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="check the text rules and exit without synthesizing",
    )
    parser.add_argument(
        "--title", default=None,
        help="title shown in the player (default: the guide's first line)",
    )
    parser.add_argument(
        "--retag", action="store_true",
        help="rewrite only the tag (title, chapters, read-along text) of the existing output file from the cache; "
             "no synthesis, the audio is not touched",
    )
    parser.add_argument(
        "--markdown", action="store_true",
        help="write the text as a Markdown reference book (default: out/<input name>.md) instead of audio",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="only read the first N sentences, for a preview",
    )
    parser.add_argument(
        "--cache-dir", type=Path, default=CACHE_DIR,
        help="where synthesized clips are cached (default: cache/audio next to the tool)",
    )
    return parser.parse_args(argv)


GUIDE_GENRE = "Leitfaden"
STORY_GENRE = "Geschichte"
ENCYCLOPEDIA_GENRE = "Enzyklopädie"


def guide_genre(path: Path) -> str:
    """The player's file type, written as the ID3 genre, from the input's name prefix.

    "story_..." is a story, "encyclopedia_..." an encyclopedia, everything else a guide.
    """
    name = Path(path).name.lower()
    if name.startswith("story_"):
        return STORY_GENRE
    if name.startswith("encyclopedia_"):
        return ENCYCLOPEDIA_GENRE
    return GUIDE_GENRE


def detect_language(path: Path) -> str | None:
    """"guide_en.txt" -> "en", "guide_de.txt" -> "de", anything else -> None."""
    suffix = Path(path).stem.lower().rsplit("_", 1)[-1]
    return suffix if suffix in LANGUAGES else None


def _format_duration(total_seconds: float) -> str:
    hours, remainder = divmod(int(total_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    return f"{minutes}m {seconds}s"


def _print_report(report: CheckReport, config: CheckConfig, show_chapters: bool) -> None:
    for error in report.errors:
        print(f"error: {error}", file=sys.stderr)
    for warning in report.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    if show_chapters and report.chapters:
        print()
        for chapter in report.chapters:
            note = ""
            if chapter.words < config.min_chapter_words:
                note = "   (short)"
            elif chapter.words > config.max_chapter_words:
                note = "   (long)"
            print(f"  {chapter.words:5d} words  {chapter.title}{note}")
        print()
    if report.sections:
        print(f"{len(report.entries)} entries, each with the sections: {' → '.join(report.sections)}")
    minutes = round(report.words / config.words_per_minute)
    print(
        f"{len(report.chapters)} chapters, {report.sentences} sentences, "
        f"{report.words} words, about {minutes} minutes"
    )


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = _parse_args(argv)

    language = args.lang or detect_language(args.input)
    if language is None:
        print(
            f"{args.input}: cannot tell the language; pass --lang en or --lang de "
            "(or name the file *_en.txt / *_de.txt)",
            file=sys.stderr,
        )
        return 2

    try:
        text = read_text(args.input)
    except LoadError as error:
        for problem in error.problems:
            print(problem, file=sys.stderr)
        return 1

    config = CheckConfig()
    genre = guide_genre(args.input)
    report = check_text(text, language, config, encyclopedia=genre == ENCYCLOPEDIA_GENRE)
    print(f"{args.input} ({language})")
    _print_report(report, config, show_chapters=args.check)
    if not report.ok:
        print(f"{len(report.errors)} error(s); fix them before building", file=sys.stderr)
        return 1
    if args.check:
        print("check passed")
        return 0

    blocks = split_text(text)
    if args.markdown:
        output = args.output or OUT_DIR / f"{args.input.stem}.md"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_markdown(blocks, language, args.input.name), encoding="utf-8")
        print(f"done: {output}")
        return 0
    title = args.title or guide_title(blocks) or args.input.stem
    if args.limit is not None:
        blocks = limit_sentences(blocks, args.limit)
    voice = VoiceConfig().for_language(language)
    timeline = text_timeline(blocks, language, voice, TextPauseConfig())
    marks = text_marks(blocks)
    lines = text_lines(blocks)

    # A preview gets its own default name, so it never replaces the full track.
    default_name = f"{args.input.stem}_preview.mp3" if args.limit is not None else f"{args.input.stem}.mp3"
    output = args.output or OUT_DIR / default_name
    # Checked now, not after an hour of synthesis: a bad output path should
    # fail in a second, before synthesis even starts.
    output.parent.mkdir(parents=True, exist_ok=True)

    if args.retag:
        engine_id, sample_rate = engine_identity()
        try:
            chapters_written, lines_written = retag_file(
                output, title, timeline, marks, lines, args.cache_dir, engine_id, sample_rate, language, genre
            )
        except RetagError as error:
            print(f"retag failed: {error}", file=sys.stderr)
            return 1
        except (OSError, wave.Error) as error:
            print(f"retag failed: {error} — nothing changed", file=sys.stderr)
            return 1
        print(f"retagged {output}: title {title!r}, genre {genre}, {chapters_written} chapters, {lines_written} text lines")
        return 0

    engine = build_engine()

    def progress(index: int, total: int, spec) -> None:
        print(f"\r  synthesizing {index}/{total}", end="", flush=True)

    print("synthesizing clips (cached clips are reused)...")
    clips = [item for item in timeline if isinstance(item, ClipSpec)]
    synth = synthesize_clips(clips, engine, args.cache_dir, progress=progress)
    print()
    print(f"  {synth.synthesized} new, {synth.reused} reused from cache")

    if synth.failures:
        print(f"{len(synth.failures)} clips failed to synthesize:", file=sys.stderr)
        for spec, message in synth.failures:
            print(f"  [{spec.language}] {spec.text!r}: {message}", file=sys.stderr)
        print("no track written; fix the above and re-run to resume", file=sys.stderr)
        return 1

    try:
        print("assembling track...")
        samples = render(timeline, args.cache_dir, engine.engine_id, engine.sample_rate)
    except (FileNotFoundError, ValueError, wave.Error) as error:
        # Exactly what a missing or corrupt cache entry raises; the recovery
        # is the same for all three and not obvious from the raw message.
        print(f"failed to assemble the track: {error}", file=sys.stderr)
        print(
            f"this looks like a problem with a cached clip in {args.cache_dir}: "
            "delete the offending file (or the whole cache directory) and "
            "re-run to re-synthesize it",
            file=sys.stderr,
        )
        return 1
    except (MemoryError, OSError) as error:
        print(f"failed to assemble the track: {error}", file=sys.stderr)
        return 1

    print(f"  {_format_duration(len(samples) / engine.sample_rate)} of audio")

    try:
        print(f"encoding {output}...")
        encode_mp3(samples, engine.sample_rate, output, MP3_BITRATE)
    except (MemoryError, OSError) as error:
        print(f"failed to encode {output}: {error}", file=sys.stderr)
        return 1

    try:
        starts, total = item_starts(timeline, args.cache_dir, engine.engine_id, engine.sample_rate)
        chapters = [Chapter(marks[i], starts[i]) for i in sorted(marks)]
        write_tags(output, title, chapters, total, engine.sample_rate, language, line_positions(starts, lines), genre=genre)
    except (OSError, wave.Error) as error:
        print(f"track written, but adding the title and chapters failed: {error}", file=sys.stderr)
        return 1
    print(f"  title {title!r}, genre {genre}, {len(chapters)} chapters, {len(lines)} text lines")

    size_mb = output.stat().st_size / 1_000_000
    print(f"done: {output} ({size_mb:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
