# Arquitectura de Linaje y Trazabilidad de Datos (Entrega E2)

**Proyecto:** Observatorio de Datos — Comercio Minorista en Puestos Escolares (Colima, México)  
**Módulo de linaje:** `src/pipeline/linaje.py`  
**Artefactos generados:** `datos/linaje/manifiesto_bronce.parquet` y `datos/linaje/tabla_linaje.parquet`

---

## 1. Esquema de Columnas de Linaje en Capa Oro

Cada registro de las 5 tablas en `datos/oro/` (las 2 tablas macroeconómicas de E1 y las 3 tablas geoespaciales agregadas de E2) conserva intactos sus valores analíticos e incorpora 9 columnas estandarizadas de trazabilidad:

| Columna | Tipo | Descripción |
| :--- | :---: | :--- |
| `id_registro` | `STRING` | Identificador determinista único (ej. `oro:matriz_mensual_macro:2026-09-01`, `oro:densidad_comercial_escolar_municipios:002`). |
| `fuente` | `STRING` | Institución(es) pública(s) fuente(s) que alimentan la fila (`INEGI`, `Banxico`, `INEGI+Banxico`, `INEGI_DENUE+INEGI_MarcoGeo`). |
| `archivos_origen_bronce` | `STRING` | Nombre(s) exacto(s) de los archivo(s) crudo(s) en `datos/bronce/` separados por `;`. |
| `fecha_ingesta` | `STRING` | Timestamp ISO-8601 UTC más reciente de la ingesta cruda en Bronce. |
| `n_registros_origen` | `INT64` | Número exacto de observaciones crudas (o establecimientos + polígono) que integran la fila. |
| `fecha_min_origen` | `STRING` | Fecha más antigua de los registros de origen (en DENUE: `fecha_alta` mínima). |
| `fecha_max_origen` | `STRING` | Fecha más reciente de los registros de origen (en DENUE: `fecha_alta` máxima). |
| `hash_captura` | `STRING` | SHA-256 del archivo de Bronce o hash SHA-256 compuesto determinista si participan múltiples capturas. |
| `run_id` | `STRING` | Identificador único de la ejecución del pipeline (`run_YYYYMMDD_HHMMSS_<hex>`). |

Además, `datos/linaje/tabla_linaje.parquet` almacena la columna `ids_origen_json` con la lista completa de identificadores crudos (`cve_serie@fecha` para series diarias/mensuales y `denue_ids` + `marco_cvegeo` para agregados espaciales), permitiendo reconstruir matemáticamente cada promedio o conteo desde los datos crudos sin publicar puntos individuales en Oro.

---

## 2. Cobertura del Registro de Linaje (`datos/linaje/tabla_linaje.parquet`)

| Capa | Tabla | Registros Rastreados |
| :--- | :--- | :---: |
| `oro` | `comparativa_sectores` | 1,614 |
| `oro` | `densidad_comercial_escolar_ageb` | 487 |
| `oro` | `densidad_comercial_escolar_localidad` | 26 |
| `oro` | `densidad_comercial_escolar_municipios` | 10 |
| `oro` | `matriz_mensual_macro` | 538 |
| `plata` | `denue_colima_plata` | 4,504 |
| `plata` | `tabla_plata_long` | 11,645 |
| `plata` | `tipo_cambio_mensual` | 421 |
| **Total** | **8 tablas (3 Plata + 5 Oro)** | **19,245** |

---

## 3. Manifiesto de Archivos Crudos en Bronce (`datos/linaje/manifiesto_bronce.parquet`)

