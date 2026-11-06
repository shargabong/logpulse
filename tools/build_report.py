"""Собирает report.pdf из docs/report.md.

Маршрут: Markdown -> HTML -> PDF (xhtml2pdf). Шрифты берутся из Windows.

Запуск: python tools/build_report.py
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import markdown
from xhtml2pdf import pisa

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "docs" / "report.md"
OUT = ROOT / "report.pdf"

# xhtml2pdf разрешает читать файлы только из каталога проекта, поэтому нужные
# шрифты копируем из системного каталога в docs/fonts (в .gitignore).
FONT_SRC = Path("C:/Windows/Fonts")
FONT_FILES = {
    "arial.ttf": "Body",
    "arialbd.ttf": "BodyBold",
    "consola.ttf": "Mono",
}
FONT_DIR = ROOT / "docs" / "fonts"

CSS = """
@font-face { font-family: "Body"; src: url("docs/fonts/arial.ttf"); }
@font-face { font-family: "Body"; font-weight: bold; src: url("docs/fonts/arialbd.ttf"); }
@font-face { font-family: "Mono"; src: url("docs/fonts/consola.ttf"); }
@page { size: A4; margin: 1.6cm 1.6cm 1.8cm 1.6cm; }
body { font-family: "Body"; font-size: 10pt; line-height: 1.35; color: #111111; }
h1 { font-size: 18pt; color: #1b3a5c; }
h2 { font-size: 14pt; color: #1b3a5c; margin-top: 14pt; }
h3 { font-size: 12pt; color: #24486e; }
p { margin: 4pt 0; }
hr { border-top: 0.5pt solid #999999; }
table { width: 100%; font-size: 8.5pt; margin: 6pt 0; }
th, td { border: 0.5pt solid #888888; padding: 3pt; vertical-align: top; }
th { background-color: #eaeaea; }
pre { font-family: "Mono"; font-size: 7.8pt; background-color: #f4f4f4;
      padding: 4pt; border: 0.5pt solid #dddddd; }
code { font-family: "Mono"; font-size: 8.3pt; }
img { max-width: 100%; }
"""


def prepare_fonts() -> None:
    """Скопировать системные шрифты в проект (для встраивания в PDF)."""
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    for name in FONT_FILES:
        src = FONT_SRC / name
        dst = FONT_DIR / name
        if src.exists() and not dst.exists():
            shutil.copyfile(src, dst)


def main() -> None:
    os.chdir(ROOT)  # относительные пути к картинкам считаются от корня проекта
    prepare_fonts()
    text = MD.read_text(encoding="utf-8")
    body = markdown.markdown(
        text, extensions=["tables", "fenced_code", "sane_lists"]
    )
    html = (
        "<html><head><meta charset='utf-8'>"
        f"<style>{CSS}</style></head><body>{body}</body></html>"
    )
    with OUT.open("wb") as handle:
        result = pisa.CreatePDF(html, dest=handle, encoding="utf-8")
    if result.err:
        print("Ошибка сборки PDF:", result.err, file=sys.stderr)
        sys.exit(1)
    print(f"report.pdf готов: {OUT}")


if __name__ == "__main__":
    main()
