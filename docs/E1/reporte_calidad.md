# Reporte de Control de Calidad de Datos (Entrega E1)

**Fecha de Auditoría:** 2026-11-13 20:24:43 UTC  
**Proyecto:** Observatorio de Datos - Puestos Escolares de Colima  
**Motor de Validación:** Pandera (Lazy Evaluation) & Pipeline Estadístico  

---

## 1. Conciliación Contable y Trazabilidad de Registros

Para garantizar que ningún registro sea eliminado en silencio, el pipeline audita el 100% de los datos de entrada:

| Métrica | Conteo de Filas | Porcentaje | Destino / Estado |
| :--- | :---: | :---: | :--- |
| **Total de Registros Crudos de Entrada** | **69,249** | **100.00%** | Ingesta desde `datos/bronce/` |
| **Registros Aprobados en Capa Plata** | **11,635** | **16.80%** | Destino `datos/plata/` |
| **Registros Rechazados en Cuarentena** | **57,614** | **83.20%** | Destino `datos/cuarentena/` |
| **Discrepancia Contable** | **0** | **0.00%** | Conciliación exacta $\checkmark$ |

$$\text{Total Entrada } (69,249) = \text{Plata } (11,635) + \text{Cuarentena } (57,614)$$

---

## 2. Segregación en Cuarentena: Descartes por Diseño vs. Reglas de Calidad

Todo registro no conforme fue aislado con trazabilidad auditable (timestamp, regla violada, motivo y payload original):

### A. Descartes por Diseño Metodológico e Integración
Registros excluidos por reglas de arquitectura de datos (resolución de duplicados temporales, depuración de series legadas y exclusión de faltantes estructurales no numéricos):

| Regla de Ingesta / Diseño | Descripción del Motivo | Conteo | Acción Realizada |
| :--- | :--- | :---: | :--- |
| `duplicado_captura_anterior` | Duplicados de capturas anteriores; descartados en favor de la captura más reciente | 53,030 | Aislado en Cuarentena |
| `serie_no_seleccionada` | Series legadas ('628xxx' y 'SP1') descartadas formalmente por desactualización o duplicidad | 3,648 | Aislado en Cuarentena |
| `valor_no_numerico_ne` | Faltante estructural ('N/E') en serie SP74625 previo a 1982 (hipótesis: el índice no existía), no imputado | 936 | Aislado en Cuarentena |
| **Subtotal Descartes por Diseño** | | **57,614** | |


### B. Registros Inválidos por Reglas de Calidad (Puerta de Calidad Pandera)
Evaluación estricta de tipos de datos, valores numéricos positivos, rangos plausibles, claves autorizadas y unicidad de fechas:

| Regla de Calidad Evaluada | Condición / Contrato Pandera | Violaciones en Datos Reales | Estado |
| :--- | :--- | :---: | :---: |
| Tipo de dato de fecha | Formato Datetime ISO | 0 | Conforme |
| Tipo de dato de valor | Flotante numérico continuo (`float64`) | 0 | Conforme |
| Valores positivos | Valor estrictamente mayor a 0 (`valor > 0`) | 0 | Conforme |
| Rango plausible de índice | Valor dentro de rango plausible (`0 < valor < 1,000`) | 0 | Conforme |
| Rango plausible de tipo de cambio | Valor dentro de rango plausible (`0 < valor < 100`) | 0 | Conforme |
| Claves autorizadas | `cve_serie` dentro del catálogo oficial de 6 series | 0 | Conforme |
| Unicidad de periodos | Clave única compuesta `(cve_serie, fecha)` sin duplicados | 0 | Conforme |
| **Total Violaciones en Datos Reales** | | **0** | **100% Conforme** |

> **Nota de Auditoría:** Con los datos reales de las capturas oficiales **no hubo ninguna violación de tipo o rango**. 
> La totalidad de las 11,635 observaciones candidatas cumplieron estrictamente el esquema de Pandera. 
> Las violaciones de tipo, rango absurdo (>1000), valores negativos y claves inexistentes se probaron y verificaron 
> exitosamente mediante casos sintéticos aislados dentro de la suite de pruebas unitarias (`tests/test_pipeline.py`).

---

## 3. Calidad de Series Aprobadas en Capa Plata

| Clave | Nombre Literal Oficial | Fuente | Observaciones | Nulos | Meses Faltantes | Periodo Inicio | Periodo Fin |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `910392` | Índice general | INEGI | 693 | 0 | 0 | 1969-01-01 | 2026-09-01 |
| `910394` | Mercancías | INEGI | 537 | 0 | 0 | 1982-01-01 | 2026-09-01 |
| `910395` | Servicios | INEGI | 537 | 0 | 0 | 1982-01-01 | 2026-09-01 |
| `910397` | Agropecuarios | INEGI | 537 | 0 | 0 | 1982-01-01 | 2026-09-01 |
| `SF43718` | Tipo de cambio FIX | Banxico | 8,794 | 0 | 0 | 1991-11-12 | 2026-11-06 |
| `SP74625` | Subíndice subyacente del INPC | Banxico | 537 | 0 | 0 | 1982-01-01 | 2026-09-01 |

---

## 4. Auditoría de Atípicos y Ruido Estadístico

Los niveles de precios no son estacionarios; por tanto, los atípicos se calcularon sobre **variaciones porcentuales** mensuales:

| Clave | Nombre Literal | IQR (1.5x) | Z-score MAD (>3.0) | Isolation Forest | Decisión Técnica |
| :---: | :--- | :---: | :---: | :---: | :--- |
| `910392` | Índice general | 86 | 100 | 21 | **Conservar** (Eventos macroeconómicos reales documentados) |
| `910394` | Mercancías | 85 | 109 | 17 | **Conservar** (Eventos macroeconómicos reales documentados) |
| `910395` | Servicios | 60 | 129 | 17 | **Conservar** (Eventos macroeconómicos reales documentados) |
| `910397` | Agropecuarios | 23 | 22 | 17 | **Conservar** (Eventos macroeconómicos reales documentados) |
| `SF43718` | Tipo de cambio FIX | 555 | 420 | 264 | **Conservar** (Eventos macroeconómicos reales documentados) |
| `SP74625` | Subíndice subyacente del INPC | 78 | 121 | 17 | **Conservar** (Eventos macroeconómicos reales documentados) |

> **Justificación de Conservación:**  

> Los valores extremos detectados en 1987-1988 (hiperinflación previa al Pacto de Solidaridad Económica), 
> 1995 (devaluación de la Crisis del Tequila) y 2020 (choque de oferta por COVID-19) son perturbaciones económicas reales. 
> Recortarlos o eliminarlos sesgaría la variabilidad macroeconómica histórica.
