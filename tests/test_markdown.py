import re

from guideaudio.markdown import readable, render_markdown
from guideaudio.reader import split_text

ENCYCLOPEDIA_DE = """Bakterien nach Gruppen.

# Die Landkarte — Map

Zuerst kommt die Übersicht.

# Teil eins: Kokken — Part one: Cocci

So erkennst du die Gruppe.

# Staphylococcus aureus — Staphylococcus aureus

Einordnung: Ein Hautbakterium.

Die Tests: Koagulasepositiv, als M R S A resistent.

Warum ist das im Labor wichtig? Im Blut nie eine Verunreinigung.

Kurz gesagt: Goldgelbe Kolonien. Koagulasepositiv.

# Die Enterokokken — Enterococci

Einordnung: Ein Darmbakterium.

Die Tests: Äskulinpositiv.

Kurz gesagt: Verträgt Galle.

# Zusammenfassung Teil eins — Part one summary

Zwei Kokken.
"""


def render(text=ENCYCLOPEDIA_DE, language="de"):
    return render_markdown(split_text(text), language, "encyclopedia_bakterien_de.txt")


def test_voice_spellings_go_back_to_written_form():
    assert readable("Ein M R S A, Antikörper der Klasse I g M, per Maldi-Tof.") == "Ein MRSA, Antikörper der Klasse IgM, per MALDI-TOF."
    assert readable("Gruppe A, B und C") == "Gruppe A, B und C"
    assert readable("Das H B s-Antigen, Anti-H B c und der C T-Wert.") == "Das HBs-Antigen, Anti-HBc und der Ct-Wert."
    assert readable("Die H I V und P C R") == "Die HIV und PCR"
    assert (readable("Das H b A eins c, das h C G, die e G F R, p C O zwei, p O zwei, N T-pro B N P und C K-M B.")
            == "Das HbA1c, das hCG, die eGFR, pCO2, pO2, NT-proBNP und CK-MB.")
    assert (readable("Das H b, H b A, H b F und H b S, die H b-Elektrophorese, das M C H C, B C R-A B L und J A K zwei.")
            == "Das Hb, HbA, HbF und HbS, die Hb-Elektrophorese, das MCHC, BCR-ABL und JAK2.")
    assert (readable("H b A zwei, C D drei, C D dreiunddreißig, C D vierunddreißig und C D-Nummern.")
            == "HbA2, CD3, CD33, CD34 und CD-Nummern.")
    assert (readable("Die a P T T, der v W F, die Anti-X a-Aktivität, t P A, A D A M T S dreizehn und P F vier.")
            == "Die aPTT, der vWF, die Anti-Xa-Aktivität, tPA, ADAMTS13 und PF4.")
    assert (readable("Faktor acht, Faktor zehn a, der Faktor-fünf-Leiden, Faktor dreizehn und Faktor drei.")
            == "Faktor VIII, Faktor Xa, der Faktor-V-Leiden, Faktor XIII und Faktor III.")
    assert (readable("Die Faktoren zwei, sieben, neun und zehn, die Faktoren acht bis zwölf, P A I eins und d R V V T.")
            == "Die Faktoren II, VII, IX und X, die Faktoren VIII bis XII, PAI-1 und dRVVT.")
    assert (readable("Des Faktors zehn a, die Faktoren fünf a und acht a, Faktor acht und Protein C.")
            == "Des Faktors Xa, die Faktoren Va und VIIIa, Faktor VIII und Protein C.")
    assert readable("Die L D H bei Hämolyse und das H b A.") == "Die LDH bei Hämolyse und das HbA."
    assert readable("Der Hemmstoff heißt P A I eins, der Aktivator t P A.") == "Der Hemmstoff heißt PAI-1, der Aktivator tPA."


def test_entry_icon_follows_the_subject_of_the_file():
    text = ENCYCLOPEDIA_DE.replace("Die Tests:", "Probe und Messung:")
    md = render_markdown(split_text(text), "de", "encyclopedia_klinische_chemie_de.txt")

    assert "## 🧪 Staphylococcus aureus" in md and "`01` 🧪 [Staphylococcus aureus]" in md
    assert "#### 🧪 Probe und Messung" in md
    blood = text.replace("Probe und Messung:", "Im Ausstrich:")
    md = render_markdown(split_text(blood), "de", "encyclopedia_haematologie_de.txt")
    assert "## 🩸 Staphylococcus aureus" in md and "#### 🔬 Im Ausstrich" in md
    clot = text.replace("Probe und Messung:", "Wirkweise:")
    md = render_markdown(split_text(clot), "de", "encyclopedia_haemostaseologie_de.txt")
    assert "## 🩹 Staphylococcus aureus" in md and "#### ⚙️ Wirkweise" in md
    assert "## 🔖 Staphylococcus aureus" in render_markdown(split_text(text), "de", "encyclopedia_neu_de.txt")


def test_entries_are_numbered_with_icon_sections_and_boxes():
    md = render()

    assert "`2 Steckbriefe` · `1 Teile` · `5 Kapitel`" in md
    assert "**So ist jeder Steckbrief aufgebaut:** 🧭 Einordnung → 🧪 Die Tests → 🏥" in md
    assert "## 🦠 Staphylococcus aureus" in md and "`Steckbrief 01` · **🟣 Kokken**" in md
    assert "#### 🧪 Die Tests\n\nKoagulasepositiv, als MRSA resistent." in md
    assert "> [!TIP]\n> **🏥 Warum ist das im Labor wichtig?** Im Blut nie eine Verunreinigung." in md
    assert "> [!NOTE]\n> **📌 Kurz gesagt:** Goldgelbe Kolonien. Koagulasepositiv." in md


def test_part_table_register_and_every_link_resolves():
    md = render()

    assert "| `01` | [**Staphylococcus aureus**](#staphylococcus-aureus) | Goldgelbe Kolonien. |" in md
    register = md[md.index("## 🔤 Register A–Z"):]
    assert register.index("Die Enterokokken") < register.index("Staphylococcus aureus")
    assert "### 📝 Zusammenfassung Teil eins" in md
    ids = set(re.findall(r'<a id="([^"]+)"', md))
    links = set(re.findall(r"\]\(#([^)]+)\)", md)) | set(re.findall(r'href="#([^"]+)"', md))
    assert links <= ids


def test_a_plain_guide_has_no_entries_or_register():
    md = render("Grundlagen.\n\n# Der Atombau — Atomic structure\n\nAlles besteht aus Atomen.\n")

    assert "`0 Steckbriefe`" in md
    assert "Register" not in md and "aufgebaut" not in md
    assert "## 🗺️ Der Atombau" in md
