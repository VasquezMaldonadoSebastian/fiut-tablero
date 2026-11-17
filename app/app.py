# -*- coding: utf-8 -*-
"""Tablero FIUT · cartera, gasto por tipo y proyección.

Streamlit sobre un archivo DuckDB local (data/fiu_fiut.duckdb).
Sin conexión a bases institucionales: el ETL es el único que lee fin21_local.
"""
import os
import sys
from datetime import date, datetime
from pathlib import Path

import altair as alt
import duckdb
import numpy as np
import pandas as pd
import streamlit as st

BASE = Path(__file__).resolve().parent.parent
FULL = BASE / "data" / "fiu_fiut.duckdb"
SHARE = BASE / "data" / "share" / "fiu_fiut_share.duckdb"
DB = Path(os.environ["FIU_DB"]) if os.environ.get("FIU_DB") else (FULL if FULL.exists() else SHARE)
MODO = "detalle" if DB == FULL else "share"
CORTE = "16-11-2026"
VERSION_TAX = "v1 · 2026-11-17"

st.set_page_config(page_title="FIUT · cartera y gasto", page_icon="◧", layout="wide")

# ---------------------------------------------------------------- estilo
INK, MUTED, LINE = "#15181D", "#7C838C", "#E6E8EB"
ACCENT = "#0E6F62"

st.markdown(f"""
<style>
  html, body, [class*="css"] {{ font-family: 'Segoe UI', Inter, system-ui, sans-serif; }}
  .stApp {{ background: #F5F6F7; }}
  .block-container {{ padding: 1.4rem 2.2rem 3rem; max-width: 1500px; }}
  h1, h2, h3, h4 {{ color: {INK}; letter-spacing: -.2px; }}
  .hero {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; }}
  .brand {{ display:flex; gap:13px; align-items:center; }}
  .mark {{ width:34px;height:34px;border-radius:9px;background:{ACCENT};color:#fff;display:flex;
           align-items:center;justify-content:center;font-weight:700;font-size:13px;letter-spacing:.5px; }}
  .h1 {{ font-size:19px;font-weight:650;color:{INK};line-height:1.2; }}
  .sub {{ font-size:12px;color:{MUTED};margin-top:3px; }}
  .kpis {{ display:grid;grid-template-columns:repeat(auto-fit,minmax(196px,1fr));gap:14px;margin:6px 0 16px; }}
  .k {{ background:#fff;border:1px solid {LINE};border-radius:11px;padding:15px 17px; }}
  .kl {{ font-size:10.5px;letter-spacing:.7px;text-transform:uppercase;color:#8B929A;font-weight:600; }}
  .kv {{ font-size:26px;font-weight:650;letter-spacing:-.6px;margin-top:7px;color:{INK};
         font-variant-numeric:tabular-nums; }}
  .kd {{ font-size:11.5px;color:{MUTED};margin-top:5px; }}
  .kd i {{ font-style:normal;color:{ACCENT};font-weight:600; }}
  .k.mute .kv {{ color:#8B929A; }}
  .card {{ background:#fff;border:1px solid {LINE};border-radius:11px;padding:16px 18px; }}
  .ct {{ font-size:13px;font-weight:650;color:{INK}; }}
  .cs {{ font-size:11px;color:#9AA0A8; }}
  div[data-testid="stDataFrame"] {{ border:1px solid {LINE}; border-radius:10px; }}
  .stRadio > div {{ gap: 4px; }}
  .stRadio label {{ font-size: 13px !important; }}
  .note {{ font-size:11.5px;color:{MUTED}; }}
  .tag {{ display:inline-block;font-size:10.5px;padding:2px 8px;border-radius:20px;
         background:#EEF4F2;color:{ACCENT};font-weight:600; }}
</style>
""", unsafe_allow_html=True)


def clp(v, dec=0):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    return "$" + f"{v:,.{dec}f}".replace(",", ".")


def mm(v):
    if v is None or pd.isna(v):
        return "—"
    return f"{v/1e6:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


@st.cache_data(show_spinner=False)
def q(sql, _mtime=None):
    con = duckdb.connect(str(DB), read_only=True)
    try:
        return con.execute(sql).df()
    finally:
        con.close()


MTIME = DB.stat().st_mtime
try:
    n_filas = int(q("SELECT valor FROM meta WHERE clave='filas_paquete'", MTIME)["valor"][0])
except Exception:
    n_filas = q("SELECT count(*) n FROM proyectos", MTIME)["n"][0]

