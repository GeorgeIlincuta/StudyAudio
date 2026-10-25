from guideaudio.check import check_text
from guideaudio.encyclopedia import check_entries
from guideaudio.reader import split_text

ENCYCLOPEDIA_DE = """Bakterien nach Gruppen.

# Die Landkarte — Map

Zuerst kommt die Übersicht. Kurz gesagt: Das ist kein Eintrag.

# Escherichia coli — Escherichia coli

Einordnung: Ein Darmbakterium.

Die Tests: Oxidasenegativ.

Es ist auch indolpositiv.

Kurz gesagt: Häufig im Urin.

# Klebsiella — Klebsiella

Einordnung: Ein Bakterium mit Kapsel.

Die Tests: Indolnegativ.

Kurz gesagt: Schleimige Kolonien.

# Zusammenfassung — Summary

Kurz gesagt: Zwei Bakterien.
"""


def entries_for(text, language="de"):
    return check_entries(split_text(text), language)


def test_the_first_entry_sets_the_sections_and_plain_chapters_are_not_entries():
    report = entries_for(ENCYCLOPEDIA_DE)

    assert report.sections == ["Einordnung", "Die Tests", "Kurz gesagt"]
    assert report.entries == ["Escherichia coli", "Klebsiella"]
    assert report.warnings == []


def test_an_entry_with_other_sections_is_a_warning():
    uneven = ENCYCLOPEDIA_DE.replace("Die Tests: Indolnegativ.", "Die Krankheiten: Lungenentzündung.")

    warnings = entries_for(uneven).warnings

    assert warnings == [
        "line 17: entry 'Klebsiella' has the sections Einordnung → Die Krankheiten → Kurz gesagt; "
        "the first entry set Einordnung → Die Tests → Kurz gesagt"
    ]


def test_the_first_entry_must_end_with_the_summary():
    report = entries_for("Titel.\n\n# Eintrag — Entry\n\nEinordnung: Ein Bakterium.\n", "de")

    assert report.warnings == ["line 3: entry 'Eintrag' does not end with a 'Kurz gesagt' section"]


def test_english_summary_label_and_no_entries_warning():
    english = "Bacteria.\n\n# E coli\n\nOverview: A gut bacterium.\n\nIn short: Common in urine.\n"

    assert entries_for(english, "en").sections == ["Overview", "In short"]
    assert any("no entries found" in w for w in entries_for("Title.\n\n# Atoms\n\nPlain text.\n", "en").warnings)


def test_check_text_runs_the_entry_check_only_for_an_encyclopedia():
    uneven = ENCYCLOPEDIA_DE.replace("Die Tests: Indolnegativ.", "Die Krankheiten: Lungenentzündung.")

    guide = check_text(uneven, "de")
    encyclopedia = check_text(uneven, "de", encyclopedia=True)

    assert guide.warnings == [] and guide.sections == []
    assert encyclopedia.ok
    assert encyclopedia.entries == ["Escherichia coli", "Klebsiella"]
    assert any("entry 'Klebsiella'" in w for w in encyclopedia.warnings)
