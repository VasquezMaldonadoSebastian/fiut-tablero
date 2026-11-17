# -*- coding: utf-8 -*-
"""Exportador Excel del tablero: 7 hojas, con la reconciliación y la equivalencia."""
import io
from datetime import datetime

import pandas as pd


def excel_bytes(df_gasto, df_paso, filtros, tax, corte, version_tax, universo, usuario=""):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="xlsxwriter", datetime_format="dd-mm-yyyy",
                        date_format="dd-mm-yyyy") as xw:
        wb = xw.book
        fmt_money = wb.add_format({"num_format": "$#,##0", "font_name": "Calibri", "font_size": 10})
        fmt_head = wb.add_format({"bold": True, "bg_color": "#0E6F62", "font_color": "white",
                                  "font_name": "Calibri", "font_size": 10, "border": 1})
        fmt_txt = wb.add_format({"font_name": "Calibri", "font_size": 10})

        ws = wb.add_worksheet("1 Parametros")
        ws.set_column(0, 1, 34)
        ws.write_row(0, 0, ["Parámetro", "Valor"], fmt_head)
        filas = [("Corte de datos", corte),
                 ("Fecha de descarga", datetime.now().strftime("%d-%m-%Y %H:%M")),
                 ("Versión equivalencia", version_tax),
                 ("Universo", universo),
                 ("Usuario", usuario or "—")]
        filas += [(k, ", ".join(map(str, v)) if isinstance(v, (list, tuple)) and v else "Todos")
                  for k, v in filtros]
        for i, (a, b) in enumerate(filas, start=1):
            ws.write(i, 0, a, fmt_txt)
            ws.write(i, 1, b, fmt_txt)

        def write(df, sheet):
            ws = wb.add_worksheet(sheet)
            for j, col in enumerate(df.columns):
                ws.write(0, j, str(col), fmt_head)
                if pd.api.types.is_numeric_dtype(df[col]):
                    ws.set_column(j, j, 16)
                    for i, v in enumerate(df[col].tolist(), start=1):
                        ws.write_number(i, j, float(v), fmt_money)
                else:
                    largo = int(df[col].astype(str).str.len().mean() * 1.3) if len(df) else 12
                    ws.set_column(j, j, min(48, max(12, largo)))
                    for i, v in enumerate(df[col].tolist(), start=1):
                        ws.write(i, j, "" if pd.isna(v) else str(v), fmt_txt)
            ws.freeze_panes(1, 0)
            if len(df):
                ws.autofilter(0, 0, len(df), len(df.columns) - 1)

        res = df_gasto.groupby("rubro", as_index=False)["valor"].sum()
        res = pd.concat([res, pd.DataFrame([
            {"rubro": "TOTAL clasificable", "valor": df_gasto["valor"].sum()},
            {"rubro": "Cuentas de paso (no suma)", "valor": df_paso["valor"].sum()},
            {"rubro": "Registrado bruto", "valor": df_gasto["valor"].sum() + df_paso["valor"].sum()},
        ])])
        write(res.rename(columns={"rubro": "Rubro", "valor": "Monto"}), "2 Resumen")

        m = df_gasto.groupby(["rubro", "subitem", "anio"], as_index=False)["valor"].sum()
        piv = m.pivot_table(index=["rubro", "subitem"], columns="anio", values="valor",
                            aggfunc="sum", fill_value=0)
        piv["Total"] = piv.sum(axis=1)
        write(piv.reset_index().rename(columns={"rubro": "Rubro", "subitem": "Subítem"}),
              "3 Subitems x año")

        it = df_gasto.groupby(["cod_sitm", "des_item", "rubro", "subitem"], as_index=False)["valor"].sum()
        write(it.rename(columns={"cod_sitm": "Ítem", "des_item": "Nombre", "rubro": "Rubro",
                                 "subitem": "Subítem", "valor": "Monto"}), "4 Items")

        cols = ["fecha", "anio", "mes", "proyecto", "cc", "cod_sitm", "des_item", "rubro",
                "subitem", "etiqueta", "glosa", "movimientos", "valor"]
        det = df_gasto[[c for c in cols if c in df_gasto.columns]].copy()
        if "glosa" in det.columns:
            det["glosa"] = det["glosa"].astype(str).str.slice(0, 250)
        write(det, "5 Detalle")

        write(df_paso.groupby(["cod_sitm", "des_item"], as_index=False)["valor"].sum()
              .rename(columns={"cod_sitm": "Ítem", "des_item": "Nombre", "valor": "Monto"}),
              "6 Cuentas de paso")

        write(tax, "7 Equivalencia")
    out.seek(0)
    return out.getvalue()