# ---------------------------------------------------------------- cartera
proys = q("SELECT * FROM dim_proyecto ORDER BY adjudicado DESC NULLS LAST", MTIME)
proys["adjudicado"] = proys["adjudicado"].fillna(0)

rubros = q("SELECT rubro, round(sum(valor)) monto FROM v_gasto GROUP BY 1 ORDER BY 2 DESC", MTIME)
total_gasto = float(rubros["monto"].sum())
paso = float(q("SELECT coalesce(sum(valor),0) v FROM v_paso", MTIME)["v"][0])
bruto = total_gasto + paso

# ---------------------------------------------------------------- filtros
st.markdown(f"""<div class="hero"><div class="brand"><div class="mark">FIU</div>
<div><div class="h1">Cartera FIUT · gasto por tipo</div>
<div class="sub">{n_filas} proyectos del paquete · {proys['cc'].replace('', pd.NA).nunique()} centros de costo ·
libro Kullin y declaración ANID · corte {CORTE}</div></div></div>
<div><span class="tag">equivalencia {VERSION_TAX}</span></div></div>""", unsafe_allow_html=True)

f1, f2, f3, f4, f5 = st.columns([1.1, 2.1, 1.9, 1.4, 0.8])
anios = q("SELECT DISTINCT anio FROM v_egreso ORDER BY 1", MTIME)["anio"].tolist()
sel_anio = f1.multiselect("Año", anios, default=anios, key="f_anio")
sel_proy = f2.multiselect("Proyecto", sorted(proys["codigo"].tolist()), default=[], key="f_proy",
                          placeholder="Todos los proyectos")
ccs = q("SELECT DISTINCT cc FROM v_egreso ORDER BY 1", MTIME)["cc"].tolist()
sel_cc = f3.multiselect("Centro de costo", ccs, default=[], key="f_cc", placeholder="Todos los C.C.")
sel_rubro = f4.multiselect("Rubro", rubros["rubro"].tolist(), default=[], key="f_rubro",
                           placeholder="Todos los rubros")


def _limpiar():
    st.session_state["f_anio"] = anios
    st.session_state["f_proy"] = []
    st.session_state["f_cc"] = []
    st.session_state["f_rubro"] = []


with f5:
    st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
    st.button("Limpiar", on_click=_limpiar, use_container_width=True,
              help="Vuelve a todos los años y sin filtros de proyecto, C.C. ni rubro")


def clause():
    w = []
    if sel_anio:
        w.append("anio IN (" + ",".join(str(int(a)) for a in sel_anio) + ")")
    if sel_proy:
        w.append("proyecto IN (" + ",".join("'" + str(p).replace("'", "''") + "'" for p in sel_proy) + ")")
    if sel_cc:
        w.append("cc IN (" + ",".join("'" + c + "'" for c in sel_cc) + ")")
    if sel_rubro:
        w.append("rubro IN (" + ",".join("'" + r.replace("'", "''") + "'" for r in sel_rubro) + ")")
    return (" WHERE " + " AND ".join(w)) if w else ""


W = clause()

# ---------------------------------------------------------------- navegación
PAGINAS = ["Resumen", "Registros", "Proyectos", "Ítems", "Declarado", "Proyección", "Ingresos", "Metodología"]
pag = st.radio("Vista", PAGINAS, horizontal=True, label_visibility="collapsed")

gasto_f = q(f"SELECT * FROM v_gasto{W}", MTIME)
total_f = float(gasto_f["valor"].sum())
paso_f = float(q(f"SELECT coalesce(sum(valor),0) v FROM v_paso{W}", MTIME)["v"][0])


def n_movs(df):
    return int(df["movimientos"].sum()) if "movimientos" in df.columns else len(df)


def kpis(vals):
    html = '<div class="kpis">'
    for lab, val, det, mute in vals:
        html += (f'<div class="k {"mute" if mute else ""}"><div class="kl">{lab}</div>'
                 f'<div class="kv">{val}</div><div class="kd">{det}</div></div>')
    return html + "</div>"


