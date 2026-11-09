# Objetivos de Calidad del Observatorio de Datos (Entrega E0)

**Proyecto:** Observatorio de Datos - Puestos Escolares (Colima, México)  
**Marco de Calidad:** Personal Software Process (PSP) / Gobierno de Datos  
**Fecha:** Noviembre 2026  

---

A continuación se definen los tres objetivos de calidad cuantitativos y medibles establecidos para el observatorio:

### Objetivo 1: Verificación Literal de Series Oficiales
* **Métrica:** Porcentaje de series configuradas en el extractor que coinciden exactamente con el nombre literal (`CL_INDICATOR`) y la unidad de medida oficial (`CL_UNIT`) del catálogo institucional de la fuente.
* **Meta:** **100%**. Ninguna clave entra al extractor con etiquetas inventadas o interpretadas.
* **Cómo se mide:** Contrastando cada identificador en `src/extractor.py` contra el catálogo oficial descargado (`CL_INDICATOR` y `CL_UNIT`) y documentándolo en `docs/E0/series_seleccionadas.md` antes de autorizar su ejecución.

---

### Objetivo 2: Estabilidad y Confiabilidad del Pipeline de Automatización
* **Métrica:** Número de ejecuciones fallidas (runs en estado rojo/failed) del flujo de trabajo automatizado en GitHub Actions.
* **Meta:** **0 ejecuciones fallidas** durante las primeras 4 semanas consecutivas de operación.
* **Cómo se mide:** Supervisando el historial de ejecuciones en la pestaña **Actions** del repositorio de GitHub sobre el flujo `.github/workflows/captura.yml`.

---

### Objetivo 3: Integridad y Continuidad Temporal de la Capa Bronce
* **Métrica:** Cantidad de meses faltantes (huecos temporales o gaps) dentro del intervalo temporal de cada serie mensual descargada.
* **Meta:** **0 meses faltantes**. La serie mensual debe ser 100% continua entre su fecha inicial y su fecha final.
* **Cómo se mide:** Mediante la ejecución automatizada del script de auditoría `src/validar_bronce.py`, el cual reconstruye el calendario mensual esperado y detecta discrepancias en los archivos JSON de `datos/bronce/`.
