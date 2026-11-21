# Relatoría PSP — Entrega E2: Datos Geoespaciales, Linaje End-to-End y Ética de Datos

**Proyecto:** Observatorio de Datos — Comercio Minorista en Puestos Escolares (Colima, México)  
**Asignatura:** Ingeniería de Datos (ATD-2602) | 7mo Semestre, Periodo Ago–Dic 2026  
**Estudiante:** Yair Alejandro Molina Díaz (No. Control: 23460519)  
**Institución:** Tecnológico Nacional de México — Instituto Tecnológico de Colima  
**Docente:** Prof. Armando Román Gallardo Heredia  
**Fecha:** [COMPLETAR POR EL ESTUDIANTE]  
**Estado:** *Borrador estructural — los tiempos reales, defectos PSP y reflexiones personales deben ser redactados exclusivamente por el estudiante.*

---

> [!IMPORTANT]
> Este archivo es únicamente un **borrador guía**. No incluye tiempos ni vivencias inventadas. Completa cada sección `[COMPLETAR POR EL ESTUDIANTE]` con base en tus registros reales de `calidad/tiempo-*.csv` y `calidad/defectos-*.csv`.

---

## Sección A. Registro y Análisis de Tiempos (PSP)

*Fuente de datos del estudiante: `calidad/tiempo-yair-molina.csv`*

| Fase de la Entrega E2 | Tiempo Planificado (min) | Tiempo Real (min) | Desviación (min) | Observaciones del Estudiante |
| :--- | :---: | :---: | :---: | :--- |
| Fase 1: Verificación de fuentes (DENUE, SCIAN, Marco) | `[COMPLETAR POR EL ESTUDIANTE]` | `[COMPLETAR POR EL ESTUDIANTE]` | `[COMPLETAR POR EL ESTUDIANTE]` | `[COMPLETAR POR EL ESTUDIANTE]` |
| Fase 2: Extractor Bronce geoespacial | `[COMPLETAR POR EL ESTUDIANTE]` | `[COMPLETAR POR EL ESTUDIANTE]` | `[COMPLETAR POR EL ESTUDIANTE]` | `[COMPLETAR POR EL ESTUDIANTE]` |
| Fase 3: Capa Plata geoespacial, CRS y Puerta de Calidad | `[COMPLETAR POR EL ESTUDIANTE]` | `[COMPLETAR POR EL ESTUDIANTE]` | `[COMPLETAR POR EL ESTUDIANTE]` | `[COMPLETAR POR EL ESTUDIANTE]` |
| Fase 4: Capa Oro agregada y cartografía | `[COMPLETAR POR EL ESTUDIANTE]` | `[COMPLETAR POR EL ESTUDIANTE]` | `[COMPLETAR POR EL ESTUDIANTE]` | `[COMPLETAR POR EL ESTUDIANTE]` |
| Fase 5: Linaje end-to-end y verificación de muestra | `[COMPLETAR POR EL ESTUDIANTE]` | `[COMPLETAR POR EL ESTUDIANTE]` | `[COMPLETAR POR EL ESTUDIANTE]` | `[COMPLETAR POR EL ESTUDIANTE]` |
| Fase 6: Declaración de ética y legalidad | `[COMPLETAR POR EL ESTUDIANTE]` | `[COMPLETAR POR EL ESTUDIANTE]` | `[COMPLETAR POR EL ESTUDIANTE]` | `[COMPLETAR POR EL ESTUDIANTE]` |
| Fase 7: Automatización CI/CD (`denue.yml`, `procesar.yml`) | `[COMPLETAR POR EL ESTUDIANTE]` | `[COMPLETAR POR EL ESTUDIANTE]` | `[COMPLETAR POR EL ESTUDIANTE]` | `[COMPLETAR POR EL ESTUDIANTE]` |
| Fase 8: Documentación y revisión final | `[COMPLETAR POR EL ESTUDIANTE]` | `[COMPLETAR POR EL ESTUDIANTE]` | `[COMPLETAR POR EL ESTUDIANTE]` | `[COMPLETAR POR EL ESTUDIANTE]` |
| **Total E2** | **`[COMPLETAR POR EL ESTUDIANTE]`** | **`[COMPLETAR POR EL ESTUDIANTE]`** | **`[COMPLETAR POR EL ESTUDIANTE]`** | |

