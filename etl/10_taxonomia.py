# -*- coding: utf-8 -*-
"""E0 · Tabla de equivalencia ítem contable -> rubro / subítem (taxonomía ANID).

Veredicto por ítem: 'gasto' | 'paso' (cuenta de paso o no gasto).
La tabla es un entregable versionado: no se edita encima, se sube de versión.
"""
import csv
from pathlib import Path

VERSION = "v1 · 2026-11-17"
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
OUT = Path(__file__).resolve().parent.parent / "data" / "taxonomia_item.csv"

PERSONAL, OPERACION, EQUIPOS = "Gastos en personal", "Gastos de operación", "Equipos"
INFRA, ADM, GENERALES, TRANSF = ("Infraestructura", "Gastos de administración superior",
                                 "Gastos generales", "Otras transferencias")

# cod_sitm: (veredicto, rubro, subitem, etiqueta, criterio)
M = {
    # --- cuentas de paso / no gasto -----------------------------------------
    "32800": ("paso", "", "", "", "Solicitud electrónica de compras: repite el monto del bien que luego se imputa al ítem real"),
    "52001": ("paso", "", "", "", "Obligaciones pendientes: documento en tránsito, se imputa al pagarse"),
    "36201": ("paso", "", "", "", "Fondos por rendir: entrega de dinero a rendir, no gasto devengado"),
    "36202": ("paso", "", "", "", "Importaciones: cuenta de tránsito aduanero"),
    "38901": ("paso", "", "", "", "Transferencias internas entre centros de costo"),
    "38912": ("paso", "", "", "", "Devolución a proyectos del sector público: reversa, no gasto"),
    "38913": ("paso", "", "", "", "Resolución de remesas internacionales: traspaso de fondos"),
    "83300": ("paso", "", "", "", "Boletas de garantía: garantía, no gasto"),
    "37401": ("paso", "", "", "", "Solicitud de beca de alumno laborante: la ejecución está en 37400"),
    "38801": ("paso", "", "", "", "Solicitud de ayuda económica a estudiantes: la ejecución está en 38800"),
    "41501": ("paso", "", "", "", "Proyecto de inversión: imputación presupuestaria, no gasto"),
    "25300": ("paso", "", "", "", "Recuperación de ingresos y gastos de años anteriores: ajuste"),
    "32706": ("paso", "", "", "", "Presupuesto de consumo corriente: asignación, no gasto ejecutado (decisión pendiente)"),

    # --- personal -----------------------------------------------------------
    "31001": ("gasto", PERSONAL, "Honorarios", "Honorarios", "Honorarios no docentes"),
    "30300": ("gasto", PERSONAL, "Remuneraciones", "Investigadores", "Remuneraciones de académicos"),
    "30600": ("gasto", PERSONAL, "Remuneraciones", "Profesionales", "Remuneraciones de no académicos"),
    "30000": ("gasto", PERSONAL, "Remuneraciones", "Directivos", "Remuneraciones de directivos"),
    "31701": ("gasto", PERSONAL, "Remuneraciones", "Aportes patronales", "Aporte patronal ley de accidentes del trabajo"),
    "31702": ("gasto", PERSONAL, "Remuneraciones", "Aportes patronales", "Aporte patronal SIS"),
    "31704": ("gasto", PERSONAL, "Remuneraciones", "Aportes patronales", "Capitalización individual"),
    "31705": ("gasto", PERSONAL, "Remuneraciones", "Aportes patronales", "Seguro social expectativa de vida"),
    "31706": ("gasto", PERSONAL, "Remuneraciones", "Aportes patronales", "Seguro social rentabilidad protegida"),
    "37400": ("gasto", PERSONAL, "Incentivos", "Becas", "Becas de alumnos laborantes"),

    # --- operación: traslados ----------------------------------------------
    "36301": ("gasto", OPERACION, "Pasajes", "", "Pasajes aéreos internacionales, agencias"),
    "36302": ("gasto", OPERACION, "Pasajes", "", "Pasajes nacionales LAN"),
    "36303": ("gasto", OPERACION, "Pasajes", "", "Pasajes nacionales SKY"),
    "36304": ("gasto", OPERACION, "Pasajes", "", "Pasajes aéreos nacionales, agencias"),
    "36305": ("gasto", OPERACION, "Pasajes", "", "Pasajes aéreos internacionales LAN"),
    "35401": ("gasto", OPERACION, "Pasajes", "Movilización", "Pasajes, fletes y movilización"),
    "31200": ("gasto", OPERACION, "Viáticos", "Nacional", "Viáticos nacionales"),
    "31201": ("gasto", OPERACION, "Viáticos", "Extranjero", "Viáticos al extranjero"),
    "35402": ("gasto", OPERACION, "Viáticos", "Hospedaje", "Hospedaje, hotel y restaurante"),

    # --- operación: materiales y servicios ----------------------------------
    "32704": ("gasto", OPERACION, "Materiales fungibles", "", "Materiales de uso corriente"),
    "32726": ("gasto", OPERACION, "Materiales fungibles", "Laboratorio", "Reactivos químicos de laboratorio"),
    "32728": ("gasto", OPERACION, "Materiales fungibles", "Laboratorio", "Insumos de laboratorio"),
    "32727": ("gasto", OPERACION, "Materiales fungibles", "Laboratorio", "Material de vidrio para laboratorio"),
    "32742": ("gasto", OPERACION, "Materiales fungibles", "Clínico", "Insumos clínicos"),
    "32729": ("gasto", OPERACION, "Materiales fungibles", "Veterinario", "Insumos veterinarios"),
    "32705": ("gasto", OPERACION, "Materiales fungibles", "", "Herramientas menores y accesorios"),
    "32702": ("gasto", OPERACION, "Materiales fungibles", "", "Textiles, vestuario y calzado"),
    "32703": ("gasto", OPERACION, "Materiales fungibles", "", "Combustibles y lubricantes"),
    "33100": ("gasto", OPERACION, "Materiales fungibles", "Docencia", "Material para la docencia"),
    "34800": ("gasto", OPERACION, "Materiales fungibles", "Computación", "Accesorios y piezas menores de computadores"),
    "34700": ("gasto", OPERACION, "Materiales fungibles", "Computación", "Suministros computacionales"),

    "35001": ("gasto", OPERACION, "Gastos generales del proyecto", "", "Otros servicios"),
    "35105": ("gasto", OPERACION, "Gastos generales del proyecto", "", "Mantención e instalación de equipos y muebles"),
    "35109": ("gasto", OPERACION, "Gastos generales del proyecto", "", "Otras mantenciones y reparaciones"),
    "35106": ("gasto", OPERACION, "Gastos generales del proyecto", "", "Reparación y mantención de vehículos"),
    "33604": ("gasto", OPERACION, "Gastos generales del proyecto", "Bancarios", "Otros cargos bancarios"),
    "36001": ("gasto", OPERACION, "Gastos generales del proyecto", "", "Gastos menores"),
    "36002": ("gasto", OPERACION, "Gastos generales del proyecto", "", "Gastos por mobiliario de aulas"),
    "35800": ("gasto", OPERACION, "Gastos generales del proyecto", "", "Gastos de despacho y correspondencia"),
    "34200": ("gasto", OPERACION, "Gastos generales del proyecto", "Arriendos", "Arriendos de equipos"),
    "34300": ("gasto", OPERACION, "Gastos generales del proyecto", "Arriendos", "Otros arriendos"),
    "34100": ("gasto", OPERACION, "Gastos generales del proyecto", "Arriendos", "Arriendos de inmuebles"),
    "34400": ("gasto", OPERACION, "Gastos generales del proyecto", "Arriendo de vehículo", "Arriendos de vehículos"),
    "32701": ("gasto", OPERACION, "Gastos generales del proyecto", "Alimentación", "Alimentos y bebidas"),
    "33200": ("gasto", OPERACION, "Gastos generales del proyecto", "", "Gastos de investigación"),
    "32001": ("gasto", OPERACION, "Gastos generales del proyecto", "Servicios básicos", "Energía eléctrica"),
    "32100": ("gasto", OPERACION, "Gastos generales del proyecto", "Servicios básicos", "Agua"),
    "32200": ("gasto", OPERACION, "Gastos generales del proyecto", "Servicios básicos", "Gas"),
    "32300": ("gasto", OPERACION, "Gastos generales del proyecto", "Servicios básicos", "Teléfonos y fax"),

    "35020": ("gasto", OPERACION, "Subcontratos", "Asesorías", "Servicios de asesoría"),
    "33501": ("gasto", OPERACION, "Seminarios, publicaciones y difusión", "", "Publicidad y difusión"),
    "33503": ("gasto", OPERACION, "Seminarios, publicaciones y difusión", "", "Servicio de impresión y reproducción"),
    "33504": ("gasto", OPERACION, "Seminarios, publicaciones y difusión", "", "Otras publicaciones"),
    "33505": ("gasto", OPERACION, "Seminarios, publicaciones y difusión", "", "Pago de tasas de publicaciones de investigación"),
    "35700": ("gasto", OPERACION, "Seminarios, publicaciones y difusión", "Suscripciones", "Suscripción de revistas y diarios"),
    "40301": ("gasto", OPERACION, "Software", "Licencias", "Licencias computacionales"),
    "40302": ("gasto", OPERACION, "Software", "", "Software"),
    "34600": ("gasto", OPERACION, "Software", "Servicios TI", "Servicios computacionales"),

    # --- equipos ------------------------------------------------------------
    "40207": ("gasto", EQUIPOS, "", "Laboratorio", "Equipos de laboratorio"),
    "40208": ("gasto", EQUIPOS, "", "", "Máquinas y equipos"),
    "40201": ("gasto", EQUIPOS, "", "Computación", "Equipos computacionales"),
    "40202": ("gasto", EQUIPOS, "", "Computación", "Impresoras"),
    "40203": ("gasto", EQUIPOS, "", "Computación", "Scanner"),
    "40300": ("gasto", EQUIPOS, "", "Bienes inventariables", "Otros bienes inventariables"),
    "40205": ("gasto", EQUIPOS, "", "Mobiliario", "Muebles de oficina"),
    "40206": ("gasto", EQUIPOS, "", "Mobiliario", "Muebles de laboratorio"),
    "40218": ("gasto", EQUIPOS, "", "Mobiliario", "Muebles y equipos de clínicas"),
    "40209": ("gasto", EQUIPOS, "", "Repuestos", "Repuestos de máquinas y equipos"),
    "41001": ("gasto", EQUIPOS, "", "Vehículos", "Vehículos"),

    # --- infraestructura ----------------------------------------------------
    "35101": ("gasto", INFRA, "", "Obras", "Pintura de edificios"),
    "35123": ("gasto", INFRA, "", "Obras", "Instalaciones fijas y accesorios"),
    "35107": ("gasto", INFRA, "", "Mantención", "Reparación y mantención de inmuebles"),
    "35108": ("gasto", INFRA, "", "Mantención", "Mantención y reparación de oficinas"),
    "35118": ("gasto", INFRA, "", "Mantención", "Otras mantenciones y reparaciones de docencia"),

    # --- otras transferencias ----------------------------------------------
    "38900": ("gasto", TRANSF, "", "Transferencias", "Otras transferencias (rubro propio por decisión DITT)"),
    "38904": ("gasto", TRANSF, "", "Contraparte", "Transferencias a contraparte de proyectos con financiamiento de terceros"),
    "38914": ("gasto", TRANSF, "", "Ayuda a terceros", "Ayuda a terceros"),
    "38915": ("gasto", TRANSF, "", "Emprendedores", "Remesas a emprendedores"),
    "38916": ("gasto", TRANSF, "", "Universidades", "Transferencias a otras universidades"),
    "38800": ("gasto", TRANSF, "", "Estudiantes", "Aportes para actividades estudiantiles"),
}


def main():
    import openpyxl  # noqa: F401  (solo para dejar constancia de la dependencia)
    nombres = {}
    with open(RAW / "dim_item.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter=";"):
            nombres[row["cod_sitm"]] = (row.get("des_item") or "").strip()

    filas = []
    for cod, (ver, rubro, sub, etiq, crit) in M.items():
        filas.append(dict(cod_sitm=cod, nombre=nombres.get(cod, ""), veredicto=ver,
                          rubro=rubro, subitem=sub, etiqueta=etiq, criterio=crit,
                          version=VERSION, autor="DITT · apoyo financiero"))
    with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()), delimiter=";")
        w.writeheader(); w.writerows(filas)

    gasto = [f for f in filas if f["veredicto"] == "gasto"]
    print(f"taxonomía {VERSION}: {len(filas)} ítems · {len(gasto)} gasto · {len(filas)-len(gasto)} paso")
    from collections import Counter
    for r, n in Counter(f["rubro"] for f in gasto).most_common():
        print(f"  {n:2d} ítems · {r}")


if __name__ == "__main__":
    main()
