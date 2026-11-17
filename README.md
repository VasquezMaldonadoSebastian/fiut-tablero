# Tablero FIUT · cartera, gasto por tipo y proyección

Herramienta de trabajo de la Dirección de Innovación y Transferencia Tecnológica (UFRO) para analizar
la cartera del **Fondo FIU · línea FIUT**: 124 proyectos del paquete y sus 112 centros de costo en FIN21.

Corre en el PC, sobre un archivo DuckDB local. No se conecta a bases institucionales: eso lo hace solo el ETL,
en modo lectura.

## Arrancar

```
EJECUTAR.bat
```

o, desde la carpeta:

```
.venv\Scripts\python.exe -m streamlit run app\app.py
```

Se abre en `http://localhost:8501`.

## Qué muestra

| Vista | Contenido |
|---|---|
| Resumen | KPIs, gasto por rubro, subítems de operación y ejecución por proyecto |
| Registros | una fila por movimiento, con los siete filtros y exportación |
| Proyectos | adjudicado, ejecutado, saldo y avance por proyecto |
| Ítems | los 84 ítems contables clasificados, con su concentración |
| Declarado | cartola ANID de los 61 proyectos que declaran, contra el libro |
| Proyección | promedio de los últimos 6 meses, fecha de agotamiento y brecha con el término |
| Metodología | definiciones, cuentas de paso y límites |

El botón **Excel con filtros** exporta lo que está en pantalla en 7 hojas: parámetros, resumen, subítems
por año, ítems, detalle, cuentas de paso y tabla de equivalencia.

## Cifras del corte 16-11-2026

- Registrado bruto en los 112 C.C.: **$23.413,0 MM** (egresos, tipos 20 a 25).
- Cuentas de paso: **$9.658,2 MM** — no son gasto y se muestran aparte.
- **Gasto clasificable: $13.754,8 MM** en 84 ítems contables.
- Declarado a ANID por los 61 proyectos con cartola: **$12.293,7 MM** en 13.791 líneas.

## Refrescar los datos

```
.venv\Scripts\python.exe etl\00_extraer.py     # lee fin21_local y el paquete, escribe data\raw
.venv\Scripts\python.exe etl\20_cargar.py      # reconstruye data\fiu_fiut.duckdb
.venv\Scripts\python.exe etl\40_controles.py   # cuadres obligatorios
```

Si entra un ítem contable nuevo que no está en la tabla de equivalencia, aparece como **Sin clasificar**
con su monto: no se reparte ni se esconde. Se agrega a `etl/10_taxonomia.py`, se sube la versión y se
reconstruye.

## Estructura

```
etl/     00_extraer · 10_taxonomia · 20_cargar · 30_test_export · 40_controles
app/     app.py (7 vistas) · exportar.py (Excel)
data/    raw/ (CSV de la extracción) · fiu_fiut.duckdb · taxonomia_item.csv
docs/    METODOLOGIA.md · TABLA_EQUIVALENCIA.md
```

## Reglas

- `data/` **no** va a git: contiene RUT de proveedores y glosas del libro.
- El ETL es de solo lectura sobre `fin21_local`.
- Ningún total por tipo de gasto se publica sin que la suma de rubros cuadre con el libro.
- Los códigos de centro de costo se leen como texto y se normalizan solo para el cruce.
