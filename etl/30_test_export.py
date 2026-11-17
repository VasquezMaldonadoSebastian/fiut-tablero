# -*- coding: utf-8 -*-
"""Control del exportador: genera el Excel con y sin filtros y cuadra los totales."""
import sys
from pathlib import Path

import duckdb
from openpyxl import load_workbook

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "app"))
from exportar import excel_bytes  # noqa: E402

con = duckdb.connect(str(BASE / "data" / "fiu_fiut.duckdb"), read_only=True)
gasto = con.execute("SELECT * FROM v_gasto").df()
paso = con.execute("SELECT * FROM v_paso").df()
tax = con.execute("SELECT * FROM taxonomia").df()

casos = {
    "cartera": (gasto, paso, [("Año", [2023, 2024, 2025, 2026]), ("Proyecto", []),
                              ("Centro de costo", []), ("Rubro", [])]),
    "filtrado": (gasto[gasto.anio == 2026], paso[paso.anio == 2026],
                 [("Año", [2026]), ("Proyecto", ["PINC230004"]), ("Centro de costo", []), ("Rubro", [])]),
}

for nombre, (g, p, f) in casos.items():
    data = excel_bytes(g, p, f, tax, "16-11-2026", "v1 · 2026-11-17", "124 proyectos · 112 C.C.")
    dest = BASE / "data" / f"_test_export_{nombre}.xlsx"
    dest.write_bytes(data)
    wb = load_workbook(dest, data_only=True)
    hojas = wb.sheetnames
    res = wb["2 Resumen"]
    vals = {res.cell(r, 1).value: res.cell(r, 2).value for r in range(2, res.max_row + 1)}
    total = vals.get("TOTAL clasificable", 0)
    paso_v = vals.get("Cuentas de paso (no suma)", 0)
    det = wb["5 Detalle"].max_row - 1
    print(f"{nombre}: {len(data)/1024:.0f} KB · {len(hojas)} hojas · detalle {det} filas")
    print(f"   resumen clasificable {total:,.0f} vs dataframe {g['valor'].sum():,.0f} | "
          f"paso {paso_v:,.0f} vs {p['valor'].sum():,.0f}")
    assert abs(total - g["valor"].sum()) < 1, "no cuadra el total clasificable"
    assert abs(paso_v - p["valor"].sum()) < 1, "no cuadra el paso"
    assert det == len(g), "el detalle no tiene una fila por movimiento"
    assert hojas == ["1 Parametros", "2 Resumen", "3 Subitems x año", "4 Items", "5 Detalle",
                     "6 Cuentas de paso", "7 Equivalencia"], hojas
    dest.unlink()

print("export verificado")