| Archivo Crudo | Fuente | Fecha de Ingesta (UTC) | Tamaño | SHA-256 (prefijo) |
| :--- | :--- | :---: | :---: | :---: |
| `banxico_series_raw.json` | Banxico (API SIE) | `2026-11-08T21:27:16.115008+00:00` | 1,046,110 B | `936960c92aac8da9...` |
| `banxico_series_raw_20261108_213139.json` | Banxico (API SIE) | `2026-11-08T21:31:53.768443+00:00` | 1,045,994 B | `d43fbdc994f3dc42...` |
| `banxico_series_raw_20261108_215617.json` | Banxico (API SIE) | `2026-11-08T21:56:30.845552+00:00` | 969,701 B | `24ac1569bdcf0ace...` |
| `banxico_series_raw_20261108_220128.json` | Banxico (API SIE) | `2026-11-08T22:01:47.192553+00:00` | 969,701 B | `c7f9b2d49a02d4a2...` |
| `banxico_series_raw_20261108_235900.json` | Banxico (API SIE) | `2026-11-08T23:59:15.253287+00:00` | 969,701 B | `c8864b2a99445180...` |
| `banxico_series_raw_20261109_013425.json` | Banxico (API SIE) | `2026-11-09T01:34:40.897444+00:00` | 969,701 B | `2eb69d7f03b0c6b7...` |
| `banxico_series_raw_20261109_214741.json` | Banxico (API SIE) | `2026-11-09T21:47:59.720710+00:00` | 969,914 B | `29b962e278601c3b...` |
| `banxico_series_raw_20261116_212859.json` | Banxico (API SIE) | `2026-11-16T21:29:15.444258+00:00` | 970,322 B | `320a87b1772b8025...` |
| `inegi_inpc_raw.json` | INEGI (API BIE-BISE INPC) | `2026-11-08T21:27:14.622753+00:00` | 356,291 B | `b896ed5de3d83a9f...` |
| `inegi_inpc_raw_20261108_213139.json` | INEGI (API BIE-BISE INPC) | `2026-11-08T21:31:39.006621+00:00` | 335,530 B | `9cea78e2eb3dbdc4...` |
| `inegi_inpc_raw_20261108_215617.json` | INEGI (API BIE-BISE INPC) | `2026-11-08T21:56:17.606992+00:00` | 523,032 B | `9e8e50ba2690b5a9...` |
| `inegi_inpc_raw_20261108_220128.json` | INEGI (API BIE-BISE INPC) | `2026-11-08T22:01:28.895971+00:00` | 681,982 B | `c83a0f8de99bdf74...` |
| `inegi_inpc_raw_20261108_235900.json` | INEGI (API BIE-BISE INPC) | `2026-11-08T23:59:00.301922+00:00` | 681,982 B | `df3b4c0fbeb4e505...` |
| `inegi_inpc_raw_20261109_013425.json` | INEGI (API BIE-BISE INPC) | `2026-11-09T01:34:25.313920+00:00` | 681,982 B | `53165143e5efaf3f...` |
| `inegi_inpc_raw_20261109_214741.json` | INEGI (API BIE-BISE INPC) | `2026-11-09T21:47:41.027342+00:00` | 683,166 B | `4fbccd355b05f482...` |
| `inegi_inpc_raw_20261116_212859.json` | INEGI (API BIE-BISE INPC) | `2026-11-16T21:28:59.755795+00:00` | 683,166 B | `c23b9224c3b1557a...` |
| `denue_colima_raw_20261120_203817.zip` | INEGI (DENUE Colima) | `2026-11-20T20:38:53.786920+00:00` | 3,788,726 B | `948e292e567ce16a...` |
| `marco_geoestadistico_colima_municipios_20261120_203817.geojson` | INEGI (Marco Geoestadístico GAIA) | `2026-11-20T20:38:57.923324+00:00` | 517,085 B | `a345fd583e0b9c35...` |

---

## 4. Tres Ejemplos Reales de Rastreo (`trazar(id_registro)`)

