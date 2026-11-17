# Metodología del tablero FIUT

**Corte de datos:** 16-11-2026 · último movimiento del libro disponible en la copia local.
**Fuentes:** copia local del libro FIN21 (`fin21_local`), paquete FIU v2 (hoja «Proyectos», 124 filas) y
cartola ANID (`v_cruce_anid_linea`).

## 1. Universo

- Los **124 proyectos** del paquete v2 (122 códigos distintos; dos filas repiten código con centros de
  costo escritos distinto).
- **112 centros de costo** distintos con movimientos en el libro. Siete filas del paquete no tienen C.C.
  utilizable: cinco sin dato y dos con la celda convertida en fecha (`16PTECFS-66647` y una fila `N/A`).
  Esos proyectos no pueden cruzar contra el libro y se declaran así.

## 2. Medida

Todas las cifras de gasto son **egresos registrados**: movimientos con `cod_tipmov` entre 20 y 25 en el
centro de costo, en pesos, sin inferir signos. Es el monto que el libro tiene registrado, no una depuración
a pagado.

- `devengado` y `percibido` existen solo para ingresos (tipos 10 a 15).
- `comprometido` y `pagado` se leen por separado: un movimiento tipo 20 suma a los dos, por eso la medida
  principal es el monto registrado.

## 3. Cuentas de paso

Trece ítems no son gasto y se excluyen de todos los totales, mostrados aparte:

| Ítem | Nombre | Monto (MM) |
|---|---|---:|
| 32800 | Solicitud electrónica de compras | 5.176,2 |
| 52001 | Obligaciones pendientes | 2.391,1 |
| 36201 | Fondos por rendir | 636,7 |
| 36202 | Importaciones | 531,6 |
| 38901 | Transferencias internas | 205,8 |
| 38912 | Devolución proyectos sector público | 184,8 |
| 32706 | Presupuesto consumo corriente | 177,9 |
| 38913 | Resolución remesas internacionales | 135,7 |
| 83300 | Boletas de garantía | 92,4 |
| 37401 | Solicitud beca alumno laborante | 88,8 |
| 41501 | Proyecto de inversión | 33,8 |
| 38801 | Solicitud ayuda económica a estudiantes | 3,4 |
| 25300 | Recuperación de ingresos de años anteriores | 0,0 |

Total: **$9.658,2 MM**, el 41 % del registrado bruto. Sumarlos al gasto infla los totales y hace que el
tablero no cuadre contra ninguna pantalla del sistema.

**32706 queda como cuenta de paso por decisión técnica pendiente de confirmar**: si se reclasifica a
Materiales fungibles, el gasto clasificable sube $177,9 MM.

## 4. Taxonomía

La clasificación sigue el catálogo ANID, con tres niveles: **rubro → subítem → etiqueta**.

Rubros (5 con datos de 7 definidos): Gastos en personal · Gastos de operación · Equipos ·
Otras transferencias · Infraestructura. Sin movimientos en este corte: Gastos de administración superior y
Gastos generales.

Decisiones de clasificación tomadas con la Dirección:

- **Otras transferencias es rubro propio** (ítem 38900, $782,9 MM), no un subítem de operación.
- **Alimentos y bebidas** va a Gastos generales del proyecto con etiqueta «Alimentación».
- **Arriendo de vehículos** va a Gastos generales del proyecto con etiqueta «Arriendo de vehículo»; no se
  suma a Pasajes.
- **Becas de alumnos laborantes** va a Personal / Incentivos.
- **Pasajes y viáticos** quedan separados en el nivel 2 y se pueden agrupar como traslados.

Detalle ítem por ítem en `data/taxonomia_item.csv` y en `docs/TABLA_EQUIVALENCIA.md`.

## 5. Declarado

Solo **61 de los 124 proyectos** tienen cartola en el portal ANID. Los demás financiadores (UFRO interno,
UFRO-INES, CORFO, Comisión Europea, GORE, fundaciones, empresas) no tienen cartola en la base.

- No se compara el total declarado contra la caja del centro de costo: la parte de contraparte no pasa por
  el C.C.
- La cobertura declarada se informa siempre con su N (61 de 124). Lo que no declara se muestra como
  «sin declaración», nunca como cero.

## 6. Proyección

Promedio mensual de los últimos seis meses con movimiento por proyecto, aplicado al saldo
(`adjudicado − ejecutado`) para estimar la fecha de agotamiento, y comparación con la fecha de término del
paquete.

Límites, explícitos en pantalla:

- No modela estacionalidad ni cambios de presupuesto.
- El monto adjudicado es el del paquete FIU, **no** el presupuesto vigente en FIN21.
- Un avance sobre 100 % significa que el C.C. ejecuta más que el monto adjudicado UFRO: habitual cuando hay
  contraparte o el C.C. concentra más de un proyecto.

## 7. Controles de cierre

`etl/40_controles.py` verifica y falla si algo no cuadra:

1. Gasto clasificable + cuentas de paso = registrado bruto del libro, al peso.
2. Cero movimientos sin clasificar.
3. 112 centros de costo con movimientos.
4. 124 filas de proyecto.
5. Cero movimientos huérfanos de proyecto.
6. 61 proyectos con cartola declarada.
7. Ningún subítem con monto negativo.
