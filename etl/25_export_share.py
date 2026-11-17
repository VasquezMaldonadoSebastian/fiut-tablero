# -*- coding: utf-8 -*-
"""Genera la base 'share' para Streamlit Cloud: agregada, sin RUT, folios ni glosas.

Se publica en el repo (data/share/) y es la que usa la app cuando no existe la base completa.
"""
from pathlib import Path

import duckdb

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "data" / "fiu_fiut.duckdb"
DEST_DIR = BASE / "data" / "share"
DEST = DEST_DIR / "fiu_fiut_share.duckdb"
DEST_DIR.mkdir(parents=True, exist_ok=True)
if DEST.exists():
    DEST.unlink()

dst = duckdb.connect(str(DEST))
dst.execute(f"ATTACH '{SRC.as_posix()}' AS org (READ_ONLY)")

# proyectos: sin investigador (dato personal)
dst.execute("""
CREATE TABLE proyectos AS
SELECT codigo, nombre, tipo, ambito, financiador, concurso, facultad, inicio, termino,
       adjudicado, remesa_2025, remesado_total, cc
FROM org.dim_proyecto
""")

dst.execute("CREATE TABLE taxonomia AS SELECT * FROM org.taxonomia")

# movimientos agregados: una fila por C.C. x mes x ítem, sin documento ni proveedor
dst.execute("""
CREATE TABLE movimientos AS
SELECT cc, proyecto, proyecto_nombre, financiador_proyecto, anio, mes, cod_tipmov,
       des_tipmov, cod_sitm, des_item, veredicto, rubro, subitem, etiqueta,
       count(*) AS movimientos,
       sum(valor) AS valor, sum(comprometido) AS comprometido, sum(pagado) AS pagado
FROM org.v_egreso
GROUP BY ALL
""")

dst.execute("""
CREATE TABLE declarado AS
SELECT proyecto, anio, periodo, item, subitem, tipo_documento, inst_financiera, universo,
       count(*) AS lineas, sum(monto_num) AS monto
FROM org.declarado
GROUP BY ALL
""")

dst.execute("""
CREATE TABLE presupuesto_anid AS
SELECT proyecto, item, inst_financiera, corte_anid, presupuesto_actual, real_gastado,
       saldo_disponible
FROM org.presupuesto_anid
""")

# vistas equivalentes a las de la base completa, para que la app no cambie de SQL
dst.execute("""
CREATE VIEW v_egreso AS
SELECT m.*, p.inicio, p.termino, p.adjudicado
FROM movimientos m LEFT JOIN proyectos p USING (codigo)
""") if False else None

dst.execute("""
CREATE VIEW v_egreso AS
SELECT m.*, p.inicio, p.termino, p.adjudicado
FROM movimientos m LEFT JOIN proyectos p ON m.proyecto = p.codigo
""")
dst.execute("CREATE VIEW v_gasto AS SELECT * FROM v_egreso WHERE veredicto = 'gasto'")
dst.execute("CREATE VIEW v_paso AS SELECT * FROM v_egreso WHERE veredicto = 'paso'")
dst.execute("CREATE TABLE dim_proyecto AS SELECT * FROM proyectos")
dst.execute("""
CREATE TABLE meta AS
SELECT 'filas_paquete' AS clave, (SELECT count(*)::VARCHAR FROM org.proyectos) AS valor
UNION ALL SELECT 'modo', 'share'
UNION ALL SELECT 'corte', '16-11-2026'
""")

for t in ("proyectos", "movimientos", "declarado", "presupuesto_anid", "taxonomia"):
    n = dst.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    print(f"{t}: {n:,}")
dst.close()

print(f"{DEST.name}: {DEST.stat().st_size/1024/1024:.2f} MB")