### Ejemplo 1 — Fila agregada multivariada en `matriz_mensual_macro` (E1)
* **Consulta:** `trazar("oro:matriz_mensual_macro:2026-09-01")`
* **Valores en Capa Oro:** `inpc_mercancias = 152.518196161`, `tipo_cambio_fix_promedio = 17.264019`
* **Fuente:** `Banxico+INEGI` | **Run ID:** `run_20261121_004546_95e121ac`
* **Registros de origen (`n_registros_origen`):** **26** (5 observaciones mensuales de INPC + 21 cotizaciones diarias hábiles de `SF43718` en septiembre de 2026)
* **Rango de fechas de origen:** `2026-09-01` a `2026-09-30`
* **Archivos crudos en Bronce:**
  - `datos/bronce/banxico_series_raw_20261116_212859.json` (SHA-256: `320a87b1772b8025...`, ingesta: `2026-11-16T21:29:15.444258+00:00`)
  - `datos/bronce/inegi_inpc_raw_20261116_212859.json` (SHA-256: `c23b9224c3b1557a...`, ingesta: `2026-11-16T21:28:59.755795+00:00`)
* **Muestra de `ids_origen` guardados para reconstrucción:** `['910392@2026-09-01', '910394@2026-09-01', '910395@2026-09-01', '910397@2026-09-01', 'SP74625@2026-09-01', 'SF43718@2026-09-01', 'SF43718@2026-09-02', 'SF43718@2026-09-03']` ... (26 en total)

### Ejemplo 2 — Fila sectorial en `comparativa_sectores` (E1)
* **Consulta:** `trazar("oro:comparativa_sectores:910394:2026-09-01")`
* **Valor en Capa Oro:** `sector = Mercancías`, `nivel_indice = 152.518196161`, `var_mensual_pct = 0.1351%`
* **Fuente:** `INEGI` | **Registros de origen:** `1` (`['910394@2026-09-01']`)
* **Archivo crudo en Bronce:** `datos/bronce/inegi_inpc_raw_20261116_212859.json`
* **Fecha de ingesta:** `2026-11-16T21:28:59.755795+00:00` | **SHA-256:** `c23b9224c3b1557af898679dc3d623215dad8036aa4a3878ea993faa191c979d`

### Ejemplo 3 — Fila agregada municipal geoespacial en `densidad_comercial_escolar_municipios` (E2)
* **Consulta:** `trazar("oro:densidad_comercial_escolar_municipios:002")` (Municipio de **Colima**, clave `002`)
* **Valores en Capa Oro:** `n_escuelas_basicas = 194`, `n_abarrotes = 702`, `n_dulces = 28`, `n_helados_paletas = 31`, `comercios_por_escuela = 3.9227`, `area_km2_continental = 741.7185`
* **Fuente:** `INEGI_DENUE+INEGI_MarcoGeo`
* **Registros de origen (`n_registros_origen`):** **956** (955 establecimientos DENUE + 1 polígono oficial `06002` del Marco Geoestadístico)
* **Rango `fecha_alta` DENUE:** `2010-07` a `2026-04`
* **Archivos crudos en Bronce:**
  - `datos/bronce/denue/denue_colima_raw_20261120_203817.zip` (SHA-256: `948e292e567ce16a...`)
  - `datos/bronce/marco_geoestadistico/marco_geoestadistico_colima_municipios_20261120_203817.geojson` (SHA-256: `a345fd583e0b9c35...`)
* **Muestra de `denue_ids` para reconstrucción:** `['10002861', '10012271', '10016269', '10023814', '10031399', '10038707', '10043869', '10045969']` ... (955 IDs en total)

---

## 5. Resultado de la Auditoría Automatizada de Muestra Aleatoria

La función `verificar_muestra_linaje(n_por_tabla=4, seed=42)` muestreó **20 filas aleatorias** a través de las 5 tablas de Capa Oro, abrió directamente los archivos crudos en `datos/bronce/` y reconstruyó sus valores desde cero:

* **Verificaciones exitosas:** **20 / 20 (100.0%)**
* **Discrepancias detectadas:** **0**
