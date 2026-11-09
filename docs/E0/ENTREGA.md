# Documento de Entrega E0 - Observatorio de Datos

**Proyecto:** Observatorio de Datos - Comercio minorista de dulces, botanas y bebidas/helados fríos en puestos escolares  
**Región:** Colima, Colima, México  
**Materia:** Ingeniería de Datos (ATD-2602)  
**Semestre:** 7mo Semestre, Ago-Dic 2026  
**Alumno:** Yair Alejandro Molina Díaz (No. Control: 23460519)  
**Institución:** Tecnológico Nacional de México — Instituto Tecnológico de Colima  
**Docente:** Prof. Armando Román Gallardo Heredia  
**Fecha:** Noviembre 2026  

---

## 1. Objetivo de la Entrega E0

Establecer los cimientos metodológicos, éticos, legales y de infraestructura de datos para el Observatorio de Datos enfocado en el comercio minorista de puestos escolares en Colima. La entrega garantiza la trazabilidad ética del proyecto, la ingesta automatizada a la capa bronce desde APIs oficiales (INEGI y Banxico), el aseguramiento de series continuas con más de 36 observaciones mensuales y la implementación de mecanismos de medición de calidad basados en PSP (Personal Software Process).

---

## 2. Matriz de Entregables del Repositorio

| Entregable | Ruta en el Repositorio | Estado Real | Descripción y Evidencia |
| :--- | :--- | :---: | :--- |
| **Propuesta del Observatorio** | [`docs/E0/propuesta.md`](propuesta.md) | **Listo** | Documento académico formal integral (4 secciones: ficha técnica institucional, entrevista de campo estructurada con comerciante escolar, 3 preguntas analíticas E1-E3 conectadas con la necesidad y plan de datos con análisis ético-legal exhaustivo). Extensión de 4 páginas (~1,800 palabras). |
| **Análisis Ético y Legal** | [`docs/E0/analisis_etico_legal.md`](analisis_etico_legal.md) | **Listo** | Revisión profunda de términos de libre uso de INEGI y Banxico SIE, respeto a directivas de `robots.txt`, anonimización de la comerciante y políticas de rate limiting (pausas éticas de 2.0s y cabecera User-Agent). |
| **Series Seleccionadas** | [`docs/E0/series_seleccionadas.md`](series_seleccionadas.md) | **Listo** | Catálogo oficial verificado, mapeo literal de claves `CL_INDICATOR`, unidades oficiales de medida, descarte justificado de series no aptas (628xxx y 7xxxxx) y análisis de cobertura regional. |
| **Extractor Automatizado** | [`src/extractor.py`](../../src/extractor.py) | **Listo** | Código robusto en Python (solo biblioteca estándar y `requests`). Lee tokens de variables de entorno, aplica pausas éticas, cabecera `User-Agent` identificable y almacena respuestas crudas en `datos/bronce/` con timestamp. |
| **Workflow de GitHub Actions** | [`.github/workflows/captura.yml`](../../.github/workflows/captura.yml) | **Listo** | Flujo CI/CD automatizado con ejecución semanal programada (lunes 12:00 UTC) y manual (`workflow_dispatch`). Permisos limitados a `contents: write`, checkout sobre `main`, inyección segura de Secrets y commit/push condicional. |
| **Serie Histórica ($\ge 36$ periodos)** | [`datos/bronce/`](../../datos/bronce/) | **Listo** | Archivos crudos JSON descargados y preservados. Incluye las series activas `910392`, `910394`, `910395`, `910397` (INEGI) y `SP74625`, `SF43718` (Banxico) con 537 a 8,794 observaciones continuas hasta 2026 y **0 meses faltantes**. |
| **Script de Validación de Calidad** | [`src/validar_bronce.py`](../../src/validar_bronce.py) | **Listo** | Script que audita sintaxis JSON, metadatos obligatorios de auditoría, presencia de observaciones y continuidad mensual ininterrumpida en la capa bronce. |
| **Objetivos de Calidad** | [`calidad/objetivos.md`](../../calidad/objetivos.md) | **Listo** | Definición formal de 3 objetivos medibles (100% verificación literal de metadatos, 0 fallos de CI en 4 semanas, 0 meses faltantes). |
| **Registros PSP de Tiempo** | [`calidad/tiempo-yair-molina.csv`](../../calidad/tiempo-yair-molina.csv) | **Listo** | Registro formal de bitácora PSP con 8 fases y actividades completadas (Planeación, Entrevista, Redacción, Diseño, Desarrollo y Verificación). |
| **Registros PSP de Defectos** | [`calidad/defectos-yair-molina.csv`](../../calidad/defectos-yair-molina.csv) | **Listo** | Registro formal de 7 defectos detectados y corregidos (D01 a D07) con trazabilidad de fase de origen, fase de detección, tipo y descripción técnica. |

