# -*- coding: utf-8 -*-
"""Extrae las fuentes del tablero FIUT a CSV (solo lectura sobre fin21_local)."""
import csv
import os
import re
import subprocess
from pathlib import Path

HOME = Path.home()
PSQL = r"C:\Program Files\PostgreSQL\16\bin\psql.exe"
DB = dict(host="127.0.0.1", port="5432", user="postgres", dbname="fin21_local")
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
XLSX = (Path(__file__).resolve().parent.parent.parent / "04_Entregables"
        / "LISTADO_PROYECTOS_PAQUETE_V2_2026-11-16.xlsx")

def norm_cc(v):
    if v is None:
        return None
    s = str(v).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2} ", s):
        return None
    if s.upper() in ("N/A", "NONE", "SIN ANTECEDENTE", ""):
        return None
    if re.match(r"^\d+\.0$", s):
        s = s[:-2]
    d = re.sub(r"[^0-9]", "", s)
    return d or None

# ---------- 1. proyectos del paquete ----------
import openpyxl
wb = openpyxl.load_workbook(XLSX, data_only=True)
ws = wb["Proyectos"]
proys = []
for r in ws.iter_rows(min_row=5, values_only=True):
    cod = r[0]
    if not cod or str(cod).strip().upper() == "CODIGO":
        continue
    proys.append(dict(
        codigo=str(cod).strip(),
        nombre=(r[1] or "").strip(),
        tipo=r[2] or "", ambito=r[3] or "", financiador=r[4] or "",
        concurso=r[5] or "", facultad=r[6] or "",
        inicio=str(r[9])[:10] if r[9] else "", termino=str(r[10])[:10] if r[10] else "",
        investigador=r[11] or "",
        adjudicado=float(r[12]) if isinstance(r[12], (int, float)) else 0,
        remesa_2025=float(r[13]) if isinstance(r[13], (int, float)) else 0,
        remesado_total=float(r[14]) if isinstance(r[14], (int, float)) else 0,
        cc_raw=str(r[15]) if r[15] not in (None, "") else "",
        cc=norm_cc(r[15]) or "",
    ))

with open(RAW / "proyectos.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(proys[0].keys()), delimiter=";")
    w.writeheader(); w.writerows(proys)
print("proyectos:", len(proys), "| con C.C.:", sum(1 for p in proys if p["cc"]))

ccs = {p["cc"] for p in proys if p["cc"]}

# centros de costo corregidos por acuerdo (no vienen en el paquete)
CORR = Path(__file__).resolve().parent.parent / "data" / "correcciones_cc.csv"
if CORR.exists():
    with open(CORR, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter=";"):
            c = norm_cc(row["cc"])
            if c:
                ccs.add(c)
    print("correcciones de C.C. aplicadas:", len(ccs) - len({p["cc"] for p in proys if p["cc"]}))
ccs = sorted(ccs)
in_list = ",".join("'" + c + "'" for c in ccs)
codigos = sorted({p["codigo"] for p in proys})
cod_list = ",".join("'" + c.replace("'", "''") + "'" for c in codigos)

# ---------- 2. movimientos ----------
env = dict(os.environ, PGPASSWORD=(HOME / ".pg_creds").read_text(encoding="utf-8").strip())

def copy(sql, dest, encoding=None):
    q = f"\\copy ({sql}) TO '{dest.as_posix()}' WITH (FORMAT csv, HEADER true, DELIMITER ';')"
    e = dict(env)
    if encoding:
        e["PGCLIENTENCODING"] = encoding
    r = subprocess.run([PSQL, "-h", DB["host"], "-p", DB["port"], "-U", DB["user"],
                        "-d", DB["dbname"], "-w", "-v", "ON_ERROR_STOP=1", "-c", q],
                       env=e, capture_output=True)
    r.stdout = (r.stdout or b"").decode("utf-8", "replace")
    r.stderr = (r.stderr or b"").decode("utf-8", "replace")
    if r.returncode:
        raise SystemExit(r.stderr)
    n = sum(1 for _ in open(dest, encoding="utf-8", errors="replace")) - 1
    print(f"{dest.name}: {n} filas")

# movimientos por COPY en Python (psycopg): evita los problemas de codificación de psql
import psycopg

sql_movs = f"""
  SELECT replace(m.centro_costo,'.','') AS cc, m.centro_costo AS cc_raw, m.numero, m.num_linea,
         m.f_ingreso::date AS fecha, m.cod_sitm, m.cod_tipmov, m.valor, m.rut_prov, m.glosa,
         (SELECT d.glosa FROM public.fact_documento d WHERE d.numero = m.numero LIMIT 1) AS glosa_doc,
         m.num_oc, m.ano_docume, m.sello_extraccion
  FROM public.fact_movimiento_cc m
  WHERE replace(m.centro_costo,'.','') IN ({in_list})
"""
with psycopg.connect(host=DB["host"], port=DB["port"], user=DB["user"], dbname=DB["dbname"],
                     password=env["PGPASSWORD"]) as conn, conn.cursor() as cur:
    with open(RAW / "movimientos.csv", "w", encoding="utf-8", newline="") as f:
        with cur.copy(f"COPY ({sql_movs}) TO STDOUT WITH (FORMAT csv, HEADER true, DELIMITER ';')") as cp:
            for data in cp:
                f.write(bytes(data).decode("utf-8"))
n = sum(1 for _ in open(RAW / "movimientos.csv", encoding="utf-8")) - 1
print(f"movimientos.csv: {n} filas")

copy("""
  SELECT cod_sitm, des_item, des_glosa, cod_cuenta
  FROM public.dim_item
""", RAW / "dim_item.csv")

copy("""
  SELECT cod_tipmov, des_tipmov, deve, perc, comp, pago
  FROM public.dim_tipo_mov
""", RAW / "dim_tipo_mov.csv")

copy(f"""
  SELECT proyecto, centro_costo, anio, periodo, item, subitem, tipo_documento,
         nro_documento, rut, rut_dv, fecha, proveedor, descripcion, monto_num,
         estado, inst_financiera, universo, cc_respaldo, documento_fin21, diferencia
  FROM public.v_cruce_anid_linea
  WHERE proyecto IN ({cod_list})
""", RAW / "declarado.csv", encoding="LATIN1")

copy("""
  SELECT proyecto, item, presupuesto_actual, real_gastado, saldo_disponible,
         nuevo_presupuesto, corte_anid, inst_financiera
  FROM public.fact_anid_presupuesto
  WHERE corte_anid = (SELECT max(corte_anid) FROM public.fact_anid_presupuesto)
""", RAW / "presupuesto_anid.csv", encoding="LATIN1")

print("extracción completa ->", RAW)
