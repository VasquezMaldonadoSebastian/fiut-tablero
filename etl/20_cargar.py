# -*- coding: utf-8 -*-
"""Construye el archivo DuckDB del tablero FIUT a partir de data/raw + taxonomía."""
import duckdb
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"
DB = BASE / "data" / "fiu_fiut.duckdb"

def csv(p):
    return f"read_csv_auto('{(RAW / p).as_posix()}', delim=';', header=true, all_varchar=false)"

con = duckdb.connect(str(DB))
con.execute("INSTALL excel; LOAD excel;") if False else None

con.execute("DROP TABLE IF EXISTS proyectos")
con.execute(f"""
CREATE TABLE proyectos AS
SELECT codigo, nombre, tipo, ambito, financiador, concurso, facultad,
       TRY_CAST(NULLIF(inicio,'') AS DATE) AS inicio, TRY_CAST(NULLIF(termino,'') AS DATE) AS termino,
       investigador, TRY_CAST(adjudicado AS DOUBLE) AS adjudicado,
       TRY_CAST(remesa_2025 AS DOUBLE) AS remesa_2025, TRY_CAST(remesado_total AS DOUBLE) AS remesado_total,
       cc_raw, cc
FROM read_csv_auto('{(RAW/'proyectos.csv').as_posix()}', delim=';', header=true, all_varchar=true)
""")

con.execute("DROP TABLE IF EXISTS taxonomia")
con.execute(f"CREATE TABLE taxonomia AS SELECT * FROM read_csv_auto('{(BASE/'data'/'taxonomia_item.csv').as_posix()}', delim=';', header=true, encoding='utf-8')")

con.execute("DROP TABLE IF EXISTS dim_item")
con.execute(f"CREATE TABLE dim_item AS SELECT cod_sitm, des_item, des_glosa, cod_cuenta FROM {csv('dim_item.csv')}")

con.execute("DROP TABLE IF EXISTS dim_tipo_mov")
con.execute(f"CREATE TABLE dim_tipo_mov AS SELECT * FROM {csv('dim_tipo_mov.csv')}")

con.execute("DROP TABLE IF EXISTS movimientos")
con.execute(f"""
CREATE TABLE movimientos AS
SELECT m.cc, m.cc_raw, CAST(m.numero AS INTEGER) AS numero, CAST(m.num_linea AS INTEGER) AS num_linea,
       CAST(m.fecha AS DATE) AS fecha,
       CAST(year(CAST(m.fecha AS DATE)) AS INTEGER) AS anio,
       CAST(month(CAST(m.fecha AS DATE)) AS INTEGER) AS mes,
       m.cod_sitm, CAST(m.cod_tipmov AS INTEGER) AS cod_tipmov, CAST(m.valor AS DOUBLE) AS valor,
       m.rut_prov, m.glosa, m.glosa_doc, m.num_oc,
       t.des_tipmov, t.deve, t.perc, t.comp, t.pago,
       m.valor * t.deve AS devengado, m.valor * t.perc AS percibido,
       m.valor * t.comp AS comprometido, m.valor * t.pago AS pagado,
       CASE
         WHEN m.cod_sitm IN ('21549','21538','21501','21550','21527','25501') THEN 'Remesa'
         WHEN m.cod_sitm = '29901' THEN 'Saldo de arrastre'
         WHEN m.cod_sitm = '25503' THEN 'Otros ingresos'
         WHEN m.cod_sitm IN ('21301','21308','21309') THEN 'Transferencias internas'
         WHEN m.cod_sitm IN ('10308','10314','25300') THEN 'Devoluciones y ajustes'
         ELSE 'Otros'
       END AS cubeta_ingreso,
       COALESCE(tx.veredicto, 'sin_clasificar') AS veredicto,
       COALESCE(tx.rubro, 'Sin clasificar') AS rubro,
       COALESCE(tx.subitem, '') AS subitem,
       COALESCE(tx.etiqueta, '') AS etiqueta,
       i.des_item
FROM read_csv_auto('{(RAW/'movimientos.csv').as_posix()}', delim=';', header=true) m
LEFT JOIN dim_tipo_mov t ON CAST(m.cod_tipmov AS INTEGER) = t.cod_tipmov
LEFT JOIN taxonomia tx ON m.cod_sitm = tx.cod_sitm
LEFT JOIN dim_item i ON m.cod_sitm = i.cod_sitm
""")

