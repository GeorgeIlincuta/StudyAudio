# guideaudio

Reads English and German study guides aloud into chaptered MP3s for the Hörplayer app, using the Supertonic
text-to-speech model locally. It's a guide-only version of GermanAudio (`C:\LOCAL FILES\Claude Code\Python\GermanAudio`):
the cache, rendering, MP3 encoding and chapter tags are copied from there, and the vocabulary mode is gone.

## Setup

```
pip install -r requirements.txt
```

The Supertonic model downloads automatically on the first run (GermanAudio already downloaded it on this PC).

## Workflow

1. Write the guide with `prompt_audio_guide.txt` in a Claude chat, once per language.
2. Save it as UTF-8 with the language at the end of the name: `<topic>_guide_en.txt` or `<topic>_guide_de.txt`.
3. Check the text rules:

   ```
   python -m guideaudio phase1_guide_en.txt --check
   ```

   It lists every error (digits, symbols, abbreviations, bad headings, missing sentence endings) with its line
   number, plus warnings (long sentences, chapters outside 300–650 words) and the length of each chapter.
   A build refuses to start while there are errors.
4. Listen to a preview of the first sentences:

   ```
   python -m guideaudio phase1_guide_en.txt --limit 20
   ```

   This writes `out/phase1_guide_en_preview.mp3` and never replaces the full track.
5. Build the full guide:

   ```
   python -m guideaudio phase1_guide_en.txt
   ```

   This writes `out/phase1_guide_en.mp3`. Use `-o` for another name and `--title` for another player title
   (the default title is the guide's first line).

The language comes from the `_en` / `_de` file name ending, or from `--lang en` / `--lang de`. Every sentence
is synthesized in that language, so the English guide gets English pronunciation.

## Read-along text

Every guide MP3 carries its text with sentence timings, which the Hörplayer shows with the spoken sentence
highlighted: one ID3 `SYLT` frame (UTF-16, `deu` or `eng`, millisecond timestamps, type lyrics) with one entry per
spoken sentence — the sentence as written, a leading line break on the first sentence of each paragraph, and
`# Title — Subtitle` for headings (at the same time as their `CHAP`).

To add or refresh the title, chapters and text of an existing MP3 without re-synthesizing (the audio stays
byte-for-byte the same; it refuses and changes nothing if a clip is missing from the cache or the text no longer
matches the audio):

```
python -m guideaudio phase1_guide_de.txt --retag
```

## Guide format

- Plain UTF-8 text. The first line is the title, ending with a period.
- An empty line starts a new paragraph (1.5 s pause); every sentence gets a 0.6 s pause.
- Chapter headings: `# Atomic structure` in English guides, `# Der Atombau — Atomic structure` in German guides
  (only the German part is spoken; the player shows the English part underneath). One to four words, no period.
- No digits, unit symbols, formulas, brackets, slashes or abbreviations with a period. The full list is in
  `prompt_audio_guide.txt`.

## Even pace

Supertonic speaks short sentences up to 60% faster than long ones ("Teil eins ist die allgemeine Chemie." came out
at 26 characters per second, long sentences at 16.5). `guideaudio/pace.py` measures every clip after synthesis and
re-synthesizes a clip that is too fast with a lower `speed` (up to three attempts, never below Supertonic's minimum
of 0.7). The target and tolerance are in `PaceConfig`. Re-synthesizing short sentences makes synthesis a little slower.

## Settings

`guideaudio/config.py`: pauses, pace, voice per language (`VoiceConfig`, both "M1"), MP3 bitrate, loudness and the check
limits. Changing pauses or the title is free (the track is re-stitched from the cache). Changing a sentence or a
voice re-synthesizes only those clips. The cache lives in `cache/audio`, and MP3s go to `out/`.

## Tests

```
python -m pytest -q
```

The tests use a fake engine and never load the real model.
