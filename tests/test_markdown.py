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
    assert (readable("Das A B null-System, Blutgruppe null, Anti-d s D N A, Anti-C C P, C drei, C vier und C eins-Esterase.")
            == "Das AB0-System, Blutgruppe 0, Anti-dsDNA, Anti-CCP, C3, C4 und C1-Esterase.")
    assert (readable("H E p-zwei-Zellen, C drei d, P R drei, Scl-siebzig und H L A-D Q zwei oder D Q acht.")
            == "HEp-2-Zellen, C3d, PR3, Scl-70 und HLA-DQ2 oder DQ8.")
    assert (readable("Anti-S m und S S-A, H L A-B siebenundzwanzig, C D achtunddreißig und C D acht.")
            == "Anti-Sm und SS-A, HLA-B27, CD38 und CD8.")
    assert (readable("Anti-F y a, F y b, J k a und J k b, die Gruppen A eins und A zwei und H L A-A zwei.")
            == "Anti-Fya, Fyb, Jka und Jkb, die Gruppen A1 und A2 und HLA-A2.")
    assert readable("Die C D vier-Zellen, I g D und Gruppe A.") == "Die CD4-Zellen, IgD und Gruppe A."
    assert readable("Der Hemmstoff heißt P A I eins, der Aktivator t P A.") == "Der Hemmstoff heißt PAI-1, der Aktivator tPA."
    assert (readable("Die H E-Färbung, H E R zwei, K i siebenundsechzig, C K sieben, C K zwanzig, P D L eins und S hundert.")
            == "Die HE-Färbung, HER2, Ki-67, CK7, CK20, PD-L1 und S100.")
    assert readable("T T F eins, C I N eins bis C I N drei und C I N.") == "TTF-1, CIN1 bis CIN3 und CIN."
    assert (readable("Die m R N A, t R N A, r R N A, c D N A, c f D N A, c t D N A und die q P C R.")
            == "Die mRNA, tRNA, rRNA, cDNA, cfDNA, ctDNA und die qPCR.")
    assert (readable("H F E C zweihundertzweiundachtzig Y, Prothrombin G zwanzigtausendzweihundertzehn A, J A K zwei V sechshundertsiebzehn F.")
            == "HFE C282Y, Prothrombin G20210A, JAK2 V617F.")
    assert (readable("B C R-A B L eins, M R drei, M R vier, C Y P zwei D sechs, m e c A, v a n A, sechzehn S r R N A und S A R S-CoV-zwei.")
            == "BCR-ABL1, MR3, MR4, CYP2D6, mecA, vanA, 16S rRNA und SARS-CoV-2.")
    assert (readable("R Nasen, R Nase-frei, R fünfhundertsechs Q, H dreiundsechzig D, E G F R T siebenhundertneunzig M und H L A-B siebenundfünfzig null eins.")
            == "RNasen, RNase-frei, R506Q, H63D, EGFR T790M und HLA-B*57:01.")
    assert (readable("Pap null, Pap eins, Pap drei D eins, Pap drei D zwei, Pap vier a, Pap vier b und Pap fünf.")
            == "Pap 0, Pap I, Pap IIID1, Pap IIID2, Pap IVa, Pap IVb und Pap V.")
    assert (readable("Das Stadium p T zwei N eins M null, T eins a, Grad G drei, R null und Gruppe A.")
            == "Das Stadium pT2 N1 M0, T1a, Grad G3, R0 und Gruppe A.")
    assert (readable("Das freie T vier, Influenza H eins N eins oder H drei N zwei, N null und M eins.")
            == "Das freie T4, Influenza H eins N eins oder H drei N zwei, N0 und M1.")
    assert (readable("Ein S G L T-zwei-Hemmer, die Rili-B Ä K mit Teil B eins und Teil B zwei, das Protein vierzehn drei drei.")
            == "Ein SGLT2-Hemmer, die Rili-BÄK mit Teil B1 und Teil B2, das Protein 14-3-3.")
    assert readable("Ein drei M R G N und ein vier M R G N.") == "Ein 3MRGN und ein 4MRGN."
    assert (readable("Die I S O fünfzehntausendeinhundertneunundachtzig, die I S O neuntausendeins, die D Akk S und Teil B drei bis Teil B fünf.")
            == "Die ISO 15189, die ISO 9001, die DAkkS und Teil B3 bis Teil B5.")
    assert (readable("Die Eins-zwei-s-Regel, die Eins-drei-s-Regel, die Zwei-zwei-s-Regel, die R-vier-s-Regel, die Vier-eins-s-Regel und die Zehn-x-Regel.")
            == "Die 1-2s-Regel, die 1-3s-Regel, die 2-2s-Regel, die R-4s-Regel, die 4-1s-Regel und die 10x-Regel.")


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
    immune = text.replace("Probe und Messung:", "Der Befund:")
    md = render_markdown(split_text(immune), "de", "encyclopedia_immunologie_transfusion_de.txt")
    assert "## 🛡️ Staphylococcus aureus" in md and "#### 📋 Der Befund" in md
    tissue = text.replace("Probe und Messung:", "Im Präparat:")
    md = render_markdown(split_text(tissue), "de", "encyclopedia_histologie_zytologie_de.txt")
    assert "## 🔬 Staphylococcus aureus" in md and "#### 🔬 Im Präparat" in md
    dna = text.replace("Probe und Messung:", "Das Ergebnis:")
    md = render_markdown(split_text(dna), "de", "encyclopedia_molekularbiologie_de.txt")
    assert "## 🧬 Staphylococcus aureus" in md and "#### 📈 Das Ergebnis" in md
    fluid = text.replace("Probe und Messung:", "Entstehung:")
    md = render_markdown(split_text(fluid), "de", "encyclopedia_urin_liquor_punktate_de.txt")
    assert "## 💧 Staphylococcus aureus" in md and "#### 🌱 Entstehung" in md
    microbes = text.replace("Probe und Messung:", "Praxis:")
    md = render_markdown(split_text(microbes), "de", "encyclopedia_mikrobiologie_methoden_hygiene_de.txt")
    assert "## 🧫 Staphylococcus aureus" in md and "#### 🛠️ Praxis" in md
    quality = text.replace("Probe und Messung:", "Die Vorgabe:")
    md = render_markdown(split_text(quality), "de", "encyclopedia_qualitaetsmanagement_de.txt")
    assert "## 📋 Staphylococcus aureus" in md and "#### 📏 Die Vorgabe" in md
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