**Análisis de desviaciones de tiempo:**  
`[COMPLETAR POR EL ESTUDIANTE: explica qué fase tomó más o menos tiempo del estimado y por qué.]`

---

## Sección B. Registro y Análisis de Defectos (PSP)

*Fuente de datos del estudiante: `calidad/defectos-yair-molina.csv`*

| ID Defecto | Fase Inyectado | Fase Removido | Tipo de Defecto | Tiempo de Corrección (min) | Descripción y Solución |
| :---: | :--- | :--- | :--- | :---: | :--- |
| `[COMPLETAR]` | `[COMPLETAR]` | `[COMPLETAR]` | `[COMPLETAR]` | `[COMPLETAR]` | `[COMPLETAR POR EL ESTUDIANTE]` |

*Nota de apoyo técnico (hechos observables durante la implementación que el estudiante puede evaluar si corresponde registrar en su bitácora de defectos):*
* Inestabilidad / *read timeouts* en los endpoints REST `Cuantificar`/`BuscarAreaAct` del DENUE → mitigado mediante sonda cortés con token enmascarado y descarga oficial `denue_06_csv.zip`.
* Presencia del Archipiélago de Revillagigedo dentro de los polígonos oficiales de Manzanillo y Tecomán → mitigado calculando `area_km2_oficial` y `area_km2_continental` por separado y acotando la vista continental en el mapa coroplético.
* Serialización PROJJSON del CRS en GeoParquet detectada en `tests/test_geo_pipeline.py` → corregida validando `gdf.crs.to_epsg() == 4326`.
* Solapamiento menor entre etiquetas de Minatitlán y Villa de Álvarez en la primera versión del mapa coroplético → corregido ajustando desplazamientos de anotación.

**Resumen de lecciones sobre defectos:**  
`[COMPLETAR POR EL ESTUDIANTE]`

---

## Sección C. Reflexión Personal del Estudiante

1. **¿Qué aprendiste al integrar datos geoespaciales reales (CRS, proyecciones métricas, polígonos oficiales y minimización de privacidad) respecto a series temporales tabulares?**  
   `[COMPLETAR POR EL ESTUDIANTE]`

2. **¿Cómo cambió tu perspectiva sobre trazabilidad al construir el linaje end-to-end y verificar una muestra de Oro directamente contra los archivos crudos en Bronce?**  
   `[COMPLETAR POR EL ESTUDIANTE]`

3. **¿Qué implicaciones éticas y legales identificaste al revisar `robots.txt`, licencias de uso comercial y el subregistro del comercio ambulante en el DENUE respecto a tu entrevista de E0?**  
   `[COMPLETAR POR EL ESTUDIANTE]`

4. **Verificaciones pendientes asignadas al estudiante (confirmar al cerrar E2):**  
   - [ ] Revisar manualmente en navegador los términos legales y uso comercial de Banxico SIE (`https://www.banxico.org.mx/SieAPIRest/service/v1/` y `https://www.banxico.org.mx/footer-es/leyendas-legales.html`).  
   - [ ] Configurar el secreto `INEGI_DENUE_TOKEN` en GitHub Actions y `.env` local (si obtienes un token específico de DENUE distinto al de indicadores).  
   - [ ] Actualizar `calidad/tiempo-*.csv` y `calidad/defectos-*.csv` con tus métricas reales antes de crear el tag `e2`.  
   `[COMPLETAR POR EL ESTUDIANTE]`
