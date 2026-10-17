from guideaudio.check import check_text

GOOD_EN = """Foundations for the lab.

# Atomic structure

Everything is made of atoms. Sodium has eleven protons.
"""

GOOD_DE = """Grundlagen für das Labor.

# Der Atombau — Atomic structure

Alles besteht aus Atomen. Natrium hat elf Protonen.
"""


def errors_for(text, language="en"):
    return check_text(text, language).errors


def test_clean_guides_pass_in_both_languages():
    for text, language in [(GOOD_EN, "en"), (GOOD_DE, "de")]:
        report = check_text(text, language)
        assert report.ok, report.errors
        assert report.warnings == []


def test_counts_chapters_sentences_and_words():
    report = check_text(GOOD_EN, "en")

    assert [(c.title, c.words) for c in report.chapters] == [("Atomic structure", 9)]
    assert report.sentences == 3
    assert report.words == 13


def test_digits_are_an_error_with_their_line():
    errors = errors_for(GOOD_EN + "\nSodium has 11 protons.\n")

    assert errors == ["line 7: digits 1; write numbers as words"]


def test_symbols_and_formulas_are_errors():
    errors = errors_for(GOOD_EN + "\nWater is H₂O at 37 °C (body).\n")

    assert any("unsupported characters" in e and "°" in e and "(" in e and "₂" in e for e in errors)
    assert any("digits 37" in e for e in errors)


def test_german_low_quotes_are_rejected():
    assert any("„" in e for e in errors_for(GOOD_DE + "\n„Hallo“, sagt er.\n", "de"))


def test_abbreviations_are_errors_in_both_languages():
    assert any("'e.g.'" in e for e in errors_for(GOOD_EN + "\nSalts, e.g. sodium chloride.\n"))
    assert any("'z. B.'" in e for e in errors_for(GOOD_DE + "\nSalze, z. B. Kochsalz.\n", "de"))


def test_three_dots_are_an_error():
    assert any("three dots" in e for e in errors_for(GOOD_EN + "\nAnd then... nothing.\n"))


def test_paragraph_must_end_with_sentence_punctuation():
    errors = errors_for(GOOD_EN + "\nThis paragraph has no ending\n")

    assert errors == ["line 7: paragraph does not end with . ! ? or …"]


def test_title_line_must_end_with_a_period_and_must_not_be_a_heading():
    assert "the title on the first line must end with a period" in errors_for("Foundations\n\nText.\n")
    assert "the first line must be the guide's title, not a heading" in errors_for("# Atoms\n\nText.\n")


def test_heading_rules():
    errors = errors_for("Title.\n\n# A heading with far too many words\n\nText.\n\n# Ends with a period.\n\nText.\n")

    assert "line 3: heading has more than 4 words: A heading with far too many words" in errors
    assert "line 7: heading ends with a period" in errors


def test_language_specific_heading_warnings():
    english_with_translation = check_text("Title.\n\n# Atoms — Atome\n\nText.\n", "en")
    german_without_translation = check_text("Titel.\n\n# Der Atombau\n\nText.\n", "de")

    assert english_with_translation.ok and german_without_translation.ok
    assert any("without a translation" in w for w in english_with_translation.warnings)
    assert any("no English translation" in w for w in german_without_translation.warnings)


def test_german_letters_in_an_english_guide_are_a_warning():
    report = check_text(GOOD_EN + "\nThe word is Größe.\n", "en")

    assert report.ok
    assert any("German letters" in w for w in report.warnings)


def test_long_sentences_are_a_warning_not_an_error():
    long_sentence = " ".join(["word"] * 30) + "."
    report = check_text(GOOD_EN + "\n" + long_sentence + "\n", "en")

    assert report.ok
    assert any("long sentence (30 words)" in w for w in report.warnings)


def test_reports_every_problem_in_one_run():
    errors = errors_for(GOOD_EN + "\nOne 1.\n\nTwo 2.\n\nThree 3.\n")

    assert len(errors) == 3