---

## 3. Resumen Técnico de las Series Oficiales Activas

Para mayor detalle sobre el catálogo completo y justificación técnica, consultar [docs/E0/series_seleccionadas.md](series_seleccionadas.md).

* **INEGI (INPC Base 2018, Actualización 2024 - Tema 189113, Fuente 3371):**
  - `910392` (`Índice general`): 693 observaciones (`1969/01` a `2026/09`, 0 faltantes).
  - `910394` (`Mercancías`): 537 observaciones (`1982/01` a `2026/09`, 0 faltantes).
  - `910395` (`Servicios`): 537 observaciones (`1982/01` a `2026/09`, 0 faltantes).
  - `910397` (`Agropecuarios`): 537 observaciones (`1982/01` a `2026/09`, 0 faltantes).
* **Banco de México (SIE API):**
  - `SP74625` (`Índice de Precios al Consumidor Subyacente Mensual`): 693 observaciones (`1969/01` a `2026/09`, 0 faltantes).
  - `SF43718` (`Tipo de cambio Pesos por Dólar E.U.A. FIX`): 8,794 observaciones (`1991/11` a `2026/11`, frecuencia diaria hábil bancaria).

---

## 4. Distinción Metodológica: Hechos Oficiales vs. Hipótesis

* **Hecho oficial documentado:**  
  La sustitución de la canasta del INPC por la *"Actualización de Canasta y Ponderadores 2024"* (Tema `189113`) en agosto de 2024 por parte del INEGI.
* **Hecho oficial observado:**  
  Las series legadas `628xxx` terminan de forma fija en `2024/07` y carecen del registro de `2024/06`. Las series activas `910xxx` incluyen continuidad plena y están actualizadas hasta septiembre de 2026.
* **[HIPÓTESIS TÉCNICA]:**  
  Se postula como hipótesis técnica que la omisión de `2024/06` en las series `628xxx` se originó por un error de sincronización o corte prematuro en el volcado de las tablas históricas del backend del INEGI al momento de archivar esa rama legada y dar de alta la canasta 2024.
* **[HIPÓTESIS ECONÓMICA]:**  
  Se postula como hipótesis económica que el subíndice de *Mercancías* (`910394`) y el *Tipo de cambio FIX* (`SF43718`) servirán como variables explicativas directas de los costos en insumos comercializados en clubes de mayoreo (Sam's Club Colima).

---

## 5. Instrucciones de Despliegue y Pruebas en CI/CD

1. **Configuración de Secretos en GitHub:**
   En el repositorio remoto ir a **Settings > Secrets and variables > Actions > Secrets**:
   - `INEGI_API_TOKEN`
   - `BANXICO_API_TOKEN`
2. **Ejecución del Workflow Automatizado:**
   - El workflow [`.github/workflows/captura.yml`](../../.github/workflows/captura.yml) corre de forma automática cada lunes a las 12:00 UTC.
   - Para probarlo de forma manual, ir a la pestaña **Actions > Captura Automática Bronce > Run workflow** seleccionando la rama `main`.
