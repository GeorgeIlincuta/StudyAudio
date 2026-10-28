from guideaudio.contents import OUTPUT_NAME, main, ordered_books, read_book, render_contents
from guideaudio.markdown import render_markdown
from guideaudio.reader import split_text
from tests.test_markdown import ENCYCLOPEDIA_DE


def write_book(folder, name, text=ENCYCLOPEDIA_DE):
    path = folder / name
    path.write_text(render_markdown(split_text(text), "de", name.replace(".md", ".txt")), encoding="utf-8")
    return path


def test_book_lists_parts_chapters_and_sections_with_links(tmp_path):
    book = read_book(write_book(tmp_path, "encyclopedia_bakterien_de.md"))

    assert book.title == "Bakterien nach Gruppen"
    assert book.stats.startswith("`2 Steckbriefe`")
    links = [node.link for node in book.nodes]
    assert "[🦠 Staphylococcus aureus](encyclopedia_bakterien_de.md#staphylococcus-aureus)" in links
    assert not any("Inhalt" in link or "Register" in link for link in links)
    staph = next(node for node in book.nodes if "Staphylococcus" in node.link)
    assert staph.sections == ["🧭 Einordnung", "🧪 Die Tests"]


def test_contents_numbers_entries_per_book_and_links_every_book(tmp_path):
    write_book(tmp_path, "encyclopedia_bakterien_de.md")
    write_book(tmp_path, "encyclopedia_viren_de.md", ENCYCLOPEDIA_DE.replace("Bakterien nach Gruppen", "Viren"))
    md = render_contents([read_book(path) for path in ordered_books(tmp_path)])

    assert "| `01` | [**Bakterien nach Gruppen**](#buch-01)" in md and "| `02` | [**Viren**](#buch-02)" in md
    assert md.count("- `01` [🦠 Staphylococcus aureus]") == 2
    assert "- `02` [🦠 Die Enterokokken]" in md
    assert "  - 🧭 Einordnung · 🧪 Die Tests" in md
    assert "### [🟣 Teil eins: Kokken](encyclopedia_viren_de.md#teil-eins-kokken)" in md
    assert "\n\n\n" not in md


def test_known_books_keep_their_order_and_new_books_come_last(tmp_path):
    for name in ("encyclopedia_aaa_neu_de.md", "encyclopedia_viren_de.md", "encyclopedia_bakterien_de.md"):
        (tmp_path / name).write_text("", encoding="utf-8")

    assert [p.name for p in ordered_books(tmp_path)] == [
        "encyclopedia_bakterien_de.md", "encyclopedia_viren_de.md", "encyclopedia_aaa_neu_de.md"]


def test_main_writes_the_file_into_the_folder(tmp_path, capsys):
    write_book(tmp_path, "encyclopedia_bakterien_de.md")

    assert main([str(tmp_path)]) == 0
    assert (tmp_path / OUTPUT_NAME).read_text(encoding="utf-8").startswith("# 📚 Gesamtinhalt")
    assert main([str(tmp_path / "leer")]) == 1
