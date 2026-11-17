# -*- coding: utf-8 -*-
"""Imprime un .md institucional a PDF con identidad UFRO (Chrome/Edge headless)."""
import html
import os
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
LOGO = Path(r"C:/Users/Luz/Desktop/05_Herramientas/Recursos/Identidad UFRO/01-logo-UFRO-azul-horizontal.png")

DOCS = [
    (BASE.parent / "04_Entregables" / "INFORME_TABLERO_FIUT_2026-11-17.md",
     BASE.parent / "04_Entregables" / "INFORME_TABLERO_FIUT_2026-11-17.pdf"),
]

BROWSERS = [
    r"C:/Program Files/Google/Chrome/Application/chrome.exe",
    r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    r"C:/Program Files/Microsoft/Edge/Application/msedge.exe",
]

CSS = """
:root{--azul:#005092;--tinta:#2B3A4A;--gris:#6B7887;--linea:#DCE3EA;--perla:#ECEFF4;
      --arena:#E8C5B0;--hielo:#F7F9FC;--salvia:#B8D4CE;}
*{box-sizing:border-box}
@page{size:A4;margin:20mm 17mm 16mm}
body{font-family:"Segoe UI",Tahoma,sans-serif;color:var(--tinta);font-size:10.2pt;line-height:1.55;
     margin:0;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.cab{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:6mm;
     padding-bottom:3mm;border-bottom:2px solid var(--azul)}
.cab img{height:11mm;width:auto}
.cab .meta{font-size:8pt;color:var(--gris);text-align:right;line-height:1.6}
h1{font-size:19pt;line-height:1.2;color:var(--azul);margin:0 0 2mm;letter-spacing:-.01em;font-weight:700}
h1::after{content:"";display:block;width:38mm;height:2.2mm;background:var(--arena);margin-top:3.5mm;border-radius:1mm}
h2{font-size:12.4pt;color:var(--azul);margin:8mm 0 2mm;padding-bottom:1.4mm;
   border-bottom:1px solid var(--linea);page-break-after:avoid;font-weight:650}
h3{font-size:10.8pt;color:var(--azul);margin:5mm 0 1.4mm;page-break-after:avoid;font-weight:650}
p{margin:0 0 2.4mm}
ul,ol{margin:0 0 2.6mm;padding-left:6mm}
li{margin-bottom:1.3mm}
strong{color:#12395E}
table{border-collapse:collapse;width:100%;margin:3mm 0 4mm;font-size:8.7pt;page-break-inside:avoid}
th,td{border:1px solid var(--linea);padding:1.7mm 2.2mm;text-align:left;vertical-align:top}
th{background:var(--perla);font-weight:700;color:#1B3A56}
tr:nth-child(even) td{background:var(--hielo)}
table.num td:last-child{text-align:right}
table.num th:last-child{text-align:right}
code{font-family:Consolas,monospace;font-size:8.7pt;background:var(--hielo);
     border:1px solid var(--linea);padding:.2mm 1mm;border-radius:1mm;color:#1B3A56}
hr{border:none;border-top:1px solid var(--linea);margin:6mm 0}
.foot{margin-top:7mm;padding-top:2.5mm;border-top:1px solid var(--linea);font-size:7.6pt;color:var(--gris);
      display:flex;justify-content:space-between;gap:8mm}
"""


def find_browser() -> str:
    for c in BROWSERS:
        if Path(c).exists():
            return c
    sys.exit("No se encontró Chrome ni Edge para imprimir.")


def _marcar_tablas_numericas(html_txt: str) -> str:
    """Marca las tablas cuya última columna es de montos para alinearla a la derecha."""
    import re

    def revisar(m):
        tabla = m.group(0)
        celdas = re.findall(r"<tr>.*?</tr>", tabla, flags=re.S)
        vals = []
        for fila in celdas[1:]:
            tds = re.findall(r"<td[^>]*>(.*?)</td>", fila, flags=re.S)
            if tds:
                vals.append(re.sub(r"<[^>]+>", "", tds[-1]).strip())
        num = sum(1 for v in vals if re.fullmatch(r"\$?[\d.]+(,\d+)? ?%?", v))
        if vals and num / len(vals) >= 0.95:
            return tabla.replace("<table>", '<table class="num">', 1)
        return tabla

    return re.sub(r"<table>.*?</table>", revisar, html_txt, flags=re.S)


def md_a_html(md_text: str, origen: str) -> str:
    import markdown
    cuerpo = markdown.markdown(md_text, extensions=["tables", "fenced_code", "sane_lists"],
                               output_format="html5")
    cuerpo = _marcar_tablas_numericas(cuerpo)
    cab = (f'<div class="cab"><img src="{LOGO.as_uri()}" alt="UFRO">'
           f'<div class="meta">Universidad de La Frontera<br>Dirección de Innovación y '
           f'Transferencia Tecnológica</div></div>')
    pie = (f'<div class="foot"><span>Documento fuente: <code>{html.escape(origen)}</code></span>'
           f'<span>Generado con scripts/md_a_pdf_fiut.py · 17-11-2026</span></div>')
    return ("<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'>"
            f"<title>{html.escape(origen)}</title><style>{CSS}</style></head><body>"
            f"{cab}{cuerpo}{pie}</body></html>")


def imprimir(browser: str, h: Path, pdf: Path) -> None:
    perfil = Path(tempfile.gettempdir()) / f"pdf-fiut-{os.getpid()}"
    r = subprocess.run([browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        f"--user-data-dir={perfil.as_posix()}", "--virtual-time-budget=5000",
                        f"--print-to-pdf={pdf.as_posix()}", h.as_uri()],
                       capture_output=True, text=True)
    if not pdf.exists() or pdf.stat().st_size == 0:
        sys.exit(f"El PDF no se generó: {pdf}\n{r.stderr[-600:]}")


def main() -> None:
    browser = find_browser()
    tmp = Path(tempfile.mkdtemp(prefix="md-fiut-"))
    for src, pdf in DOCS:
        h = tmp / (src.stem + ".html")
        h.write_text(md_a_html(src.read_text(encoding="utf-8"), src.name), encoding="utf-8")
        if pdf.exists():
            pdf.unlink()
        imprimir(browser, h, pdf)
        print(f"OK {pdf.name} · {pdf.stat().st_size/1024:.0f} KB")


if __name__ == "__main__":
    main()
