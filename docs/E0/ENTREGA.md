# Documento de Entrega E0 - Observatorio de Datos

**Proyecto:** Observatorio de Datos - Comercio minorista de dulces, botanas y bebidas/helados fríos en puestos escolares  
**Región:** Colima, México  
**Materia:** Ingeniería de Datos  
**Alumno:** Yair Alejandro Molina Díaz  
**Fecha:** Noviembre 2026  

---

## 1. Objetivo de la Entrega E0

Establecer los cimientos metodológicos, éticos, legales y de infraestructura de datos para el Observatorio de Datos enfocado en el comercio minorista de puestos escolares en Colima. La entrega garantiza la trazabilidad ética del proyecto, la ingesta automatizada a la capa bronce desde APIs oficiales (INEGI y Banxico), el aseguramiento de series continuas con más de 36 observaciones mensuales y la implementación de mecanismos de medición de calidad basados en PSP (Personal Software Process).

---

## 2. Matriz de Entregables del Repositorio

| Entregable | Ruta en el Repositorio | Estado Real | Descripción y Evidencia |
| :--- | :--- | :---: | :--- |
| **Propuesta del Observatorio** | [`docs/E0/propuesta.md`](propuesta.md) | **Listo** | Ficha con resumen de entrevista primaria, aprendizajes, sector, región y formulación de preguntas analíticas (E1 pronóstico, E2 factores, E3 grupos). Conservado intacto (hash verificado). |
| **Análisis Ético y Legal** | [`docs/E0/analisis_etico_legal.md`](analisis_etico_legal.md) | **Listo** | Revisión de términos de libre uso de INEGI y Banxico SIE, respeto a directivas de `robots.txt`, anonimización de la entrevistada y políticas de rate limiting. |
| **Series Seleccionadas** | [`docs/E0/series_seleccionadas.md`](series_seleccionadas.md) | **Listo** | Catálogo oficial verificado, nombres literales de `CL_INDICATOR`, unidades oficiales, descarte de series no aptas y análisis de cobertura regional. |
| **Extractor Automatizado** | [`src/extractor.py`](../../src/extractor.py) | **Listo** | Código en Python (solo biblioteca estándar y `requests`). Lee tokens de variables de entorno, aplica pausas éticas de 2.0s, cabecera `User-Agent` identificable y guarda archivos crudos con timestamp. |
| **Workflow de GitHub Actions** | [`.github/workflows/captura.yml`](../../.github/workflows/captura.yml) | **Listo** | Flujo automatizado con ejecución semanal (lunes 12:00 UTC) y manual (`workflow_dispatch`). Permisos limitados a `contents: write`, concurrencia controlada, inyección de Secrets y commit/push condicional. |
| **Serie Histórica ($\ge 36$ periodos)** | [`datos/bronce/`](../../datos/bronce/) | **Listo** | Archivos crudos descargados y validados. Incluye las series activas `910392`, `910394`, `910395`, `910397` (INEGI) y `SP74625`, `SF43718` (Banxico) con 537 a 8,794 observaciones continuas hasta 2026 y **0 meses faltantes**. |
| **Script de Validación de Calidad** | [`src/validar_bronce.py`](../../src/validar_bronce.py) | **Listo** | Script que audita sintaxis JSON, metadatos obligatorios de auditoría, presencia de observaciones y continuidad mensual en la capa bronce. |
| **Objetivos de Calidad** | [`calidad/objetivos.md`](../../calidad/objetivos.md) | **Listo** | Definición formal de 3 objetivos medibles (100% verificación literal, 0 fallos de CI en 4 semanas, 0 meses faltantes). |
| **Registros PSP de Tiempo** | [`calidad/tiempo-yair-molina.csv`](../../calidad/tiempo-yair-molina.csv) | **Pendiente** | Archivo CSV inicializado con encabezados oficiales (`fecha,fase,actividad,inicio,fin,minutos_netos,interrupciones,comentarios`). Pendiente el registro manual de las sesiones de trabajo por parte del alumno. |
| **Registros PSP de Defectos** | [`calidad/defectos-yair-molina.csv`](../../calidad/defectos-yair-molina.csv) | **Pendiente** | Archivo CSV inicializado con encabezados oficiales (`id,fecha,fase_origen,fase_deteccion,tipo,descripcion,minutos_correccion`). Pendiente el registro manual de defectos encontrados durante el desarrollo. |

---

## 3. Resumen Técnico de las Series Oficiales Activas

Para mayor detalle sobre el catálogo completo y justificación técnica, consultar [docs/E0/series_seleccionadas.md](series_seleccionadas.md).

* **INEGI (INPC Base 2018, Actualización 2024 - Tema 189113):**
  - `910392` (`Índice general`): 693 observaciones (`1969/01` a `2026/09`, 0 faltantes).
  - `910394` (`Mercancías`): 537 observaciones (`1982/01` a `2026/09`, 0 faltantes).
  - `910395` (`Servicios`): 537 observaciones (`1982/01` a `2026/09`, 0 faltantes).
  - `910397` (`Agropecuarios`): 537 observaciones (`1982/01` a `2026/09`, 0 faltantes).
* **Banco de México (SIE API):**
  - `SP74625` (`Subíndice subyacente del INPC`): 693 observaciones (`1969/01` a `2026/09`, 0 faltantes).
  - `SF43718` (`Tipo de cambio FIX`): 8,794 observaciones (`1991/11` a `2026/11`, frecuencia diaria hábil bancaria).

---

## 4. Distinción Metodológica: Hechos Oficiales vs. Hipótesis

* **Hecho oficial documentado:**  
  La sustitución de la canasta del INPC por la *"Actualización de Canasta y Ponderadores 2024"* (Tema `189113`) en agosto de 2024 por parte del INEGI.
* **Hecho oficial observado:**  
  Las series legadas `628xxx` terminan de forma fija en `2024/07` y carecen del registro de `2024/06`. La serie activa `910392` incluye `2024/06` y está actualizada hasta septiembre de 2026.
* **[HIPÓTESIS]:**  
  Se postula como hipótesis técnica que la omisión de `2024/06` en las series `628xxx` se originó por un error de sincronización o corte prematuro en el volcado de las tablas históricas del backend del INEGI al momento de archivar esa rama legada y dar de alta la canasta 2024.
* **[HIPÓTESIS]:**  
  Se postula como hipótesis económica que la serie `SF43718` (Tipo de cambio FIX) servirá como variable explicativa indirecta de los costos en insumos importados comercializados en Sam's Club (chocolates, confitería y jarabes).

---

## 5. Instrucciones de Despliegue y Pruebas

1. Configurar los secretos en GitHub: **Settings > Secrets and variables > Actions**:
   - `INEGI_API_TOKEN`
   - `BANXICO_API_TOKEN`
2. El workflow [`.github/workflows/captura.yml`](../../.github/workflows/captura.yml) puede ejecutarse manualmente desde la pestaña **Actions > Captura Automática Bronce > Run workflow**.
