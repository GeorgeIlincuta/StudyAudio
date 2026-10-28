"""Collect the contents of all Markdown books into one file (INHALTSVERZEICHNIS.md).

    python -m guideaudio.contents

Reads every encyclopedia_*.md written by `--markdown` and lists each book with its parts, chapters and the
section labels of every entry. Every link points to an anchor in the book, so the file works as one index.
"""

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path

# The order the books were written in; a book that is not listed yet comes after them, by file name.
BOOK_ORDER = ["bakterien", "viren", "pilze_parasiten", "klinische_chemie", "haematologie", "haemostaseologie",
              "immunologie_transfusion", "histologie_zytologie", "molekularbiologie", "urin_liquor_punktate",
              "mikrobiologie_methoden_hygiene", "qualitaetsmanagement", "klinische_chemie_ii",
              "laborgeraete_analytik"]
OUTPUT_NAME = "INHALTSVERZEICHNIS.md"
SKIPPED_HEADINGS = ("🗂️ ", "🔤 ")  # the book's own contents and its A–Z register


@dataclass
class Node:
    level: int
    link: str
    sections: list[str] = field(default_factory=list)


@dataclass
class Book:
    name: str
    title: str
    stats: str
    nodes: list[Node]


def book_key(path: Path) -> str:
    return path.name.removeprefix("encyclopedia_").removesuffix("_de.md").removesuffix("_en.md")


def ordered_books(folder: Path) -> list[Path]:
    paths = sorted(folder.glob("encyclopedia_*.md"))
    rank = {key: n for n, key in enumerate(BOOK_ORDER)}
    return sorted(paths, key=lambda p: (rank.get(book_key(p), len(BOOK_ORDER)), p.name))


def read_book(path: Path) -> Book:
    title, stats, anchor, nodes = "", "", None, []
    for line in path.read_text(encoding="utf-8").splitlines():
        if m := re.match(r'<a id="([^"]+)"></a>', line):
            anchor = m.group(1)
        elif not title and line.startswith("# 📚 "):
            title = line.removeprefix("# 📚 ")
        elif not stats and line.startswith("`") and "` · `" in line:
            stats = line
        elif m := re.match(r"(#{1,4}) (.+)", line):
            level, text = len(m.group(1)), m.group(2)
            if level == 4:
                if nodes:
                    nodes[-1].sections.append(text)
            elif not text.startswith(SKIPPED_HEADINGS):
                nodes.append(Node(level, f"[{text}]({path.name}#{anchor})" if anchor else text))
            anchor = None
    return Book(path.name, title, stats, nodes)


def render_contents(books: list[Book]) -> str:
    lines = ["# 📚 Gesamtinhalt der Steckbrief-Bücher", "",
             "Alle Markdown-Bücher mit ihren Teilen, Kapiteln und Abschnitten. Jeder Link öffnet die Stelle im Buch.",
             "", "| Nr. | Buch | Umfang |", "|:--:|---|---|"]
    for n, book in enumerate(books, 1):
        short = book.title.split(":")[0]
        lines.append(f"| `{n:02d}` | [**{short}**](#buch-{n:02d}) · [{book.name}]({book.name}) | {book.stats} |")
    for n, book in enumerate(books, 1):
        short, _, subtitle = book.title.partition(":")
        lines += ["", "---", "", f'<a id="buch-{n:02d}"></a>', "", f"## 📗 {n:02d} · [{short}]({book.name})", ""]
        if subtitle:
            lines += [f"*{subtitle.strip()}*", ""]
        lines += [book.stats, ""]
        entry = 0
        for node in book.nodes:
            if node.level == 1:
                lines += ["", f"### {node.link}", ""]
            elif node.sections:
                entry += 1
                lines += [f"- `{entry:02d}` {node.link}", "  - " + " · ".join(node.sections)]
            else:
                lines.append(f"- {node.link}")
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m guideaudio.contents", description=__doc__.splitlines()[0])
    parser.add_argument("folder", nargs="?", type=Path, default=Path("."),
                        help="the folder with the encyclopedia_*.md books (default: the current folder)")
    parser.add_argument("-o", "--output", type=Path, help=f"output file (default: <folder>/{OUTPUT_NAME})")
    args = parser.parse_args(argv)
    books = [read_book(path) for path in ordered_books(args.folder)]
    if not books:
        print(f"no encyclopedia_*.md books in {args.folder}")
        return 1
    output = args.output or args.folder / OUTPUT_NAME
    output.write_text(render_contents(books), encoding="utf-8")
    print(f"done: {output} ({len(books)} books, {sum(len(b.nodes) for b in books)} headings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
