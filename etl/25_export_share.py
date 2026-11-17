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
SELECT m.cc, cp.proyecto, cp.proyecto_nombre, m.anio, m.mes, m.cod_tipmov, m.des_tipmov,
       m.cod_sitm, m.des_item, m.veredicto, m.rubro, m.subitem, m.etiqueta, m.cubeta_ingreso,
       count(*) AS movimientos,
       sum(m.valor) AS valor, sum(m.comprometido) AS comprometido, sum(m.pagado) AS pagado
FROM org.movimientos m
LEFT JOIN org.cc_proyecto cp ON m.cc = cp.cc AND cp.rn = 1
GROUP BY ALL
""")

# detalle por movimiento: sin RUT, sin número de documento, con glosa saneada
dst.execute(r"""
CREATE TABLE mov_detalle AS
SELECT m.cc, cp.proyecto, m.fecha, m.anio, m.mes, m.cod_tipmov, m.des_tipmov,
       m.cod_sitm, m.des_item, m.veredicto, m.rubro, m.subitem, m.etiqueta, m.cubeta_ingreso,
       m.valor,
       regexp_replace(
         regexp_replace(
           regexp_replace(coalesce(m.glosa,''), '\b\d{1,2}\.\d{3}\.\d{3}-[\dkK]\b', 'RUT', 'g'),
           '\b\d{3,8}-[\dkK]\b', 'RUT', 'g'),
         '[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+', 'correo', 'g') AS glosa
FROM org.movimientos m
LEFT JOIN org.cc_proyecto cp ON m.cc = cp.cc AND cp.rn = 1
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
WHERE m.cod_tipmov BETWEEN 20 AND 25
""")
dst.execute("CREATE VIEW v_gasto AS SELECT * FROM v_egreso WHERE veredicto = 'gasto'")
dst.execute("CREATE VIEW v_paso AS SELECT * FROM v_egreso WHERE veredicto = 'paso'")
dst.execute("CREATE VIEW v_ingreso AS SELECT * FROM movimientos WHERE cod_tipmov BETWEEN 10 AND 15")
dst.execute("CREATE TABLE dim_proyecto AS SELECT * FROM proyectos")
dst.execute("""
CREATE TABLE meta AS
SELECT 'filas_paquete' AS clave, (SELECT count(*)::VARCHAR FROM org.proyectos) AS valor
UNION ALL SELECT 'modo', 'share'
UNION ALL SELECT 'corte', '16-11-2026'
""")

for t in ("proyectos", "movimientos", "mov_detalle", "v_gasto", "v_paso", "v_ingreso", "declarado",
          "presupuesto_anid", "taxonomia"):
    n = dst.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"{t}: {n:,}")

g = dst.execute("SELECT sum(valor) FROM v_gasto").fetchone()[0]
p = dst.execute("SELECT sum(valor) FROM v_paso").fetchone()[0]
i = dst.execute("SELECT sum(valor) FROM v_ingreso").fetchone()[0]
print(f"gasto {g/1e6:,.1f} MM · paso {p/1e6:,.1f} MM · ingresos {i/1e6:,.1f} MM")
dst.close()

print(f"{DEST.name}: {DEST.stat().st_size/1024/1024:.2f} MB")
