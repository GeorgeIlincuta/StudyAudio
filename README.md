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

Each build also writes the genre (`TCON`): `Leitfaden`, `Geschichte` for an input named `story_*.txt`, or
`Enzyklopädie` for an input named `encyclopedia_*.txt`. The Hörplayer picks the file's icon from it. `--retag`
writes it too.

To add or refresh the title, chapters and text of an existing MP3 without re-synthesizing (the audio stays
byte-for-byte the same; it refuses and changes nothing if a clip is missing from the cache or the text no longer
matches the audio):

```
python -m guideaudio phase1_guide_de.txt --retag
```

## Titles — numbered per category

Every track's player title is `NN · Short title` (two digits, middle dot), numbered in build order within its
phone folder; a new track gets the next number. Pass it with `--title` on every build and `--retag` (the default,
the first line, has no number and keeps the subtitle):

```
python -m guideaudio encyclopedia_viren_de.txt --retag --title "02 · Viren nach Gruppen"
```

- **Leitfaden** (`MTL/Leitfaden/`): 01 · Grundlagen für das medizinische Labor (`phase1_guide_de`) · 02 · Foundations
  for the medical laboratory (`phase1_guide_en`) · 03 · Aufbauwissen für das medizinische Labor (`phase2_guide_de`) ·
  04 · Building on the foundations (`phase2_guide_en`) · 05 · Das diagnostische Labor (`phase3_guide_de`) ·
  06 · The diagnostic laboratory (`phase3_guide_en`). Next: 07.
- **Enzyklopädie** (`MTL/Enzyklopädie/`, inputs `encyclopedia_<slug>_de.txt`): 01 · Bakterien nach Gruppen (`bakterien`) ·
  02 · Viren nach Gruppen (`viren`) · 03 · Pilze und Parasiten (`pilze_parasiten`) · 04 · Klinische Chemie nach Organen
  (`klinische_chemie`) · 05 · Hämatologie (`haematologie`) · 06 · Hämostaseologie (`haemostaseologie`) ·
  07 · Immunologie und Transfusionsmedizin (`immunologie_transfusion`) · 08 · Histologie und Zytologie
  (`histologie_zytologie`) · 09 · Molekularbiologie (`molekularbiologie`) · 10 · Urin, Liquor und Punktate
  (`urin_liquor_punktate`) · 11 · Mikrobiologie-Methoden und Hygiene (`mikrobiologie_methoden_hygiene`) ·
  12 · Qualitätsmanagement im Labor (`qualitaetsmanagement`) · 13 · Klinische Chemie zwei (`klinische_chemie_ii`) ·
  14 · Laborgeräte und Analytik (`laborgeraete_analytik`) · 15 · Krankheitsbilder (`krankheitsbilder`) ·
  16 · Prüfungsfälle (`pruefungsfaelle`). Next: 17.
- **Geschichten** (`MTL/Geschichten/`, shared with GermanAudio): 04 · Andrei lernt die Grundlagen für das Labor
  (`story_grundlagen_phase1_de`); the numbering lives in GermanAudio's CLAUDE.md.

## Guide format

- Plain UTF-8 text. The first line is the title, ending with a period.
- An empty line starts a new paragraph (1.5 s pause); every sentence gets a 0.6 s pause.
- Chapter headings: `# Atomic structure` in English guides, `# Der Atombau — Atomic structure` in German guides
  (only the German part is spoken; the player shows the English part underneath). One to four words, no period.
- No digits, unit symbols, formulas, brackets, slashes or abbreviations with a period. The full list is in
  `prompt_audio_guide.txt`.

## Encyclopedias

An encyclopedia is a guide made of entries: one per item of a topic (one bacterium, one drug), sorted into parts by
a classification, with overview, quick-reference and summary chapters around them. Write it with
`prompt_audio_encyclopedia.txt` and name it `encyclopedia_<topic>_de.txt` or `_en.txt`.

Every entry walks through the same sections, each starting a paragraph with its label and a colon
(`Einordnung: …`, `Die Tests: …`) and ending with `Kurz gesagt: …` (`In short: …` in English). The labels are
not configured: the first chapter whose first paragraph starts with a label sets them, and `--check` warns about
every later entry with other labels or another order. Chapters that start with plain prose are not entries. The
check prints the template it found:

```
42 entries, each with the sections: Einordnung → Mikroskop und Kultur → Die Tests → Die Krankheiten → Resistenz und Therapie → Kurz gesagt
```

`--markdown` writes the same text as a Markdown reference book instead of audio (default `out/<input name>.md`, or
`-o`): a title page, contents grouped by part, an overview table per part, every entry numbered with its section
labels as headings, the practice and summary paragraphs as boxes, and an A–Z register. Spellings made for the voice
go back to their written form ("M R S A" → MRSA). It works for any guide; one without entries just gets no register.

```
python -m guideaudio encyclopedia_bakterien_de.txt --markdown
```

`python -m guideaudio.contents` collects all `encyclopedia_*.md` books in the current folder into one contents file,
`INHALTSVERZEICHNIS.md`: every book with its parts, chapters and the section labels of each entry, all linked to the
book. The books keep the order they were written in (`BOOK_ORDER` in `guideaudio/contents.py`); a new book comes
last until it is added there. Run it again after each new book.

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