# ================================================================ RESUMEN
if pag == "Resumen":
    n_proy = gasto_f["proyecto"].nunique()
    st.markdown(kpis([
        ("Gasto clasificable", f"${mm(total_f)}", f"<i>{n_movs(gasto_f):,}</i> movimientos · {gasto_f['rubro'].nunique()} rubros con datos".replace(",", "."), False),
        ("Cuentas de paso", f"${mm(paso_f)}", "fuera de los totales", True),
        ("Registrado bruto", f"${mm(total_f + paso_f)}", "libro Kullin, sin depurar", False),
        ("Cartera", f"{n_filas}", f"{n_proy} con ejecución · 122 códigos", False),
    ]), unsafe_allow_html=True)

    c1, c2 = st.columns([1.55, 1])
    with c1, st.container(border=True):
        st.markdown('<div class="ct">Gasto por rubro</div><div class="cs">MM de pesos · filtros aplicados</div>',
                    unsafe_allow_html=True)
        d = gasto_f.groupby("rubro", as_index=False)["valor"].sum().sort_values("valor", ascending=False)
        d["mm"] = d["valor"] / 1e6
        colores = ["#7FC4B8", "#A9B9E0", "#E6C08C", "#CBB6D6", "#C4D19B", "#E8A9A0", "#9FC7D8"]
        dom = d["rubro"].tolist()
        ch = (alt.Chart(d).mark_bar(cornerRadius=4, size=18).encode(
            x=alt.X("mm:Q", title="MM de pesos", axis=alt.Axis(format=",.0f", grid=True, gridColor="#F1F3F4")),
            y=alt.Y("rubro:N", sort=dom, title=None, axis=alt.Axis(labelLimit=220)),
            color=alt.Color("rubro:N", scale=alt.Scale(domain=dom, range=colores[:len(dom)]), legend=None),
            tooltip=[alt.Tooltip("rubro:N", title="Rubro"),
                     alt.Tooltip("valor:Q", title="Monto", format=",.0f")],
        ).properties(height=max(190, 44 * len(d))))
        st.altair_chart(ch, use_container_width=True)

    with c2, st.container(border=True):
        st.markdown('<div class="ct">Operación · subítems</div><div class="cs">MM de pesos</div>',
                    unsafe_allow_html=True)
        s = (gasto_f[gasto_f["rubro"] == "Gastos de operación"]
             .groupby("subitem", as_index=False)["valor"].sum().sort_values("valor", ascending=False))
        s["subitem"] = s["subitem"].replace("", "Sin subítem")
        s["mm"] = s["valor"] / 1e6
        ch2 = (alt.Chart(s).mark_bar(cornerRadius=3, size=13, color="#A9B9E0").encode(
            x=alt.X("mm:Q", title=None, axis=alt.Axis(format=",.0f", grid=False, labels=False)),
            y=alt.Y("subitem:N", sort="-x", title=None, axis=alt.Axis(labelLimit=180)),
            tooltip=[alt.Tooltip("subitem:N", title="Subítem"),
                     alt.Tooltip("valor:Q", title="Monto", format=",.0f")],
        ).properties(height=max(190, 34 * len(s))))
        st.altair_chart(ch2, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    hoy = date.today()
    t = gasto_f.groupby(["proyecto", "proyecto_nombre"], as_index=False).agg(
        ejecutado=("valor", "sum"), cc=("cc", "first"))
    t = t.merge(proys[["codigo", "adjudicado", "termino", "financiador"]],
                left_on="proyecto", right_on="codigo", how="left")
    t["avance"] = (t["ejecutado"] / t["adjudicado"] * 100).where(t["adjudicado"] > 0)
    t["termino"] = pd.to_datetime(t["termino"])
    t["dias"] = (t["termino"] - pd.Timestamp(hoy)).dt.days
    t["estado"] = t["dias"].apply(lambda d: "vencido" if pd.notna(d) and d < 0
                                  else ("por cerrar" if pd.notna(d) and d <= 90 else "vigente"))
    t["nombre"] = t["proyecto_nombre"].fillna("—").str.slice(0, 58)
    t["codigo"] = t["proyecto"]
    t["cc"] = t["cc"].astype(str)
    t["cc_fmt"] = t["cc"].str.slice(0, 4) + "." + t["cc"].str.slice(4)
    t["eje"] = t["ejecutado"].map(lambda v: f"${mm(v)}").astype(str)
    t["adj"] = t["adjudicado"].map(lambda v: f"${mm(v)}").astype(str)

    def av(v):
        return "—" if pd.isna(v) else f"{v:.0f}%"
    t["av"] = t["avance"].map(av)
    t["term"] = t["termino"].dt.strftime("%d-%m-%Y").fillna("—")

    vv = t.sort_values("ejecutado", ascending=False)
    st.markdown('<div class="ct">Ejecución por proyecto</div>'
                '<div class="cs">clasificable sobre monto adjudicado</div>', unsafe_allow_html=True)
    st.dataframe(
        vv[["codigo", "nombre", "cc_fmt", "adj", "eje", "av", "term", "estado"]].rename(columns={
            "codigo": "Código", "nombre": "Proyecto", "cc_fmt": "C.C.", "adj": "Adjudicado",
            "eje": "Ejecutado", "av": "Avance", "term": "Término", "estado": "Estado"}),
        use_container_width=True, hide_index=True, height=380,
        column_config={"Estado": st.column_config.TextColumn(width="small")})
    st.markdown(f'<div class="note">Bruto {clp(bruto)} − cuentas de paso {clp(paso)} = '
                f'clasificable {clp(total_gasto)} · valores sin filtros. Un avance sobre 100 % significa que el '
                f'centro de costo ejecuta más que el monto adjudicado UFRO (habitual cuando hay contraparte o '
                f'el C.C. concentra más de un proyecto).</div>', unsafe_allow_html=True)

# ================================================================ REGISTROS
elif pag == "Registros":
    if MODO == "detalle":
        st.markdown(f'<div class="ct">Registros de gasto</div><div class="cs">una fila por movimiento · '
                    f'{len(gasto_f):,} filas con los filtros actuales</div>'.replace(",", "."),
                    unsafe_allow_html=True)
        cols = ["fecha", "anio", "proyecto", "cc", "cod_sitm", "des_item", "glosa", "rubro", "valor"]
        d = gasto_f[cols].sort_values("fecha", ascending=False).copy()
        d.insert(0, "n", range(1, len(d) + 1))
        st.dataframe(d, use_container_width=True, hide_index=True, height=560,
                     column_config={
                         "fecha": st.column_config.DateColumn("Fecha", format="DD-MM-YYYY"),
                         "valor": st.column_config.NumberColumn("Monto ($)", format="localized"),
                         "cc": st.column_config.TextColumn("C.C."),
                         "des_item": st.column_config.TextColumn("Ítem contable", width="medium"),
                         "rubro": st.column_config.TextColumn("Rubro", width="small"),
                         "glosa": st.column_config.TextColumn("Glosa", width="medium"),
                     })
    else:
        st.markdown('<div class="ct">Registros de gasto</div>'
                    '<div class="cs">versión en línea: una fila por movimiento · sin RUT ni número '
                    'de documento</div>', unsafe_allow_html=True)
        w2 = W.replace("WHERE", "AND") if W else ""
        d = q(f"""SELECT fecha, anio, proyecto, cc, cod_sitm, des_item, glosa, rubro, valor
                   FROM mov_detalle WHERE veredicto = 'gasto' {w2}
                   ORDER BY fecha DESC""", MTIME)
        st.dataframe(d, use_container_width=True, hide_index=True, height=560,
                     column_config={
                         "fecha": st.column_config.DateColumn("Fecha", format="DD-MM-YYYY"),
                         "valor": st.column_config.NumberColumn("Monto ($)", format="localized"),
                         "anio": st.column_config.NumberColumn("Año", width="small"),
                         "mes": st.column_config.NumberColumn("Mes", width="small"),
                         "des_item": st.column_config.TextColumn("Ítem contable", width="medium"),
                         "rubro": st.column_config.TextColumn("Rubro", width="small"),
                         "glosa": st.column_config.TextColumn("Glosa", width="medium"),
                     })
    st.caption(f"Total filtrado: {clp(total_f)} · cuentas de paso excluidas: {clp(paso_f)} · "
               f"modo {'detalle completo' if MODO == 'detalle' else 'en línea (sin RUT ni documento)'}")

# ================================================================ PROYECTOS
elif pag == "Proyectos":
    agg_movs = ("movimientos", "sum") if "movimientos" in gasto_f.columns else ("valor", "count")
    d = gasto_f.groupby(["proyecto", "proyecto_nombre"], as_index=False).agg(
        ejecutado=("valor", "sum"), movimientos=agg_movs)
    d = d.merge(proys[["codigo", "adjudicado", "financiador", "inicio", "termino"]],
                left_on="proyecto", right_on="codigo", how="left")
    d["saldo"] = d["adjudicado"] - d["ejecutado"]
    d["avance"] = (d["ejecutado"] / d["adjudicado"] * 100).where(d["adjudicado"] > 0, 0)
    st.markdown('<div class="ct">Cartera con ejecución</div><div class="cs">adjudicado vs clasificable</div>',
                unsafe_allow_html=True)
    st.dataframe(
        d.sort_values("ejecutado", ascending=False)[
            ["proyecto", "proyecto_nombre", "financiador", "adjudicado", "ejecutado", "saldo", "avance", "movimientos"]],
        use_container_width=True, hide_index=True, height=520,
        column_config={
            "proyecto": "Código", "proyecto_nombre": "Proyecto", "financiador": "Financiador",
            "adjudicado": st.column_config.NumberColumn("Adjudicado ($)", format="localized"),
            "ejecutado": st.column_config.NumberColumn("Ejecutado ($)", format="localized"),
            "saldo": st.column_config.NumberColumn("Saldo ($)", format="localized"),
            "avance": st.column_config.ProgressColumn("Avance", format="%.0f%%", min_value=0, max_value=150),
            "movimientos": "Movs."})

# ================================================================ ÍTEMS
elif pag == "Ítems":
    tt = q("SELECT cod_sitm, rubro, subitem, etiqueta, veredicto FROM taxonomia", MTIME)
    d = gasto_f.groupby(["cod_sitm", "des_item", "cod_tipmov"], as_index=False).agg(
        valor=("valor", "sum"))
    piv = gasto_f.assign(
        med=np.where(gasto_f["pagado"].abs() > 0, "pagado",
                     np.where(gasto_f["comprometido"].abs() > 0, "comprometido", "registrado")))
    base = gasto_f.groupby(["cod_sitm", "des_item", "rubro", "subitem"], as_index=False).agg(
        monto=("valor", "sum"), movimientos=("valor", "count"))
    base["pct"] = base["monto"] / base["monto"].sum() * 100
    base["acum"] = base.sort_values("monto", ascending=False)["pct"].cumsum()
    st.markdown('<div class="ct">Ítems contables clasificados</div>'
                f'<div class="cs">{len(base)} ítems · 29 concentran el 95 %</div>', unsafe_allow_html=True)
    st.dataframe(
        base.sort_values("monto", ascending=False),
        use_container_width=True, hide_index=True, height=560,
        column_config={"cod_sitm": "Ítem", "des_item": "Nombre", "rubro": "Rubro", "subitem": "Subítem",
                       "monto": st.column_config.NumberColumn("Monto ($)", format="localized"),
                       "movimientos": "Movs.",
                       "pct": st.column_config.NumberColumn("%", format="%.1f%%"),
                       "acum": st.column_config.NumberColumn("% acum.", format="%.1f%%")})

# ================================================================ DECLARADO
elif pag == "Declarado":
    sql_decl = ("""SELECT proyecto, anio, sum(monto_num) monto, count(*) lineas
                   FROM declarado GROUP BY 1,2 ORDER BY 1,2""" if MODO == "detalle" else
                """SELECT proyecto, anio, sum(monto) monto, sum(lineas) lineas
                   FROM declarado GROUP BY 1,2 ORDER BY 1,2""")
    decl = q(sql_decl, MTIME)
    tot_d = float(decl["monto"].sum())
    reg = gasto_f.groupby("proyecto", as_index=False)["valor"].sum()
    dp = decl.groupby("proyecto", as_index=False)["monto"].sum().merge(reg, on="proyecto", how="left")
    dp["brecha"] = dp["monto"] - dp["valor"].fillna(0)
    st.markdown(kpis([
        ("Proyectos con cartola", f"{len(dp)}", "de 124 con declaración ANID", False),
        ("Declarado", f"${mm(tot_d)}", "líneas del portal ANID", False),
        ("Registrado en libro", f"${mm(dp['valor'].fillna(0).sum())}", "mismos proyectos", False),
        ("Brecha", f"${mm(dp['brecha'].sum())}", "declarado − registrado", True),
    ]), unsafe_allow_html=True)
    c1, c2 = st.columns([1.2, 1])
    with c1:
        ch = (alt.Chart(dp.sort_values("monto", ascending=False).head(20)).mark_bar(cornerRadius=3).encode(
            x=alt.X("monto:Q", title=None, axis=alt.Axis(format="~s")),
            y=alt.Y("proyecto:N", sort="-x", title=None, axis=alt.Axis(labelLimit=160)),
            color=alt.value("#7FC4B8"),
            tooltip=[alt.Tooltip("proyecto:N"), alt.Tooltip("monto:Q", format=",.0f")],
        ).properties(height=430, title="Declarado · top 20"))
        st.altair_chart(ch, use_container_width=True)
    with c2:
        st.dataframe(dp.sort_values("monto", ascending=False),
                     use_container_width=True, hide_index=True, height=430,
                     column_config={
                         "proyecto": "Proyecto",
                         "monto": st.column_config.NumberColumn("Declarado ($)", format="localized"),
                         "valor": st.column_config.NumberColumn("Registrado ($)", format="localized"),
                         "brecha": st.column_config.NumberColumn("Brecha ($)", format="localized")})
    st.caption("Solo proyectos con cartola ANID. El resto de la cartera no declara en ese portal.")

# ================================================================ PROYECCIÓN
elif pag == "Proyección":
    d = gasto_f.groupby(["proyecto", "anio", "mes"], as_index=False)["valor"].sum()
    d["f"] = pd.to_datetime(dict(year=d.anio, month=d.mes, day=1))
    ult = (d.sort_values("f").groupby("proyecto").tail(6)
           .groupby("proyecto", as_index=False)["valor"].sum()
           .rename(columns={"valor": "suma6"}))
    ult["prom6"] = ult["suma6"] / 6
    ult = ult[["proyecto", "prom6"]]
    tot = gasto_f.groupby("proyecto", as_index=False)["valor"].sum()
    p = tot.merge(ult, on="proyecto").merge(
        proys[["codigo", "adjudicado", "termino", "nombre"]], left_on="proyecto", right_on="codigo", how="left")
    p["prom6"] = p["prom6"].fillna(0)
    p["saldo"] = p["adjudicado"].fillna(0) - p["valor"]
    p["meses_restantes"] = (p["saldo"] / p["prom6"].replace(0, np.nan)).where(p["saldo"] > 0)
    p["fecha_agota"] = pd.Timestamp(date.today()) + pd.to_timedelta(p["meses_restantes"] * 30.4, unit="D")
    p["termino"] = pd.to_datetime(p["termino"])
    p["brecha_meses"] = ((p["fecha_agota"] - p["termino"]).dt.days / 30.4)
    p["riesgo"] = np.select(
        [p["adjudicado"].fillna(0) <= 0, p["saldo"] <= 0, p["prom6"] <= 0,
         p["brecha_meses"] < -3, p["brecha_meses"] < 0],
        ["sin monto", "sobreejecutado", "sin ejecución", "agota antes", "ajustado"], default="alcanza")
    for c in ("adjudicado", "valor", "prom6", "saldo"):
        p[c] = p[c].astype(float).round(0)
    p["nombre"] = p["nombre"].fillna("—").str.slice(0, 46)
    cnt = p["riesgo"].value_counts()
    st.markdown(kpis([
        ("Agotan antes", f"{int(cnt.get('agota antes', 0))}", "más de 3 meses antes del término", True),
        ("Sobreejecutados", f"{int(cnt.get('sobreejecutado', 0))}", "gastaron más que lo adjudicado", True),
        ("Ajustados", f"{int(cnt.get('ajustado', 0))}", "agotan dentro de los 3 meses previos", False),
        ("Alcanzan", f"{int(cnt.get('alcanza', 0))}", "el saldo cubre hasta el término", False),
        ("Sin ejecución", f"{int(cnt.get('sin ejecución', 0))}", "sin movimientos en 6 meses", True),
    ]), unsafe_allow_html=True)
    st.markdown('<div class="ct">Proyección de ejecución</div>'
                '<div class="cs">promedio de los últimos 6 meses con movimiento · fecha de agotamiento vs término</div>',
                unsafe_allow_html=True)
    st.dataframe(
        p.sort_values("brecha_meses")[
            ["proyecto", "nombre", "adjudicado", "valor", "prom6", "fecha_agota", "termino", "brecha_meses", "riesgo"]],
        use_container_width=True, hide_index=True, height=520,
        column_config={
            "proyecto": st.column_config.TextColumn("Código", width="small"),
            "nombre": st.column_config.TextColumn("Proyecto", width="medium"),
            "adjudicado": st.column_config.NumberColumn("Adjudicado ($)", format="localized", width="small"),
            "valor": st.column_config.NumberColumn("Ejecutado ($)", format="localized", width="small"),
            "prom6": st.column_config.NumberColumn("Prom. 6m ($)", format="localized", width="small"),
            "fecha_agota": st.column_config.DateColumn("Agota", format="MM-YYYY", width="small"),
            "termino": st.column_config.DateColumn("Término", format="MM-YYYY", width="small"),
            "brecha_meses": st.column_config.NumberColumn("Brecha", format="%.1f", width="small"),
            "riesgo": st.column_config.TextColumn("Riesgo", width="medium")})
    st.caption("Proyección lineal con el promedio mensual reciente. No modela estacionalidad ni cambios de "
               "presupuesto; el monto adjudicado es el del paquete FIU, no el presupuesto vigente en FIN21. "
               "«Sobreejecutado» significa que el centro de costo ya gastó más que el monto adjudicado UFRO: "
               "habitual cuando hay contraparte o el C.C. concentra más de un proyecto; en esos casos la "
               "proyección no aplica y el riesgo se informa como tal.")


# ================================================================ INGRESOS
elif pag == "Ingresos":
    tabla_ing = "v_ingreso" if MODO == "detalle" else "mov_detalle"
    col_glosa = "coalesce(glosa,'') AS glosa" if MODO == "detalle" else "glosa"
    ing = q(f"""SELECT cc, proyecto, anio, mes, cod_sitm, des_item, cubeta_ingreso,
                       {col_glosa}, valor
                FROM {tabla_ing}
                WHERE cod_tipmov BETWEEN 10 AND 15
                  {"AND anio IN (" + ",".join(str(int(a)) for a in sel_anio) + ")" if sel_anio else ""}
                """, MTIME)
    if sel_proy:
        ing = ing[ing["proyecto"].isin(sel_proy)]
    if sel_cc:
        ing = ing[ing["cc"].astype(str).isin(sel_cc)]

    rem = float(ing.loc[ing["cubeta_ingreso"] == "Remesa", "valor"].sum())
    arr = float(ing.loc[ing["cubeta_ingreso"] == "Saldo de arrastre", "valor"].sum())
    otr = float(ing.loc[ing["cubeta_ingreso"] == "Otros ingresos", "valor"].sum())
    tot = float(ing["valor"].sum())
    st.markdown(kpis([
        ("Remesas del período", f"${mm(rem)}", "ítems 21549, 21538, 21501, 21550", False),
        ("Saldo de arrastre", f"${mm(arr)}", "ítem 29901 · no es ingreso del período", True),
        ("Otros ingresos", f"${mm(otr)}", "ítem 25503 · sin clasificar por glosa", True),
        ("Ingresos del período", f"${mm(tot - arr)}", f"{len(ing):,} movimientos".replace(",", "."), False),
    ]), unsafe_allow_html=True)

    c1, c2 = st.columns([1.5, 1])
    with c1, st.container(border=True):
        st.markdown('<div class="ct">Ingresos por año y tipo</div>'
                    '<div class="cs">MM de pesos · según filtros</div>', unsafe_allow_html=True)
        d = ing.groupby(["anio", "cubeta_ingreso"], as_index=False)["valor"].sum()
        d["mm"] = d["valor"] / 1e6
        orden = ["Remesa", "Otros ingresos", "Transferencias internas", "Devoluciones y ajustes",
                 "Saldo de arrastre", "Otros"]
        colores = ["#7FC4B8", "#E6C08C", "#A9B9E0", "#CBB6D6", "#C9CED4", "#DFE3E6"]
        ch = (alt.Chart(d).mark_bar(cornerRadius=3).encode(
            x=alt.X("anio:O", title=None),
            y=alt.Y("mm:Q", title="MM de pesos", axis=alt.Axis(format=",.0f")),
            color=alt.Color("cubeta_ingreso:N", sort=orden,
                            scale=alt.Scale(domain=orden, range=colores), title=None),
            tooltip=[alt.Tooltip("anio:O", title="Año"), alt.Tooltip("cubeta_ingreso:N", title="Tipo"),
                     alt.Tooltip("valor:Q", title="Monto", format=",.0f")],
        ).properties(height=320))
        st.altair_chart(ch, use_container_width=True)

    with c2, st.container(border=True):
        st.markdown('<div class="ct">Remesas por proyecto</div><div class="cs">MM de pesos</div>',
                    unsafe_allow_html=True)
        r = (ing[ing["cubeta_ingreso"] == "Remesa"].groupby("proyecto", as_index=False)["valor"]
             .sum().sort_values("valor", ascending=False).head(12))
        r["mm"] = r["valor"] / 1e6
        ch2 = (alt.Chart(r).mark_bar(cornerRadius=3, size=14, color="#7FC4B8").encode(
            x=alt.X("mm:Q", title=None, axis=alt.Axis(format=",.0f", labels=False, grid=False)),
            y=alt.Y("proyecto:N", sort="-x", title=None, axis=alt.Axis(labelLimit=150)),
            tooltip=[alt.Tooltip("proyecto:N"), alt.Tooltip("valor:Q", format=",.0f")],
        ).properties(height=340))
        st.altair_chart(ch2, use_container_width=True)

    st.markdown('<div class="ct" style="margin-top:14px">Detalle de ingresos</div>', unsafe_allow_html=True)
    det = ing.sort_values(["anio", "mes"], ascending=False).copy()
    st.dataframe(det, use_container_width=True, hide_index=True, height=340,
                 column_config={"valor": st.column_config.NumberColumn("Monto ($)", format="localized"),
                                "glosa": st.column_config.TextColumn("Glosa", width="medium"),
                                "cubeta_ingreso": st.column_config.TextColumn("Tipo", width="small")})
    st.caption("El saldo de arrastre (29901) no es ingreso del período: se muestra para cuadrar contra la caja. "
               "«Otros ingresos» corresponde al ítem 25503, cuyas glosas son números de comprobante y no "
               "permiten clasificar por concepto.")

# ================================================================ METODOLOGÍA
else:
    st.markdown(f"""
<div class="card"><div class="ct">Cómo se calcula</div>
<div class="cs" style="margin-bottom:10px">versión de la tabla de equivalencia: {VERSION_TAX}</div>
<ul style="font-size:13px;color:#3D434B;line-height:1.75">
<li><b>Universo:</b> los 124 proyectos del paquete FIUT y sus 115 centros de costo en FIN21, incluidas las tres correcciones de C.C. acordadas el 17-11-2026.</li>
<li><b>Gasto:</b> movimientos de egreso (tipos 20 a 25) del libro Kullin, corte {CORTE}.</li>
<li><b>Cuentas de paso:</b> 13 ítems que no son gasto (solicitud electrónica de compras, obligaciones
pendientes, fondos por rendir, importaciones, transferencias internas, boletas de garantía, solicitudes de
beca y ayuda, proyecto de inversión y ajustes). Se muestran aparte y nunca se suman.</li>
<li><b>Clasificación:</b> cada ítem contable tiene rubro, subítem y etiqueta en la tabla de equivalencia.
Un ítem sin clasificar aparece como tal, con su monto.</li>
<li><b>Declarado:</b> líneas de la cartola ANID de los 61 proyectos que declaran en ese portal. Los demás
financiadores no tienen cartola en la base.</li>
<li><b>Doble conteo:</b> un movimiento de tipo 20 suma a comprometido y a pagado. Por eso la medida principal
es el monto registrado, y comprometido/pagado se leen por separado.</li>
</ul></div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- export
sys.path.insert(0, str(Path(__file__).resolve().parent))
from exportar import excel_bytes  # noqa: E402

st.sidebar.markdown("### Descargar")
st.sidebar.caption("Exporta lo que está filtrado en pantalla, con la reconciliación y la tabla de equivalencia.")
fname = (f"FIUT_{'-'.join(map(str, sel_anio)) or 'todos'}_"
         f"{'filtrado' if (sel_proy or sel_cc or sel_rubro) else 'cartera'}_"
         f"{date.today():%Y%m%d}.xlsx")
if MODO == "detalle":
    exp_gasto, exp_paso = gasto_f, q(f"SELECT * FROM v_paso{W}", MTIME)
else:
    w2 = W.replace("WHERE", "AND") if W else ""
    exp_gasto = q(f"SELECT * FROM mov_detalle WHERE veredicto='gasto' {w2}", MTIME)
    exp_paso = q(f"SELECT * FROM mov_detalle WHERE veredicto='paso' {w2}", MTIME)

st.sidebar.download_button(
    "↓ Excel con filtros",
    data=excel_bytes(exp_gasto, exp_paso,
                     [("Año", sel_anio), ("Proyecto", sel_proy), ("Centro de costo", sel_cc),
                      ("Rubro", sel_rubro)],
                     q("SELECT * FROM taxonomia", MTIME), CORTE, VERSION_TAX,
                     f"{n_filas} proyectos · {len(ccs)} centros de costo"),
    file_name=fname, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True)
st.sidebar.caption(f"{n_movs(gasto_f):,} movimientos · {clp(total_f)}".replace(",", "."))
