# -*- coding: utf-8 -*-
"""Controles de cierre del tablero. Falla con excepción si algo no cuadra."""
from pathlib import Path

import duckdb

BASE = Path(__file__).resolve().parent.parent
con = duckdb.connect(str(BASE / "data" / "fiu_fiut.duckdb"), read_only=True)

ok = []

def check(nombre, cond, detalle=""):
    ok.append(cond)
    print(("OK  " if cond else "FALLA ") + nombre + (f" · {detalle}" if detalle else ""))

gasto, paso, bruto = con.execute("""
SELECT (SELECT sum(valor) FROM v_gasto), (SELECT sum(valor) FROM v_paso),
       (SELECT sum(valor) FROM movimientos WHERE cod_tipmov BETWEEN 20 AND 25)
""").fetchone()

check("gasto + paso = bruto del libro", abs(gasto + paso - bruto) < 1,
      f"{gasto+paso:,.0f} vs {bruto:,.0f}")

sin = con.execute("SELECT count(*) FROM v_egreso WHERE veredicto = 'sin_clasificar'").fetchone()[0]
check("todo egreso clasificado", sin == 0, f"{sin} sin clasificar")

n_cc = con.execute("SELECT count(DISTINCT cc) FROM movimientos").fetchone()[0]
check("112 centro de costo con movimientos", n_cc == 112, f"{n_cc} C.C.")

n_proy = con.execute("SELECT count(*) FROM proyectos").fetchone()[0]
check("124 filas de proyecto", n_proy == 124, f"{n_proy} filas")

huerf = con.execute("SELECT count(*) FROM v_egreso WHERE proyecto IS NULL").fetchone()[0]
check("sin movimientos huérfanos de proyecto", huerf == 0, f"{huerf} filas")

d_proy, d_monto, d_lineas = con.execute(
    "SELECT count(DISTINCT proyecto), sum(monto_num), count(*) FROM declarado").fetchone()
check("declarado: 61 proyectos con cartola", d_proy == 61, f"{d_proy} proyectos · {d_lineas} líneas")

piv = con.execute("""
SELECT count(*) FROM (
  SELECT rubro, subitem, sum(valor) s FROM v_gasto GROUP BY 1,2 HAVING s < 0)
""").fetchone()[0]
check("sin subítems con monto negativo", piv == 0, f"{piv} casos")

print("\ndimensiones:")
for r in con.execute("SELECT rubro, count(*), round(sum(valor)/1e6,1) FROM v_gasto GROUP BY 1 ORDER BY 3 DESC").fetchall():
    print(f"  {r[0]:<32} {r[1]:>6} movs   ${r[2]:>9,.1f} MM")

print(f"\ndeclarado: ${d_monto/1e6:,.1f} MM en {d_lineas:,} líneas de {d_proy} proyectos")
print("\nRESULTADO:", "todos los controles en verde" if all(ok) else "HAY FALLAS")