# --- correcciones de centro de costo acordadas (no se edita el paquete) ---
con.execute("DROP TABLE IF EXISTS cc_corregido")
con.execute(f"""CREATE TABLE cc_corregido AS
SELECT * FROM read_csv_auto('{(BASE/'data'/'correcciones_cc.csv').as_posix()}', delim=';', header=true, all_varchar=true)""")
con.execute("""
UPDATE proyectos p SET cc = c.cc, cc_raw = p.cc_raw || ' -> ' || c.cc
FROM cc_corregido c WHERE upper(p.codigo) = upper(c.codigo)
""")

con.execute("DROP TABLE IF EXISTS dim_proyecto")
con.execute("""
CREATE TABLE dim_proyecto AS
SELECT DISTINCT ON (codigo) *
FROM proyectos ORDER BY codigo, (cc <> '') DESC, adjudicado DESC NULLS LAST
""")

con.execute("DROP TABLE IF EXISTS cc_proyecto")
con.execute("""
CREATE TABLE cc_proyecto AS
SELECT cc, codigo AS proyecto, nombre AS proyecto_nombre, financiador,
       row_number() OVER (PARTITION BY cc ORDER BY adjudicado DESC) AS rn
FROM proyectos WHERE cc IS NOT NULL AND cc <> ''
""")

con.execute("DROP TABLE IF EXISTS declarado")
con.execute(f"""
CREATE TABLE declarado AS
SELECT * FROM read_csv_auto('{(RAW/'declarado.csv').as_posix()}', delim=';', header=true,
                            encoding='latin-1', all_varchar=true)
""")
con.execute("ALTER TABLE declarado ALTER COLUMN monto_num TYPE DOUBLE USING CAST(replace(monto_num, ',', '.') AS DOUBLE)")
con.execute("ALTER TABLE declarado ALTER COLUMN anio TYPE INTEGER USING CAST(anio AS INTEGER)")

con.execute("DROP TABLE IF EXISTS presupuesto_anid")
con.execute(f"CREATE TABLE presupuesto_anid AS SELECT * FROM read_csv_auto('{(RAW/'presupuesto_anid.csv').as_posix()}', delim=';', header=true, encoding='latin-1', all_varchar=true)")
for c in ("presupuesto_actual", "real_gastado", "saldo_disponible", "nuevo_presupuesto"):
    con.execute(f"ALTER TABLE presupuesto_anid ALTER COLUMN {c} TYPE DOUBLE USING CAST(replace({c}, ',', '.') AS DOUBLE)")

# ---------------- vistas de trabajo ----------------
con.execute("""
CREATE OR REPLACE VIEW v_egreso AS
SELECT m.*, cp.proyecto, cp.proyecto_nombre, p.financiador AS financiador_proyecto,
       p.inicio, p.termino, p.adjudicado
FROM movimientos m
LEFT JOIN cc_proyecto cp ON m.cc = cp.cc AND cp.rn = 1
LEFT JOIN dim_proyecto p ON cp.proyecto = p.codigo
WHERE m.cod_tipmov BETWEEN 20 AND 25
""")

con.execute("""
CREATE OR REPLACE VIEW v_ingreso AS
SELECT m.*, cp.proyecto, cp.proyecto_nombre
FROM movimientos m
LEFT JOIN cc_proyecto cp ON m.cc = cp.cc AND cp.rn = 1
WHERE m.cod_tipmov BETWEEN 10 AND 15
""")

con.execute("""
CREATE OR REPLACE VIEW v_gasto AS
SELECT * FROM v_egreso WHERE veredicto = 'gasto'
""")

con.execute("""
CREATE OR REPLACE VIEW v_paso AS
SELECT * FROM v_egreso WHERE veredicto = 'paso'
""")

for t in ("proyectos", "movimientos", "v_gasto", "v_paso", "v_ingreso", "declarado", "presupuesto_anid"):
    n = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    print(f"{t}: {n:,}")

print("gasto clasificable:", f"{con.execute('SELECT round(sum(valor))/1e6 FROM v_gasto').fetchone()[0]:,.1f} MM")
print("cuentas de paso:", f"{con.execute('SELECT round(sum(valor))/1e6 FROM v_paso').fetchone()[0]:,.1f} MM")
print("sin clasificar:", con.execute("SELECT count(*) FROM v_egreso WHERE veredicto='sin_clasificar'").fetchone()[0])
