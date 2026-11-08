# Catálogo Oficial y Series Seleccionadas (Entrega E0)

**Observatorio de Datos:** Comercio minorista de dulces, botanas y bebidas/helados fríos en puestos escolares (Colima, México)  
**Fecha:** Noviembre 2026  
**Fuentes Oficiales:** INEGI (API BIE-BISE v2.0) y Banco de México (API SIE)  

---

## 1. Mapeo Literal del Catálogo Activo del INPC en INEGI (`910392` a `910439`)

Los siguientes nombres y unidades fueron extraídos directamente de los catálogos de metadatos oficiales del INEGI (`CL_INDICATOR`, `CL_UNIT`, `CL_TOPIC`):

| Clave | Nombre Literal (`CL_INDICATOR`) | Unidad Literal (`CL_UNIT`) | Tema / Clasificación (`CL_TOPIC`) |
| :--- | :--- | :--- | :--- |
| **`910392`** | `Índice general` | `Índice base 2018=100` | Mensual / Índice General |
| **`910393`** | `total` | `Índice base 2018=100` | Mensual / Subyacente Total |
| **`910394`** | `Mercancías` | `Índice base 2018=100` | Mensual / Subyacente Mercancías |
| **`910395`** | `Servicios` | `Índice base 2018=100` | Mensual / Subyacente Servicios |
| **`910396`** | `total` | `Índice base 2018=100` | Mensual / No subyacente Total |
| **`910397`** | `Agropecuarios` | `Índice base 2018=100` | Mensual / No subyacente Agropecuarios |
| **`910398`** | `Energéticos y tarifas autorizadas por el gobierno` | `Índice base 2018=100` | Mensual / No subyacente Energéticos |
| **`910399`** | `Índice general` | `Variación Porcentual` | Mensual / Inflación mensual general |
| **`910400`** | `total` | `Variación Porcentual` | Mensual / Inflación mensual subyacente |
| **`910401`** | `Mercancías` | `Variación Porcentual` | Mensual / Inflación mensual mercancías |
| **`910402`** | `Servicios` | `Variación Porcentual` | Mensual / Inflación mensual servicios |
| **`910403`** | `total` | `Variación Porcentual` | Mensual / Inflación mensual no subyacente |
| **`910404`** | `Agropecuarios` | `Variación Porcentual` | Mensual / Inflación mensual agropecuarios |
| **`910405`** | `Energéticos y tarifas autorizadas por el gobierno` | `Variación Porcentual` | Mensual / Inflación mensual energéticos |
| **`910406`** | `Índice general` | `Variación Porcentual` | Mensual / Inflación anualizada general |
| **`910407`** a **`910412`** | `total`, `Mercancías`, `Servicios`, etc. | `Variación Porcentual` | Mensual / Inflación interanual por subíndice |
| **`910413`** a **`910419`** | `Índice general`, `total`, `Mercancías`, etc. | `Variación Porcentual` | Mensual / Inflación acumulada anual |
| **`910420`** a **`910426`** | `Índice general`, `total`, `Mercancías`, etc. | `Índice base 2018=100` | Quincenal / Índice quincenal |
| **`910427`** a **`910433`** | `Índice general`, `total`, `Mercancías`, etc. | `Variación Porcentual` | Quincenal / Inflación quincenal |
| **`910434`** a **`910437`** | *No asignados en API (`HTTP 400`)* | N/A | N/A |
| **`910438`** a **`910439`** | `Índice general`, `total` | `Variación Porcentual` | Quincenal / Inflación quincenal anual |

*Nota metodológica sobre genéricos de alimentos y bebidas:*  
En la estructura de la API activa (Tema 189113), **no existen claves denominadas literalmente "alimentos" o "bebidas"**. El rubro de alimentos procesados y bebidas de consumo está integrado formalmente dentro del subíndice literal **`Mercancías`** (`910394`), y los alimentos primarios en **`Agropecuarios`** (`910397`).

---

## 2. Tabla Final de Series Seleccionadas y Verificadas en Vivo

Todas las series fueron descargadas en `datos/bronce/` y validadas por `src/validar_bronce.py`. Cada una cuenta con **0 meses faltantes** y supera con creces el requerimiento mínimo de 36 periodos:

| Clave | Nombre Literal Oficial | Unidad Oficial | Institución Fuente | Observaciones | Primera Fecha | Última Fecha | Meses Faltantes | Cumple $\ge 36$ |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`910392`** | `Índice general` | `Índice base 2018=100` | INEGI (INPC) | **693** | `1969/01` | `2026/09` | **0 (Ninguno)** | **SÍ** |
| **`910394`** | `Mercancías` | `Índice base 2018=100` | INEGI (INPC) | **537** | `1982/01` | `2026/09` | **0 (Ninguno)** | **SÍ** |
| **`910395`** | `Servicios` | `Índice base 2018=100` | INEGI (INPC) | **537** | `1982/01` | `2026/09` | **0 (Ninguno)** | **SÍ** |
| **`910397`** | `Agropecuarios` | `Índice base 2018=100` | INEGI (INPC) | **537** | `1982/01` | `2026/09` | **0 (Ninguno)** | **SÍ** |
| **`SP74625`** | `Subíndice subyacente del INPC` | `Índice base 2018=100` | Banxico (SIE) | **693** | `01/01/1969` | `01/09/2026` | **0 (Ninguno)** | **SÍ** |
| **`SF43718`** | `Tipo de cambio FIX` | `Pesos por Dólar` | Banxico (SIE) | **8,794** | `12/11/1991` | `06/11/2026` | *Días hábiles* | **SÍ** |

*Criterio de desduplicación:*  
Se eliminó la serie `SP1` de Banxico porque replica el Índice General de INEGI (`910392`), evitando redundancias innecesarias.

---

## 3. Descarte de Series Industriales `7xxxxx` y Legadas `628xxx`

1. **Series de la industria manufacturera (`706027`, `706309`, `704122`, etc.):**  
   Fueron descartadas permanentemente tras verificar en los metadatos oficiales del INEGI que miden **variables laborales** (horas trabajadas por obreros y número de personas ocupadas fijas de la muestra), y **no** precios al consumidor ni volumen físico de producción.
2. **Series legadas `628xxx`:**  
   Fueron descartadas debido a que corresponden a la rama de la canasta anterior que el INEGI congeló en julio de 2024 (`2024/07`) y a que presentan la omisión del mes de junio de 2024 (`2024/06`).

---

## 4. Estado de Series Desagregadas por Ciudad / Región (Colima)

* **En el INPC del INEGI:**  
  La consulta por entidad federativa o ciudad (claves `06` para Colima o `14` para Jalisco) devuelve error `HTTP 400 Bad Request` en el endpoint REST del INPC. En la API activa de desarrolladores, el INPC únicamente se disemina con cobertura geográfica nacional (`00`).
* **En el SIE de Banxico:**  
  En el catálogo público de la API REST del SIE, Banxico solo mantiene actualizadas las series macroeconómicas generales (`SP1`, `SP74625`, `SF43718`). Las series de inflación por ciudad corresponden a tabulados históricos previos a la transferencia constitucional del INPC a INEGI (2011) y no se encuentran activas por endpoint individual para Colima.

---

## 5. Sustento Documental vs. Hipótesis

Para cumplir con el principio de transparencia científica y auditoría de datos:

* **Hecho verificado documentalmente:**  
  El INEGI formalizó la sustitución de la canasta base 2018 por la *"Actualización de Canasta y Ponderadores 2024"* (registrada bajo el Tema oficial `189113`), migrando el consumo activo de la API hacia la serie `910392` y subíndices afines.
* **Hecho verificado observacionalmente:**  
  Las series legadas `628xxx` se detuvieron en julio de 2024 (`2024/07`), mientras que las series activas `910xxx` continúan sin interrupción mes a mes hasta septiembre de 2026.
* **[HIPÓTESIS]:**  
  Se postula como hipótesis técnica que la ausencia del mes de junio de 2024 (`2024/06`) en la familia `628xxx` obedeció a una desincronización o error de corte en el volcado de las tablas históricas del backend del INEGI al momento de archivar esa rama legada y activar la actualización 2024.
